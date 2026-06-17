"""OCRmyPDF integration for creating searchable (text-layer) PDFs."""

from __future__ import annotations

import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable


INSTALL_HINT = (
    "Installa: sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-ita"
)

DEFAULT_OCRMYPDF_TIMEOUT_SECONDS = 1800
PROCESS_TERMINATE_GRACE_SECONDS = 5.0


class SearchablePdfError(RuntimeError):
    """Raised when OCRmyPDF fails or is not available."""


def validate_ocrmypdf_timeout_seconds(timeout_seconds: int) -> int:
    """Return a validated OCRmyPDF timeout in seconds."""
    if timeout_seconds <= 0:
        raise ValueError(
            "Timeout OCRmyPDF non valido: deve essere maggiore di 0 secondi."
        )
    return timeout_seconds


def validate_ocrmypdf_jobs(jobs: int | None) -> int | None:
    """Return a validated OCRmyPDF jobs value."""
    if jobs is not None and jobs <= 0:
        raise ValueError(
            "Jobs OCRmyPDF non valido: deve essere maggiore di 0."
        )
    return jobs


def is_ocrmypdf_available() -> bool:
    """Return True if the ocrmypdf executable is found in PATH."""
    return shutil.which("ocrmypdf") is not None


def build_ocrmypdf_command(
    input_pdf: str | Path,
    output_pdf: str | Path,
    language: str = "ita",
    jobs: int | None = None,
) -> list[str]:
    """Build the OCRmyPDF CLI command as an argument list (never shell=True)."""
    jobs = validate_ocrmypdf_jobs(jobs)
    command = [
        "ocrmypdf",
        "--language", language,
        "--deskew",
        "--rotate-pages",
        "--skip-text",
        "--optimize", "1",
    ]
    if jobs is not None:
        command.extend(["--jobs", str(jobs)])
    command.extend([str(input_pdf), str(output_pdf)])
    return command


def make_progressive_output_path(
    output_dir: str | Path,
    stem: str,
    suffix: str = "_searchable",
) -> Path:
    """Return a non-existing path for the searchable PDF output."""
    output_dir = Path(output_dir)
    base = output_dir / f"{stem}{suffix}.pdf"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = output_dir / f"{stem}{suffix}_{n}.pdf"
        if not candidate.exists():
            return candidate
        n += 1


def run_process_with_incremental_output(
    command: list[str],
    *,
    timeout_seconds: int,
    line_callback: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Run *command* and stream merged stdout/stderr lines as they arrive."""
    timeout_seconds = validate_ocrmypdf_timeout_seconds(timeout_seconds)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines: list[str] = []
    lines: queue.Queue[str | None] = queue.Queue()

    def read_output() -> None:
        stdout = process.stdout
        try:
            if stdout is not None:
                for raw_line in stdout:
                    lines.put(raw_line)
        finally:
            if stdout is not None and hasattr(stdout, "close"):
                stdout.close()
            lines.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout_seconds
    reader_done = False

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 and process.poll() is None:
                _terminate_timed_out_process(process, command, timeout_seconds)
            try:
                raw_line = lines.get(timeout=min(max(remaining, 0.0), 0.1))
            except queue.Empty:
                if process.poll() is not None and reader_done:
                    break
                continue
            if raw_line is None:
                reader_done = True
                if process.poll() is not None:
                    break
                continue
            output_lines.append(raw_line)
            if line_callback:
                line = raw_line.rstrip()
                if line:
                    line_callback(line)
    finally:
        reader.join(timeout=1.0)

    return process.wait(), "".join(output_lines)


def _terminate_timed_out_process(
    process: subprocess.Popen[str],
    command: list[str],
    timeout_seconds: int,
) -> None:
    process.terminate()
    try:
        process.wait(timeout=PROCESS_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    raise subprocess.TimeoutExpired(command, timeout_seconds)


def run_ocrmypdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    language: str = "ita",
    jobs: int | None = None,
    log_callback: Callable[[str], None] | None = None,
    timeout_seconds: int = DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
) -> None:
    """Run OCRmyPDF, collecting output into *log_callback*.

    Raises SearchablePdfError if ocrmypdf is not installed, times out, or fails.
    """
    timeout_seconds = validate_ocrmypdf_timeout_seconds(timeout_seconds)
    if not is_ocrmypdf_available():
        raise SearchablePdfError(
            f"OCRmyPDF non installato. {INSTALL_HINT}"
        )

    command = build_ocrmypdf_command(input_pdf, output_pdf, language, jobs)
    if log_callback:
        log_callback(f"Comando OCRmyPDF: {' '.join(command)}")

    try:
        returncode, _stdout = run_process_with_incremental_output(
            command,
            timeout_seconds=timeout_seconds,
            line_callback=(
                (lambda line: log_callback(f"ocrmypdf: {line}"))
                if log_callback
                else None
            ),
        )
    except OSError as exc:
        raise SearchablePdfError(
            f"Impossibile avviare OCRmyPDF: {exc}"
        ) from exc
    except subprocess.TimeoutExpired:
        raise SearchablePdfError(
            f"OCRmyPDF timeout dopo {timeout_seconds}s; processo terminato."
        )

    if returncode != 0:
        raise SearchablePdfError(
            f"OCRmyPDF è terminato con codice {returncode}"
        )
