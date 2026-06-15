"""Background OCR orchestration using a dedicated QThread."""

from __future__ import annotations

import shlex
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from gdlex_ocr.bookmarks import select_bookmarks, write_bookmark_index
from gdlex_ocr.docling_runner import (
    DoclingCancelled,
    DoclingError,
    DoclingRunner,
)
from gdlex_ocr.manifest import (
    build_initial_manifest,
    safe_write_manifest,
    utc_now_iso,
)
from gdlex_ocr.markdown_merge import (
    MarkdownBlock,
    MarkdownMergeError,
    merge_markdown,
)
from gdlex_ocr.markdown_sanitize import sanitize_markdown_file
from gdlex_ocr.markdown_structure import structure_markdown_file
from gdlex_ocr.ocr_backends import (
    OcrBackend,
    OcrBackendError,
    backend_manifest,
    detect_ocr_backend,
    run_ocr_backend,
)
from gdlex_ocr.output_layout import (
    build_job_output_dir,
    build_output_layout,
    create_unique_output_dir,
)
from gdlex_ocr.pdf_outline import add_outline_items
from gdlex_ocr.pdf_splitter import PdfSplitError, count_pdf_pages, split_pdf
from gdlex_ocr.profiles import ProcessingProfile
from gdlex_ocr.searchable_pdf import make_progressive_output_path
from gdlex_ocr.version import APP_VERSION


