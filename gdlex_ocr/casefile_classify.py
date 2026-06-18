"""Filename-only document classification for local case folders."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdlex_ocr.casefile import DocumentType

SOURCE_FILENAME = "filename"
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

_SEPARATORS_RE = re.compile(r"[^a-z0-9]+")


def classify_by_filename(filename: str) -> tuple["DocumentType", str, str]:
    """Classify a document using only its filename or relative path."""
    from gdlex_ocr.casefile import DocumentType

    normalized = _normalize_filename(filename)
    tokens = set(normalized.split())

    if "sentenza" in tokens or "sent" in tokens:
        return (DocumentType.SENTENZA, CONFIDENCE_HIGH, SOURCE_FILENAME)
    if "ordinanza" in tokens or "ord" in tokens:
        return (DocumentType.ORDINANZA, CONFIDENCE_HIGH, SOURCE_FILENAME)
    if "decreto" in tokens or "decr" in tokens:
        return (DocumentType.DECRETO, CONFIDENCE_HIGH, SOURCE_FILENAME)
    if (
        "verbale" in tokens
        or ("verb" in tokens and "ud" in tokens)
        or ("verbale" in normalized and "udienza" in normalized)
    ):
        return (
            DocumentType.VERBALE_UDIENZA,
            CONFIDENCE_HIGH,
            SOURCE_FILENAME,
        )
    if "udienza" in tokens:
        return (
            DocumentType.VERBALE_UDIENZA,
            CONFIDENCE_MEDIUM,
            SOURCE_FILENAME,
        )
    if (
        "memoria" in tokens
        or _contains_phrase(normalized, "note difensive")
        or _contains_phrase(normalized, "note autorizzate")
    ):
        return (DocumentType.MEMORIA, CONFIDENCE_MEDIUM, SOURCE_FILENAME)
    if "istanza" in tokens or "richiesta" in tokens:
        return (DocumentType.ISTANZA, CONFIDENCE_MEDIUM, SOURCE_FILENAME)
    if "allegato" in tokens or "all" in tokens:
        return (DocumentType.ALLEGATO, CONFIDENCE_LOW, SOURCE_FILENAME)
    return (DocumentType.SCONOSCIUTO, CONFIDENCE_LOW, SOURCE_FILENAME)


def _normalize_filename(filename: str) -> str:
    path_without_extension = PurePosixPath(filename.replace("\\", "/")).with_suffix("")
    decomposed = unicodedata.normalize("NFKD", str(path_without_extension).casefold())
    without_accents = "".join(
        char
        for char in decomposed
        if not unicodedata.combining(char)
    )
    return _SEPARATORS_RE.sub(" ", without_accents).strip()


def _contains_phrase(normalized: str, phrase: str) -> bool:
    return f" {phrase} " in f" {normalized} "
