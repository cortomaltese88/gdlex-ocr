"""OCRmyPDF integration for creating searchable (text-layer) PDFs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable


INSTALL_HINT = (
    "Installa: sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-ita"
)

DEFAULT_OCRMYPDF_TIMEOUT_SECONDS = 1800


class SearchablePdfError(RuntimeError):
    """Raised when OCRmyPDF fails or is not available."""


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
    if not is_ocrmypdf_available():
        raise SearchablePdfError(
            f"OCRmyPDF non installato. {INSTALL_HINT}"
        )

    command = build_ocrmypdf_command(input_pdf, output_pdf, language, jobs)
    if log_callback:
        log_callback(f"Comando OCRmyPDF: {' '.join(command)}")

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise SearchablePdfError(
            f"Impossibile avviare OCRmyPDF: {exc}"
        ) from exc

    try:
        stdout, _ = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise SearchablePdfError(
            f"OCRmyPDF timeout dopo {timeout_seconds}s; processo terminato."
        )

    if log_callback:
        for raw_line in stdout.splitlines():
            line = raw_line.rstrip()
            if line:
                log_callback(f"ocrmypdf: {line}")

    if proc.returncode != 0:
        raise SearchablePdfError(
            f"OCRmyPDF è terminato con codice {proc.returncode}"
        )
