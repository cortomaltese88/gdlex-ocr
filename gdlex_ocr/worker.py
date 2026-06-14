"""Background OCR orchestration using a dedicated QThread."""

from __future__ import annotations

import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from gdlex_ocr.act_outline import write_act_index
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
from gdlex_ocr.pdf_outline import add_technical_fallback_bookmarks
from gdlex_ocr.pdf_splitter import PdfSplitError, count_pdf_pages, split_pdf
from gdlex_ocr.profiles import ProcessingProfile
from gdlex_ocr.searchable_pdf import (
    SearchablePdfError,
    make_progressive_output_path,
    run_ocrmypdf,
)
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
    ) -> None:
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.pages_per_block = pages_per_block
        self._profile = profile
        self._create_searchable = create_searchable
        self._ocr_language = ocr_language
        self._runner = DoclingRunner()
        self._work_dir: Path | None = None
        self._log_path = self.output_dir / "run.log"
        self._manifest: dict[str, Any] | None = None

    @property
    def work_dir(self) -> Path | None:
        return self._work_dir

    def request_cancel(self) -> None:
        self.requestInterruption()
        self._runner.cancel()

    def run(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._manifest = build_initial_manifest(
            pdf_path=self.pdf_path,
            output_dir=self.output_dir,
            profile=self._profile,
            pages_per_block=self.pages_per_block,
            create_searchable=self._create_searchable,
            ocr_language=self._ocr_language,
            app_version=APP_VERSION,
        )
        safe_write_manifest(self._manifest, self.output_dir)

        try:
            self._write_log("=" * 72)
            self._write_log(
                f"Avvio elaborazione: {self.pdf_path.name} "
                f"({datetime.now().isoformat(timespec='seconds')})"
            )
            self._write_log(f"Profilo: {self._profile.name}")

            total_pages = count_pdf_pages(self.pdf_path)
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
                self.pdf_path,
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

            if self._create_searchable:
                self._build_searchable_pdf(total_pages, final_path)

        except DoclingCancelled:
            if self._manifest is not None:
                self._manifest["job"]["status"] = "cancelled"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                safe_write_manifest(self._manifest, self.output_dir)
            self._handle_cancelled()
        except (
            PdfSplitError,
            DoclingError,
            MarkdownMergeError,
            OSError,
            ValueError,
        ) as exc:
            self._write_log(f"ERRORE: {exc}")
            if self._manifest is not None:
                self._manifest["job"]["status"] = "failed"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                self._manifest["errors"].append(str(exc))
                safe_write_manifest(self._manifest, self.output_dir)
            self.failed.emit(str(exc))
        except Exception as exc:
            message = f"Errore inatteso: {exc}"
            self._write_log(f"ERRORE: {message}")
            if self._manifest is not None:
                self._manifest["job"]["status"] = "failed"
                self._manifest["job"]["finished_at"] = utc_now_iso()
                self._manifest["errors"].append(message)
                safe_write_manifest(self._manifest, self.output_dir)
            self.failed.emit(message)

    def _build_searchable_pdf(
        self,
        total_pages: int,
        markdown_path: Path,
    ) -> None:
        try:
            self._write_log("─" * 60)
            self._write_log("Creazione PDF ricercabile OCR...")
            searchable_path = make_progressive_output_path(
                self.output_dir, self.pdf_path.stem
            )
            run_ocrmypdf(
                self.pdf_path,
                searchable_path,
                language=self._ocr_language,
                log_callback=self._write_log,
            )
            add_technical_fallback_bookmarks(
                searchable_path,
                self.pages_per_block,
                total_pages,
            )
            self._write_log(
                "Aggiunti segnalibri PDF tecnici per intervalli di pagine."
            )
            index = write_act_index(markdown_path)
            self._write_log(
                f"Indice atti Markdown sperimentale creato: {index.index_path}"
            )
            self._write_log(f"PDF ricercabile creato: {searchable_path}")
            self._write_log("─" * 60)
            if self._manifest is not None:
                self._manifest["outputs"]["searchable_pdf"] = str(searchable_path)
                self._manifest["outputs"]["index_markdown"] = str(index.index_path)
                safe_write_manifest(self._manifest, self.output_dir)
            self.searchable_pdf_done.emit(str(searchable_path))
        except (SearchablePdfError, OSError, ValueError) as exc:
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

    def _raise_if_cancelled(self) -> None:
        if self.isInterruptionRequested():
            raise DoclingCancelled("Elaborazione annullata.")

    def _handle_cancelled(self) -> None:
        location = str(self._work_dir) if self._work_dir else str(self.output_dir)
        self._write_log("Elaborazione annullata dall'utente.")
        self.cancelled.emit(location)

    def _next_output_path(self) -> Path:
        base_path = self.output_dir / f"{self.pdf_path.stem}_ocr.md"
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
