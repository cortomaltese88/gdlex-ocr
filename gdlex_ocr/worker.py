"""Background OCR orchestration using a dedicated QThread."""

from __future__ import annotations

import tempfile
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from gdlex_ocr.docling_runner import (
    DoclingCancelled,
    DoclingError,
    DoclingRunner,
)
from gdlex_ocr.markdown_merge import (
    MarkdownBlock,
    MarkdownMergeError,
    merge_markdown,
)
from gdlex_ocr.markdown_sanitize import sanitize_markdown_file
from gdlex_ocr.pdf_splitter import PdfSplitError, count_pdf_pages, split_pdf


class OcrWorker(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int, str)
    completed = Signal(str, str)
    cancelled = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        pdf_path: str,
        output_dir: str,
        pages_per_block: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.pages_per_block = pages_per_block
        self._runner = DoclingRunner()
        self._work_dir: Path | None = None
        self._log_path = self.output_dir / "run.log"

    @property
    def work_dir(self) -> Path | None:
        return self._work_dir

    def request_cancel(self) -> None:
        self.requestInterruption()
        self._runner.cancel()

    def run(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._write_log("=" * 72)
            self._write_log(
                f"Avvio elaborazione: {self.pdf_path.name} "
                f"({datetime.now().isoformat(timespec='seconds')})"
            )

            total_pages = count_pdf_pages(self.pdf_path)
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
            self._raise_if_cancelled()

            partials: list[MarkdownBlock] = []
            processed_pages = 0
            processing_seconds = 0.0

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
                partials.append(
                    MarkdownBlock(
                        block.index,
                        block.start_page,
                        block.end_page,
                        markdown_path,
                    )
                )

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
            self._write_log(f"Markdown finale creato: {final_path}")
            self._write_log("Elaborazione completata.")
            self.progress_changed.emit(100, "Completato")
            self.completed.emit(str(final_path), str(self._work_dir))
        except DoclingCancelled:
            self._handle_cancelled()
        except (
            PdfSplitError,
            DoclingError,
            MarkdownMergeError,
            OSError,
            ValueError,
        ) as exc:
            self._write_log(f"ERRORE: {exc}")
            self.failed.emit(str(exc))
        except Exception as exc:
            message = f"Errore inatteso: {exc}"
            self._write_log(f"ERRORE: {message}")
            self.failed.emit(message)

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
