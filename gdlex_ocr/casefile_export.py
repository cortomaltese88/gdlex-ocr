"""Privacy-safe JSON-ready case-file export primitives."""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from posixpath import basename
from typing import Any
from urllib.parse import unquote, urlsplit

from gdlex_ocr.casefile import (
    CaseFileAnalysis,
    CaseFileDocument,
    CaseFileIndex,
    ExtractionWarning,
)
from gdlex_ocr.casefile_index import CaseFileIndexEntry, CaseFileIndexMatch

_MAX_LABEL_LENGTH = 160
_MAX_WARNING_MESSAGE_LENGTH = 240
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[a-zA-Z]:/")
_POSIX_ABSOLUTE_TOKEN_RE = re.compile(r"(?<!\S)/(?:[^\s:;,)]+/)*[^\s:;,)]+")
_WINDOWS_ABSOLUTE_TOKEN_RE = re.compile(
    r"(?<!\S)[a-zA-Z]:[\\/](?:[^\s:;,)]+[\\/])*[^\s:;,)]+"
)


def default_casefile_json_path(output_dir: Path) -> Path:
    return Path(output_dir) / "fascicolo_index.json"


def write_casefile_analysis_json(
    analysis: CaseFileAnalysis,
    output_path: Path,
    *,
    indent: int = 2,
) -> Path:
    path = Path(output_path)
    if path.is_dir():
        raise IsADirectoryError(f"Il percorso di output è una cartella: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = casefile_analysis_to_dict(analysis)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )
    return output_path


def casefile_analysis_to_dict(analysis: CaseFileAnalysis) -> dict[str, object]:
    """Return a JSON-safe, privacy-safe mapping for a case-file analysis."""
    documents = [
        casefile_document_to_dict(document)
        for document in analysis.documents
    ]
    indexes = [
        casefile_index_to_dict(index)
        for index in analysis.indexes
    ]
    warnings = [
        casefile_warning_to_dict(warning)
        for warning in analysis.warnings
    ]

    return {
        "source_dir": _safe_source_dir(analysis.source_dir),
        "summary": {
            "total_files": int(analysis.total_files),
            "total_pdf_files": int(analysis.total_pdf_files),
            "total_non_pdf_files": int(analysis.total_non_pdf_files),
            "total_indexes": len(indexes),
            "total_index_entries": sum(
                len(index["entries"]) for index in indexes
            ),
            "total_index_matches": sum(
                len(entry["matches"])
                for index in indexes
                for entry in index["entries"]
            ),
            "total_warnings": _count_warnings(analysis),
        },
        "documents": documents,
        "indexes": indexes,
        "warnings": warnings,
    }


def casefile_warning_to_dict(warning: ExtractionWarning) -> dict[str, object]:
    return {
        "code": str(warning.code),
        "message": _short_warning_message(warning.message),
        "path": _safe_optional_path(warning.path),
    }


def casefile_document_to_dict(document: CaseFileDocument) -> dict[str, object]:
    return {
        "id": str(document.id),
        "filename": _safe_filename(document.filename),
        "relative_path": _safe_path(document.relative_path),
        "extension": str(document.extension),
        "size_bytes": int(document.size_bytes),
        "file_order": document.file_order,
        "document_type": _safe_enum_value(document.document_type),
        "type_confidence": str(document.type_confidence),
        "type_source": str(document.type_source),
        "sha256": document.sha256,
        "page_count": document.page_count,
        "is_searchable": document.is_searchable,
        "markdown_path": _safe_optional_path(document.markdown_path),
        "judgment_analysis_path": _safe_optional_path(
            document.judgment_analysis_path
        ),
        "warnings": [
            casefile_warning_to_dict(warning)
            for warning in document.warnings
        ],
    }


def casefile_index_to_dict(index: CaseFileIndex) -> dict[str, object]:
    return {
        "relative_path": _safe_path(index.relative_path),
        "extension": str(index.extension),
        "confidence": str(index.confidence),
        "source": str(index.source),
        "detected_format": str(index.detected_format),
        "entries": [
            casefile_index_entry_to_dict(entry)
            for entry in index.entries
        ],
        "warnings": [
            casefile_warning_to_dict(warning)
            for warning in index.warnings
        ],
    }


def casefile_index_entry_to_dict(entry: CaseFileIndexEntry) -> dict[str, object]:
    return {
        "row_number": int(entry.row_number),
        "label": _short_label(entry.label),
        "referenced_path": _safe_optional_path(entry.referenced_path),
        "document_date": entry.document_date,
        "document_type_hint": entry.document_type_hint,
        "confidence": str(entry.confidence),
        "source": str(entry.source),
        "matches": [
            casefile_index_match_to_dict(match)
            for match in entry.matches
        ],
        "warnings": [
            casefile_warning_to_dict(warning)
            for warning in entry.warnings
        ],
    }


def casefile_index_match_to_dict(match: CaseFileIndexMatch) -> dict[str, object]:
    return {
        "entry_row_number": int(match.entry_row_number),
        "document_id": str(match.document_id),
        "entry_reference": _safe_optional_path(match.entry_reference),
        "matched_relative_path": _safe_path(match.matched_relative_path),
        "confidence": str(match.confidence),
        "strategy": str(match.strategy),
        "warnings": [
            casefile_warning_to_dict(warning)
            for warning in match.warnings
        ],
    }


def _count_warnings(analysis: CaseFileAnalysis) -> int:
    total = len(analysis.warnings)
    total += sum(len(document.warnings) for document in analysis.documents)
    for index in analysis.indexes:
        total += len(index.warnings)
        for entry in index.entries:
            total += len(entry.warnings)
            total += sum(len(match.warnings) for match in entry.matches)
    return total


def _safe_source_dir(value: str) -> str:
    normalized = _normalize_path_text(value)
    return basename(normalized.rstrip("/")) or Path(value).name or "."


def _safe_optional_path(value: str | None) -> str | None:
    if value is None:
        return None
    return _safe_path(value)


def _safe_path(value: str) -> str:
    normalized = _normalize_path_text(value)
    parsed = urlsplit(value.strip())
    if parsed.scheme or parsed.netloc or _is_absolute_path(normalized):
        return basename(normalized.rstrip("/")) or basename(parsed.path) or ""
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _safe_filename(value: str) -> str:
    return basename(_normalize_path_text(value).rstrip("/")) or value


def _normalize_path_text(value: str) -> str:
    parsed = urlsplit(value.strip().replace("\\", "/"))
    path = parsed.path if parsed.path else value
    return unquote(path).strip().replace("\\", "/")


def _is_absolute_path(value: str) -> bool:
    return value.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(value) is not None


def _safe_enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _short_label(value: str) -> str:
    return _truncate(_clean_text(value), _MAX_LABEL_LENGTH)


def _short_warning_message(value: str) -> str:
    message = _clean_text(value)
    message = _WINDOWS_ABSOLUTE_TOKEN_RE.sub(
        lambda match: basename(_normalize_path_text(match.group(0))),
        message,
    )
    message = _POSIX_ABSOLUTE_TOKEN_RE.sub(
        lambda match: basename(_normalize_path_text(match.group(0))),
        message,
    )
    return _truncate(message, _MAX_WARNING_MESSAGE_LENGTH)


def _clean_text(value: str) -> str:
    return " ".join(str(value).split())


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."
