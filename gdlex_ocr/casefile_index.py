"""Filename-only case-file index detection."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from gdlex_ocr.casefile import CaseFileIndex

MULTIPLE_CASEFILE_INDEXES_WARNING = "multiple_casefile_indexes"

_INDEX_EXTENSIONS = {".html", ".htm", ".xml", ".txt", ".csv"}
_HIGH_TERMS = ("indice", "index")
_MEDIUM_TERMS = ("fascicolo", "elenco", "documenti", "atti")
_LOW_TERMS = ("pdp", "tiap")
_ALL_TERMS = _HIGH_TERMS + _MEDIUM_TERMS + _LOW_TERMS
_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def detect_casefile_indexes(
    folder: Path,
    paths: Iterable[Path],
) -> tuple[CaseFileIndex, ...]:
    """Detect possible fascicolo index files from already discovered paths."""
    root = Path(folder).expanduser().resolve()
    indexes = [
        index
        for path in paths
        if (index := _detect_index(root, Path(path))) is not None
    ]
    return tuple(
        sorted(
            indexes,
            key=lambda index: (
                _CONFIDENCE_ORDER[index.confidence],
                index.relative_path.casefold(),
                index.relative_path,
            ),
        )
    )


def _detect_index(root: Path, path: Path) -> CaseFileIndex | None:
    absolute_path = path if path.is_absolute() else root / path
    extension = absolute_path.suffix.lower()
    if extension not in _INDEX_EXTENSIONS:
        return None

    filename = absolute_path.stem.casefold()
    confidence = _detect_confidence(filename, extension)
    if confidence is None:
        return None

    return CaseFileIndex(
        relative_path=_relative_path(root, absolute_path),
        extension=extension,
        confidence=confidence,
        source="filename",
        detected_format=_detected_format(extension),
    )


def _detect_confidence(
    filename: str,
    extension: str,
) -> str | None:
    if extension in {".html", ".htm", ".xml"} and _has_any(filename, _HIGH_TERMS):
        return "high"
    if _has_any(filename, _MEDIUM_TERMS):
        return "medium"
    if _has_any(filename, _ALL_TERMS):
        return "low"
    return None


def _has_any(filename: str, candidates: tuple[str, ...]) -> bool:
    return any(candidate in filename for candidate in candidates)


def _detected_format(extension: str) -> str:
    if extension in {".html", ".htm"}:
        return "html"
    if extension == ".xml":
        return "xml"
    if extension == ".txt":
        return "text"
    if extension == ".csv":
        return "csv"
    return "unknown"


def _relative_path(root: Path, path: Path) -> str:
    absolute_path = path if path.is_absolute() else root / path
    return absolute_path.relative_to(root).as_posix()
