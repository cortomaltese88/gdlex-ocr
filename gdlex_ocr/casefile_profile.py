"""Deterministic folder-profile detection for case-file analysis."""

from __future__ import annotations

from dataclasses import dataclass

from gdlex_ocr.casefile import (
    ATTACHMENT_INDEX_FILENAME,
    CaseFileAnalysis,
    CaseFileDocument,
    PDF_EXTENSION,
)

_IMAGE_EXTENSIONS = frozenset({
    ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".gif",
})

PROFILE_LABELS: dict[str, str] = {
    "ministeriale_tiap": "Ministeriale TIAP",
    "immagini_scansioni": "Immagini/Scansioni",
    "pdf_sciolti": "PDF sciolti",
    "misto": "Misto",
    "sconosciuto": "Sconosciuto",
}


@dataclass(frozen=True, slots=True)
class CaseFileProfile:
    profile: str
    confidence: str
    reason: str


def detect_casefile_profile(analysis: CaseFileAnalysis) -> CaseFileProfile:
    """Detect the folder profile from structural metadata only."""
    total = analysis.total_files
    if total == 0:
        return CaseFileProfile("sconosciuto", "low", "cartella vuota")

    n_units = len(analysis.units)
    n_pdf = analysis.total_pdf_files
    n_images = _count_images(analysis.documents)
    has_indexes = _has_attachment_indexes(analysis.documents)

    if _is_ministeriale_tiap(n_units, n_pdf, has_indexes, total):
        units_with_index = sum(
            1 for u in analysis.units if u.attachment_index_path
        )
        return CaseFileProfile(
            "ministeriale_tiap",
            "high",
            f"rilevate {n_units} unità con {units_with_index} "
            f"{ATTACHMENT_INDEX_FILENAME} e PDF principale numerico",
        )

    if _is_misto(n_pdf, n_images, n_units, total):
        return CaseFileProfile(
            "misto",
            "medium",
            f"{n_pdf} PDF, {n_images} immagini, {n_units} unità TIAP "
            f"su {total} file totali",
        )

    if _is_immagini_scansioni(n_images, n_pdf, total, has_indexes):
        pct = round(n_images / total * 100)
        return CaseFileProfile(
            "immagini_scansioni",
            "high" if pct >= 80 else "medium",
            f"{n_images}/{total} file immagine ({pct}%), "
            f"{n_pdf} PDF, nessun indice allegati",
        )

    if _is_pdf_sciolti(n_pdf, n_units, total, has_indexes):
        pct = round(n_pdf / total * 100)
        return CaseFileProfile(
            "pdf_sciolti",
            "high" if pct >= 80 else "medium",
            f"{n_pdf}/{total} PDF ({pct}%), "
            f"assenza struttura TIAP e indici allegati",
        )

    return CaseFileProfile(
        "sconosciuto",
        "low",
        f"{total} file, nessun pattern strutturale riconosciuto",
    )


def _is_ministeriale_tiap(
    n_units: int, n_pdf: int, has_indexes: bool, total: int,
) -> bool:
    return n_units >= 2 and has_indexes and n_pdf >= 2


def _is_immagini_scansioni(
    n_images: int, n_pdf: int, total: int, has_indexes: bool,
) -> bool:
    if has_indexes or total == 0:
        return False
    return n_images > 0 and n_images / total >= 0.5 and n_pdf <= n_images


def _is_pdf_sciolti(
    n_pdf: int, n_units: int, total: int, has_indexes: bool,
) -> bool:
    if has_indexes or n_units > 0 or total == 0:
        return False
    return n_pdf > 0 and n_pdf / total >= 0.5


def _is_misto(
    n_pdf: int, n_images: int, n_units: int, total: int,
) -> bool:
    if total == 0:
        return False
    has_pdf = n_pdf > 0
    has_images = n_images > 0
    has_units = n_units > 0
    if has_pdf and has_images:
        return True
    if has_units and (n_pdf + n_images) < total:
        return True
    return False


def _count_images(documents: tuple[CaseFileDocument, ...]) -> int:
    return sum(1 for d in documents if d.extension in _IMAGE_EXTENSIONS)


def _has_attachment_indexes(documents: tuple[CaseFileDocument, ...]) -> bool:
    return any(d.filename == ATTACHMENT_INDEX_FILENAME for d in documents)