class OcrWorker(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int, str)
    # (final_path, work_dir, duration_text, speed_text)
    completed = Signal(str, str, str, str)
    cancelled = Signal(str)
    failed = Signal(str)
    searchable_pdf_done = Signal(str)
    searchable_pdf_error = Signal(str)

    def __init__(
        self,
        pdf_path: str,
        output_dir: str,
        pages_per_block: int,
        profile: ProcessingProfile,
        create_searchable: bool = False,
        ocr_language: str = "ita",
        parent=None,
        *,
        structured_output: bool = False,
        ocr_backend: str = "auto",
        external_ocr_command: str | None = None,
        use_searchable_as_source: bool = False,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.output_root = Path(output_dir)
        self.output_dir = self.output_root
        self.pages_per_block = pages_per_block
        self._profile = profile
        self._create_searchable = create_searchable
        self._ocr_language = ocr_language
        self._structured_output = structured_output
        self._ocr_backend_name = ocr_backend
        self._external_ocr_command = external_ocr_command
        self._use_searchable_as_source = use_searchable_as_source
        self._ocr_backend: OcrBackend | None = None
        self._prepared_searchable_path: Path | None = None
        self._source_backend_failed = False
        self._runner = DoclingRunner()
        self._work_dir: Path | None = None
        self._output_layout = build_output_layout(
            self.pdf_path,
            self.output_dir,
        )
        self._log_path = self._output_layout["run_log"]
        self._manifest: dict[str, Any] | None = None

    @property
    def work_dir(self) -> Path | None:
        return self._work_dir

    def request_cancel(self) -> None:
        self.requestInterruption()
        self._runner.cancel()

    def run(self) -> None:
        job_started = time.monotonic()
        try:
            self._prepare_output_dir()
            self._manifest = build_initial_manifest(
                pdf_path=self.pdf_path,
                output_dir=self.output_dir,
                profile=self._profile,
                pages_per_block=self.pages_per_block,
                create_searchable=self._create_searchable,
                ocr_language=self._ocr_language,
                app_version=APP_VERSION,
                structured_output=self._structured_output,
                ocr_backend=self._ocr_backend_name,
                external_ocr_command=self._external_ocr_command,
                use_searchable_as_source=self._use_searchable_as_source,
            )
            safe_write_manifest(self._manifest, self.output_dir)

            self._write_log("=" * 72)
            self._write_log(
                f"Avvio elaborazione: {self.pdf_path.name} "
                f"({datetime.now().isoformat(timespec='seconds')})"
            )
            self._write_log(f"Profilo: {self._profile.name}")

            processing_pdf = self.pdf_path
            if self._create_searchable:
                self._ocr_backend = detect_ocr_backend(
                    self._ocr_backend_name,
                    external_command=self._external_ocr_command,
                )
                self._manifest["ocr_backend"].update(
                    backend_manifest(self._ocr_backend)
                )
                if self._use_searchable_as_source:
                    processing_pdf = self._prepare_searchable_source()

            total_pages = count_pdf_pages(processing_pdf)
            self._manifest["input"]["page_count"] = total_pages
            self._write_log(f"Pagine totali: {total_pages}")
            self._work_dir = Path(
                tempfile.mkdtemp(
                    prefix=f".gdlex_ocr_{self.pdf_path.stem}_",
                    dir=self.output_dir,
                )
            )
            pdf_blocks_dir = self._work_dir / "pdf_blocks"
            markdown_dir = self._work_dir / "markdown_blocks"
            markdown_dir.mkdir(parents=True, exist_ok=True)
            self._write_log(f"Directory output parziali: {self._work_dir}")

            blocks = split_pdf(
                processing_pdf,
                pdf_blocks_dir,
                self.pages_per_block,
                on_block_created=lambda block: self._write_log(
                    f"Creato blocco {block.index}: pagine "
                    f"{block.start_page}-{block.end_page}"
                ),
            )
            self._manifest["processing"]["blocks_total"] = len(blocks)
            self._raise_if_cancelled()

            partials: list[MarkdownBlock] = []
            processed_pages = 0
            processing_seconds = 0.0
            total_started = time.monotonic()
            slowest_block_index = 0
            slowest_block_seconds = 0.0

            for block in blocks:
                self._raise_if_cancelled()
                self._write_log(
                    f"Elaborazione blocco {block.index}/{len(blocks)} "
                    f"(pagine {block.start_page}-{block.end_page})"
                )
                started = time.monotonic()
                markdown_path = self._runner.run(
                    block.path,
                    markdown_dir,
                    log_callback=self._write_log,
                    table_mode=self._profile.table_mode,
                    num_threads=self._profile.num_threads,
                    page_batch_size=self._profile.page_batch_size,
                    enable_ocr=self._profile.enable_ocr,
                    enrich_picture=self._profile.enrich_picture,
                    enrich_chart=self._profile.enrich_chart,
                )
                sanitize_result = sanitize_markdown_file(markdown_path)
                self._write_log(
                    f"Sanitizzazione blocco {block.index}: "
                    f"{sanitize_result.total_removed} rimozioni "
                    f"({sanitize_result.embedded_images_removed} immagini "
                    "embedded, "
                    f"{sanitize_result.long_base64_lines_removed} righe "
                    "base64 patologiche)"
                )
                block_seconds = time.monotonic() - started
                processing_seconds += block_seconds
                processed_pages += block.page_count

                if block_seconds > slowest_block_seconds:
                    slowest_block_seconds = block_seconds
                    slowest_block_index = block.index

                partials.append(
                    MarkdownBlock(
                        block.index,
                        block.start_page,
                        block.end_page,
                        markdown_path,
                    )
                )
                self._manifest["processing"]["blocks_completed"] = len(partials)

                seconds_per_page = processing_seconds / processed_pages
                remaining_pages = total_pages - processed_pages
                eta_seconds = seconds_per_page * remaining_pages
                percent = round(processed_pages / total_pages * 100)
                eta_text = self._format_eta(eta_seconds)
                self._write_log(
                    f"Blocco {block.index} completato in "
                    f"{self._format_duration(block_seconds)}. "
                    f"Avanzamento {percent}% - ETA {eta_text}"
                )
                self.progress_changed.emit(percent, eta_text)

            self._raise_if_cancelled()
            final_output_path = self._next_output_path()
            final_path = merge_markdown(
                partials,
                final_output_path,
                self.pdf_path.name,
            )
            if self._profile.structure_markdown:
                self._post_process_markdown(final_path)

            total_seconds = time.monotonic() - total_started
            pages_per_min = (
                total_pages / (total_seconds / 60) if total_seconds > 0 else 0.0
            )
            duration_text = self._format_duration(total_seconds)
            speed_text = f"{pages_per_min:.1f} pag/min"
            slowest_text = (
                f"blocco {slowest_block_index} "
                f"({self._format_duration(slowest_block_seconds)})"
            )

            self._write_log("─" * 60)
            self._write_log("Riepilogo elaborazione:")
            self._write_log(f"  Durata totale:    {duration_text}")
            self._write_log(f"  Pagine totali:    {total_pages}")
            self._write_log(f"  Velocità:         {speed_text}")
            self._write_log(f"  Blocco più lento: {slowest_text}")
            self._write_log(f"  Markdown finale:  {final_path}")
            self._write_log("─" * 60)
            self._write_log("Elaborazione completata.")

            self._manifest["job"]["status"] = "success"
            self._manifest["job"]["finished_at"] = utc_now_iso()
            self._manifest["job"]["duration_seconds"] = round(total_seconds, 3)
            self._manifest["outputs"]["markdown"] = str(final_path)
            safe_write_manifest(self._manifest, self.output_dir)

            self.progress_changed.emit(100, "Completato")
            self.completed.emit(
                str(final_path),
                str(self._work_dir),
                duration_text,
                speed_text,
            )

            if self._create_searchable and not self._source_backend_failed:
                self._build_searchable_pdf(
                    total_pages,
                    final_path,
                    searchable_path=self._prepared_searchable_path,
                )

        except DoclingCancelled:
            if self._manifest is not None:
                self._manifest["job"]["status"] = "cancelled"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                self._manifest["job"]["duration_seconds"] = round(
                    time.monotonic() - job_started, 3
                )
                safe_write_manifest(self._manifest, self.output_dir)
            self._handle_cancelled()
        except (
            PdfSplitError,
            DoclingError,
            MarkdownMergeError,
            OcrBackendError,
            OSError,
            ValueError,
        ) as exc:
            self._write_log(f"ERRORE: {exc}")
            if self._manifest is not None:
                self._manifest["job"]["status"] = "failed"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                self._manifest["job"]["duration_seconds"] = round(
                    time.monotonic() - job_started, 3
                )
                self._manifest["errors"].append(str(exc))
                safe_write_manifest(self._manifest, self.output_dir)
            self.failed.emit(str(exc))
        except Exception as exc:
            message = f"Errore inatteso: {exc}"
            self._write_log(f"ERRORE: {message}")
            if self._manifest is not None:
                self._manifest["job"]["status"] = "failed"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                self._manifest["job"]["duration_seconds"] = round(
                    time.monotonic() - job_started, 3
                )
                self._manifest["errors"].append(message)
                safe_write_manifest(self._manifest, self.output_dir)
            self.failed.emit(message)

    def _prepare_output_dir(self) -> None:
        if self._structured_output:
            self.output_dir = create_unique_output_dir(
                build_job_output_dir(self.pdf_path, self.output_root)
            )
        else:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self._output_layout = build_output_layout(
            self.pdf_path,
            self.output_dir,
        )
        self._log_path = self._output_layout["run_log"]

    def _build_searchable_pdf(
        self,
        total_pages: int,
        markdown_path: Path,
        *,
        searchable_path: Path | None = None,
    ) -> None:
        try:
            self._write_log("─" * 60)
            if searchable_path is None:
                self._write_log("Creazione PDF ricercabile OCR...")
                searchable_path = make_progressive_output_path(
                    self.output_dir, self.pdf_path.stem
                )
                self._run_selected_backend(self.pdf_path, searchable_path)
            else:
                self._write_log(
                    "Uso del PDF ricercabile preparato come sorgente Docling."
                )
            bookmarks = select_bookmarks(
                self.pdf_path,
                markdown_path,
                block_size=self.pages_per_block,
                total_pages=total_pages,
            )
            add_outline_items(searchable_path, bookmarks.items)
            index_path = write_bookmark_index(markdown_path, bookmarks)
            if bookmarks.fallback:
                self._write_log(
                    "Indice/segnalibri: fallback tecnico "
                    f"{bookmarks.strategy}, {len(bookmarks.items)} voci."
                )
            else:
                self._write_log(
                    "Indice/segnalibri: strategia "
                    f"{bookmarks.strategy}, {len(bookmarks.items)} voci."
                )
            for warning in bookmarks.warnings:
                self._write_log(f"Warning segnalibri: {warning}")
            self._write_log(
                f"Indice Markdown creato: {index_path}"
            )
            self._write_log(f"PDF ricercabile creato: {searchable_path}")
            self._write_log("─" * 60)
            if self._manifest is not None:
                self._manifest["outputs"]["searchable_pdf"] = str(searchable_path)
                self._manifest["outputs"]["index_markdown"] = str(index_path)
                self._manifest["bookmarks"] = {
                    "strategy": bookmarks.strategy,
                    "count": len(bookmarks.items),
                    "fallback": bookmarks.fallback,
                    "warnings": list(bookmarks.warnings),
                }
                safe_write_manifest(self._manifest, self.output_dir)
            self.searchable_pdf_done.emit(str(searchable_path))
        except (OcrBackendError, OSError, ValueError) as exc:
            self._write_log(f"ERRORE PDF ricercabile: {exc}")
            if self._manifest is not None:
                self._manifest["warnings"].append(
                    f"PDF ricercabile non creato: {exc}"
                )
                safe_write_manifest(self._manifest, self.output_dir)
            self.searchable_pdf_error.emit(str(exc))
        except Exception as exc:
            message = f"Errore inatteso durante la creazione PDF ricercabile: {exc}"
            self._write_log(f"ERRORE PDF ricercabile: {message}")
            if self._manifest is not None:
                self._manifest["warnings"].append(message)
                safe_write_manifest(self._manifest, self.output_dir)
            self.searchable_pdf_error.emit(message)

    def _prepare_searchable_source(self) -> Path:
        searchable_path = make_progressive_output_path(
            self.output_dir,
            self.pdf_path.stem,
        )
        self._write_log(
            "Preparazione PDF ricercabile come sorgente della conversione..."
        )
        try:
            self._run_selected_backend(self.pdf_path, searchable_path)
        except OcrBackendError as exc:
            self._source_backend_failed = True
            message = (
                f"Backend OCR non disponibile; uso il PDF originale: {exc}"
            )
            self._write_log(f"Warning: {message}")
            if self._manifest is not None:
                self._manifest["warnings"].append(message)
                self._manifest["ocr_backend"]["warnings"].append(str(exc))
                safe_write_manifest(self._manifest, self.output_dir)
            self.searchable_pdf_error.emit(str(exc))
            return self.pdf_path
        self._prepared_searchable_path = searchable_path
        return searchable_path

    def _run_selected_backend(
        self,
        input_pdf: Path,
        output_pdf: Path,
    ) -> None:
        backend = self._ocr_backend or detect_ocr_backend(
            self._ocr_backend_name,
            external_command=self._external_ocr_command,
        )
        self._ocr_backend = backend
        if self._manifest is not None:
            self._manifest["ocr_backend"].update(backend_manifest(backend))
        result = run_ocr_backend(
            backend,
            input_pdf,
            output_pdf,
            language=self._ocr_language,
            log_callback=self._write_log,
        )
        if self._manifest is not None:
            self._manifest["ocr_backend"].update({
                "name": result.name,
                "command": shlex.join(result.command),
                "available": True,
                "used": True,
                "warnings": list(backend.warnings),
            })
        self._write_log(f"Backend OCR usato: {result.name}.")

    def _post_process_markdown(self, markdown_path: Path) -> None:
        result = structure_markdown_file(markdown_path)
        if self._manifest is not None:
            self._manifest["markdown_structure"] = {
                "enabled": True,
                "post_processed": True,
                "headings_added": result.headings_added,
                "strategy": result.strategy,
                "warnings": list(result.warnings),
            }
        self._write_log(
            "Markdown: aggiunti "
            f"{result.headings_added} heading strutturali "
            "con euristiche conservative."
        )

    def _raise_if_cancelled(self) -> None:
        if self.isInterruptionRequested():
            raise DoclingCancelled("Elaborazione annullata.")

    def _handle_cancelled(self) -> None:
        location = str(self._work_dir) if self._work_dir else str(self.output_dir)
        self._write_log("Elaborazione annullata dall'utente.")
        self.cancelled.emit(location)

    def _next_output_path(self) -> Path:
        base_path = self._output_layout["markdown"]
        if not base_path.exists():
            return base_path

        suffix = 2
        while True:
            candidate = self.output_dir / (
                f"{self.pdf_path.stem}_ocr_{suffix}.md"
            )
            if not candidate.exists():
                return candidate
            suffix += 1

    def _write_log(self, message: str) -> None:
        timestamped = (
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        )
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(timestamped + "\n")
        except OSError:
            pass
        self.log_message.emit(timestamped)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        rounded = max(0, round(seconds))
        minutes, secs = divmod(rounded, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {secs:02d}s"
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"

    @classmethod
    def _format_eta(cls, seconds: float) -> str:
        return cls._format_duration(seconds)
