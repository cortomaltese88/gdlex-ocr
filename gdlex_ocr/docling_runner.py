"""Interruptible subprocess wrapper for the local Docling CLI."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Literal


TableMode = Literal["fast", "accurate"]


def build_docling_command(
    executable: str,
    source_pdf: str | Path,
    output_dir: str | Path,
    *,
    table_mode: TableMode | None = None,
    num_threads: int | None = None,
    page_batch_size: int | None = None,
    enable_ocr: bool = True,
    enrich_picture: bool = True,
    enrich_chart: bool = True,
) -> list[str]:
    """Build the Docling CLI command without starting a subprocess."""
    if table_mode not in (None, "fast", "accurate"):
        raise ValueError(
            "table_mode deve essere 'fast', 'accurate' oppure None."
        )

    command = [
        executable,
        str(source_pdf),
        "--from",
        "pdf",
        "--to",
        "md",
        "--output",
        str(output_dir),
        "--image-export-mode",
        "placeholder",
        "--ocr" if enable_ocr else "--no-ocr",
        "--abort-on-error",
        "-v",
    ]
    if table_mode is not None:
        command.extend(["--table-mode", table_mode])
    if num_threads is not None:
        command.extend(["--num-threads", str(num_threads)])
    if page_batch_size is not None:
        command.extend(["--page-batch-size", str(page_batch_size)])
    if not enrich_picture:
        command.extend([
            "--no-enrich-picture-classes",
            "--no-enrich-picture-description",
        ])
    if not enrich_chart:
        command.append("--no-enrich-chart-extraction")
    return command


class DoclingError(RuntimeError):
    """Raised when Docling cannot be started or finishes unsuccessfully."""


class DoclingCancelled(RuntimeError):
    """Raised when a running conversion is cancelled."""


class DoclingRunner:
    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._cancel_requested = threading.Event()

    @staticmethod
    def find_executable() -> str:
        executable = shutil.which("docling")
        if executable:
            return executable

        sibling = Path(sys.executable).with_name("docling")
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return str(sibling)

        raise DoclingError(
            "Comando Docling non trovato. Installare 'docling' nello stesso "
            "ambiente Python usato per avviare GD LEX OCR."
        )

    def run(
        self,
        source_pdf: str | Path,
        output_dir: str | Path,
        log_callback: Callable[[str], None] | None = None,
        table_mode: TableMode | None = None,
        num_threads: int | None = None,
        page_batch_size: int | None = None,
        enable_ocr: bool = True,
        enrich_picture: bool = True,
        enrich_chart: bool = True,
    ) -> Path:
        if self._cancel_requested.is_set():
            raise DoclingCancelled("Elaborazione annullata.")

        source = Path(source_pdf)
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        expected_markdown = destination / f"{source.stem}.md"
        command = build_docling_command(
            self.find_executable(),
            source,
            destination,
            table_mode=table_mode,
            num_threads=num_threads,
            page_batch_size=page_batch_size,
            enable_ocr=enable_ocr,
            enrich_picture=enrich_picture,
            enrich_chart=enrich_chart,
        )

        if log_callback:
            log_callback(f"Comando: {' '.join(command)}")

        with self._lock:
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
            except OSError as exc:
                raise DoclingError(
                    f"Impossibile avviare Docling: {exc}"
                ) from exc
            self._process = process

        if self._cancel_requested.is_set():
            self._terminate_process(process)

        output_lines: list[str] = []
        try:
            if process.stdout is None:
                self._terminate_process(process)
                process.wait()
                raise DoclingError(
                    "Impossibile leggere l'output del processo Docling."
                )
            for raw_line in process.stdout:
                line = raw_line.rstrip()
                if line:
                    output_lines.append(line)
                    if log_callback:
                        log_callback(f"Docling: {line}")
            return_code = process.wait()
        finally:
            with self._lock:
                self._process = None

        if self._cancel_requested.is_set():
            raise DoclingCancelled("Elaborazione annullata.")
        if return_code != 0:
            detail = output_lines[-1] if output_lines else "nessun dettaglio disponibile"
            raise DoclingError(
                f"Docling è terminato con codice {return_code}: {detail}"
            )
        if not expected_markdown.is_file():
            candidates = sorted(destination.glob("*.md"))
            if len(candidates) == 1:
                return candidates[0]
            raise DoclingError(
                f"Docling non ha prodotto il file Markdown atteso: "
                f"{expected_markdown.name}"
            )
        return expected_markdown

    def cancel(self) -> None:
        self._cancel_requested.set()
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return

        self._terminate_process(process)
        threading.Thread(
            target=self._force_kill_after_timeout,
            args=(process,),
            daemon=True,
        ).start()

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    @staticmethod
    def _force_kill_after_timeout(process: subprocess.Popen[str]) -> None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
