"""Optional local OCR backend discovery and execution."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from gdlex_ocr.searchable_pdf import (
    DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
    build_ocrmypdf_command,
)

SUPPORTED_BACKENDS = ("auto", "ocrmypdf", "external")
DIAGNOSTIC_BACKENDS = ("tesseract", "masterpdf", "pdfstudio")


class OcrBackendError(RuntimeError):
    """Raised when a requested OCR backend cannot be used."""


@dataclass(frozen=True, slots=True)
class OcrBackend:
    name: str
    available: bool
    executable: str | None
    command_template: str | None
    runnable: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrBackendRun:
    name: str
    command: tuple[str, ...]


def detect_ocr_backend(
    name: str,
    *,
    external_command: str | None = None,
) -> OcrBackend:
    """Return local availability without starting OCR or proprietary tools."""
    normalized = name.strip().casefold()
    if normalized == "auto":
        ocrmypdf = detect_ocr_backend("ocrmypdf")
        if ocrmypdf.available:
            return ocrmypdf
        return OcrBackend(
            "auto",
            False,
            None,
            None,
            False,
            ("Nessun backend OCR PDF automatico disponibile.",),
        )
    if normalized == "ocrmypdf":
        executable = shutil.which("ocrmypdf")
        warnings = ()
        if executable is None:
            warnings = (
                "OCRmyPDF non disponibile; installare ocrmypdf e Tesseract.",
            )
        return OcrBackend(
            "ocrmypdf",
            executable is not None,
            executable,
            None,
            executable is not None,
            warnings,
        )
    if normalized == "external":
        return _detect_external(external_command)
    if normalized == "tesseract":
        executable = shutil.which("tesseract")
        return OcrBackend(
            "tesseract",
            executable is not None,
            executable,
            None,
            False,
            (
                "Tesseract è un motore OCR, ma non viene usato direttamente "
                "per creare PDF multipagina; selezionare OCRmyPDF.",
            ),
        )
    if normalized == "masterpdf":
        executable = (
            shutil.which("masterpdfeditor")
            or shutil.which("masterpdfeditor5")
        )
        return OcrBackend(
            "masterpdf",
            executable is not None,
            executable,
            None,
            False,
            (
                "Master PDF Editor rilevato, ma non è disponibile una CLI OCR "
                "batch verificata; usare il workflow manuale documentato.",
            ),
        )
    if normalized == "pdfstudio":
        executable = shutil.which("pdfstudio")
        return OcrBackend(
            "pdfstudio",
            executable is not None,
            executable,
            None,
            False,
            (
                "PDF Studio non dispone di una CLI OCR batch verificata in "
                "GD LEX OCR; non viene automatizzato.",
            ),
        )
    raise ValueError(f"Backend OCR sconosciuto: {name}")


def build_backend_command(
    backend: OcrBackend,
    input_pdf: str | Path,
    output_pdf: str | Path,
    language: str,
) -> list[str]:
    """Build an argument list for a runnable backend."""
    if not backend.available or not backend.runnable:
        detail = backend.warnings[0] if backend.warnings else "non disponibile"
        raise OcrBackendError(
            f"Backend OCR {backend.name} non utilizzabile: {detail}"
        )
    if backend.name == "ocrmypdf":
        command = build_ocrmypdf_command(input_pdf, output_pdf, language)
        if backend.executable is not None:
            command[0] = backend.executable
        return command
    if backend.name == "external" and backend.command_template is not None:
        try:
            command = [
                token.format(
                    input=str(input_pdf),
                    output=str(output_pdf),
                    language=language,
                )
                for token in shlex.split(backend.command_template)
            ]
        except (KeyError, ValueError) as exc:
            raise OcrBackendError(
                f"Placeholder del comando esterno non valido: {exc}"
            ) from exc
        if backend.executable is not None:
            command[0] = backend.executable
        return command
    raise OcrBackendError(f"Backend OCR {backend.name} non implementato.")


def run_ocr_backend(
    backend: OcrBackend,
    input_pdf: str | Path,
    output_pdf: str | Path,
    *,
    language: str = "ita",
    log_callback: Callable[[str], None] | None = None,
    timeout_seconds: int = DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
) -> OcrBackendRun:
    """Run a configured local backend using an argument list.

    Raises OcrBackendError if the backend times out, fails, or produces no output.
    """
    command = build_backend_command(backend, input_pdf, output_pdf, language)
    if log_callback:
        log_callback(
            f"Backend OCR: {backend.name}; comando: {shlex.join(command)}"
        )
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise OcrBackendError(
            f"Impossibile avviare il backend OCR {backend.name}: {exc}"
        ) from exc

    try:
        stdout, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise OcrBackendError(
            f"Backend OCR {backend.name} timeout dopo {timeout_seconds}s; "
            "processo terminato."
        )

    if log_callback:
        for raw_line in stdout.splitlines():
            line = raw_line.rstrip()
            if line:
                log_callback(f"{backend.name}: {line}")

    if process.returncode != 0:
        raise OcrBackendError(
            f"Backend OCR {backend.name} terminato con codice {process.returncode}"
        )
    if not Path(output_pdf).is_file():
        raise OcrBackendError(
            f"Backend OCR {backend.name} non ha creato il PDF atteso."
        )
    return OcrBackendRun(backend.name, tuple(command))


def backend_manifest(backend: OcrBackend, *, used: bool = False) -> dict:
    """Return additive, content-free manifest metadata."""
    return {
        "name": backend.name,
        "command": backend.command_template or backend.executable,
        "available": backend.available,
        "used": used,
        "warnings": list(backend.warnings),
    }


def _detect_external(external_command: str | None) -> OcrBackend:
    template = (external_command or "").strip()
    warnings: list[str] = []
    executable: str | None = None
    runnable = False
    if not template:
        warnings.append("Comando backend esterno non configurato.")
    else:
        try:
            tokens = shlex.split(template)
        except ValueError as exc:
            warnings.append(f"Comando backend esterno non valido: {exc}")
            tokens = []
        if tokens and not {"{input}", "{output}"}.issubset(
            set(_template_fields(tokens))
        ):
            warnings.append(
                "Il comando esterno deve contenere {input} e {output}."
            )
            tokens = []
        elif tokens:
            unknown_fields = [
                token
                for token in tokens
                if "{" in token
                and not all(
                    field in ("input", "output", "language")
                    for field in _field_names(token)
                )
            ]
            if unknown_fields:
                warnings.append(
                    "Il comando esterno contiene placeholder non supportati."
                )
                tokens = []
        if tokens:
            executable = shutil.which(tokens[0])
            if executable is None and Path(tokens[0]).is_file():
                executable = str(Path(tokens[0]))
            if executable is None:
                warnings.append(
                    f"Eseguibile backend esterno non trovato: {tokens[0]}"
                )
            else:
                runnable = True
    return OcrBackend(
        "external",
        runnable,
        executable,
        template or None,
        runnable,
        tuple(warnings),
    )


def _template_fields(tokens: list[str]) -> list[str]:
    fields: list[str] = []
    for token in tokens:
        for field in ("{input}", "{output}", "{language}"):
            if field in token:
                fields.append(field)
    return fields


def _field_names(token: str) -> list[str]:
    names: list[str] = []
    for part in token.split("{")[1:]:
        if "}" in part:
            names.append(part.split("}", 1)[0])
    return names
