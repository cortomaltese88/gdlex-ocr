"""Privacy-safe JSON, Markdown and CSV case-file export primitives."""

from __future__ import annotations

import csv
import io
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
    CaseFileUnit,
    DocumentType,
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
    units = [
        casefile_unit_to_dict(unit)
        for unit in analysis.units
    ]
    total_technical = sum(
        1
        for doc in analysis.documents
        if doc.document_type == DocumentType.MARKER_TECNICO
    )

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
            "total_units": len(units),
            "total_technical_files": total_technical,
        },
        "documents": documents,
        "indexes": indexes,
        "warnings": warnings,
        "units": units,
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


def casefile_unit_to_dict(unit: CaseFileUnit) -> dict[str, object]:
    return {
        "unit_id": str(unit.unit_id),
        "relative_dir": _safe_path(unit.relative_dir),
        "main_pdf_path": _safe_optional_path(unit.main_pdf_path),
        "attachment_index_path": _safe_optional_path(unit.attachment_index_path),
        "complete_marker_path": _safe_optional_path(unit.complete_marker_path),
        "total_files": int(unit.total_files),
        "total_pdf_files": int(unit.total_pdf_files),
        "total_non_pdf_files": int(unit.total_non_pdf_files),
        "size_bytes": int(unit.size_bytes),
        "warnings": [
            casefile_warning_to_dict(warning)
            for warning in unit.warnings
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
        return _safe_basename(normalized) or _safe_basename(parsed.path)
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if _has_parent_segment(normalized):
        return _safe_basename(normalized)
    return normalized


def _safe_filename(value: str) -> str:
    return basename(_normalize_path_text(value).rstrip("/")) or value


def _normalize_path_text(value: str) -> str:
    parsed = urlsplit(value.strip().replace("\\", "/"))
    path = parsed.path if parsed.path else value
    return unquote(path).strip().replace("\\", "/")


def _is_absolute_path(value: str) -> bool:
    return value.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(value) is not None


def _has_parent_segment(value: str) -> bool:
    return ".." in value.replace("\\", "/").split("/")


def _safe_basename(value: str) -> str:
    normalized = _normalize_path_text(value).rstrip("/")
    for part in reversed(normalized.split("/")):
        if part and part not in {".", ".."}:
            return part
    return ""


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
    message = _strip_relative_traversal_tokens(message)
    return _truncate(message, _MAX_WARNING_MESSAGE_LENGTH)


def _strip_relative_traversal_tokens(message: str) -> str:
    return re.sub(
        r"(?<!\S)\S*(?:\.\.[\\/])+\S*",
        lambda match: _safe_path(match.group(0)) or "",
        message,
    )


def _clean_text(value: str) -> str:
    return " ".join(str(value).split())


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

_SHA256_SHORT_LENGTH = 12


def default_casefile_markdown_path(output_dir: Path) -> Path:
    return Path(output_dir) / "fascicolo_index.md"


def format_casefile_analysis_markdown(analysis: CaseFileAnalysis) -> str:
    payload = casefile_analysis_to_dict(analysis)
    summary = payload["summary"]
    lines: list[str] = []

    lines.append("# Indice fascicolo")
    lines.append("")
    lines.append(
        "> Analisi locale euristica."
        " Non esegue OCR e non interpreta il contenuto dei documenti."
    )
    lines.append("")

    # -- Riepilogo --
    lines.append("## Riepilogo")
    lines.append("")
    lines.append(f"- File totali: {summary['total_files']}")
    lines.append(f"- PDF: {summary['total_pdf_files']}")
    lines.append(f"- Non PDF: {summary['total_non_pdf_files']}")
    if summary["total_units"]:
        lines.append(f"- Unità documentali: {summary['total_units']}")
    if summary["total_technical_files"]:
        lines.append(f"- File tecnici: {summary['total_technical_files']}")
    lines.append(f"- Indici rilevati: {summary['total_indexes']}")
    lines.append(f"- Voci indice: {summary['total_index_entries']}")
    lines.append(f"- Match indice-documenti: {summary['total_index_matches']}")
    lines.append(f"- Warning: {summary['total_warnings']}")
    lines.append("")

    # -- Unità documentali PDP/TIAP --
    units = payload["units"]
    if units:
        lines.append("## Unità documentali PDP/TIAP")
        lines.append("")
        lines.append(
            "| # | ID | PDF principale | Dimensione"
            " | Lista allegati | File | Warning |"
        )
        lines.append("|---|----|----------------|------------|----------------|------|---------|")
        for i, unit in enumerate(units, 1):
            uid = _md_escape(str(unit["unit_id"]))
            main_pdf = _md_escape(str(unit["main_pdf_path"] or ""))
            size = _format_size(unit["size_bytes"])
            index_path = _md_escape(str(unit["attachment_index_path"] or ""))
            total = unit["total_files"]
            warn_count = len(unit["warnings"])
            lines.append(
                f"| {i} | {uid} | {main_pdf} | {size}"
                f" | {index_path} | {total} | {warn_count} |"
            )
        lines.append("")

    # -- Documenti --
    lines.append("## Documenti")
    lines.append("")
    documents = payload["documents"]
    if documents:
        lines.append("| # | Tipo | Conf. | File | Dimensione | SHA-256 |")
        lines.append("|---|------|-------|------|------------|---------|")
        for i, doc in enumerate(documents, 1):
            doc_type = _md_escape(str(doc["document_type"]))
            confidence = _md_escape(str(doc["type_confidence"]))
            rel_path = _md_escape(str(doc["relative_path"]))
            size = _format_size(doc["size_bytes"])
            sha_short = (
                str(doc["sha256"])[:_SHA256_SHORT_LENGTH]
                if doc["sha256"]
                else ""
            )
            lines.append(
                f"| {i} | {doc_type} | {confidence}"
                f" | {rel_path} | {size} | {sha_short} |"
            )
    else:
        lines.append("Nessun documento trovato.")
    lines.append("")

    # -- Indici rilevati --
    lines.append("## Indici rilevati")
    lines.append("")
    indexes = payload["indexes"]
    if indexes:
        for idx in indexes:
            idx_path = _md_escape(str(idx["relative_path"]))
            lines.append(f"### {idx_path}")
            lines.append("")
            lines.append(f"- formato: {_md_escape(str(idx['detected_format']))}")
            lines.append(f"- confidenza: {_md_escape(str(idx['confidence']))}")
            lines.append(f"- voci: {len(idx['entries'])}")
            lines.append("")

            entries = idx["entries"]
            if entries:
                lines.append("| Riga | Etichetta | Riferimento | Match |")
                lines.append("|------|-----------|-------------|-------|")
                for entry in entries:
                    row = entry["row_number"]
                    label = _md_escape(str(entry["label"]))
                    ref = _md_escape(str(entry["referenced_path"] or ""))
                    match_count = len(entry["matches"])
                    lines.append(f"| {row} | {label} | {ref} | {match_count} |")
            lines.append("")
    else:
        lines.append("Nessun indice rilevato.")
        lines.append("")

    # -- File più grandi --
    documents = payload["documents"]
    if documents:
        sorted_by_size = sorted(documents, key=lambda d: d["size_bytes"], reverse=True)
        top_n = sorted_by_size[:10]
        lines.append("## File più grandi")
        lines.append("")
        lines.append("| # | File | Dimensione | Tipo |")
        lines.append("|---|------|------------|------|")
        for i, doc in enumerate(top_n, 1):
            rel_path = _md_escape(str(doc["relative_path"]))
            size = _format_size(doc["size_bytes"])
            doc_type = _md_escape(str(doc["document_type"]))
            lines.append(f"| {i} | {rel_path} | {size} | {doc_type} |")
        lines.append("")

    # -- Warning --
    lines.append("## Warning")
    lines.append("")
    warnings = payload["warnings"]
    if warnings:
        for warning in warnings:
            code = _md_escape(str(warning["code"]))
            message = _md_escape(str(warning["message"]))
            lines.append(f"- `{code}`: {message}")
    else:
        lines.append("Nessun warning.")
    lines.append("")

    # -- Riepilogo operativo --
    total_size = sum(int(doc["size_bytes"]) for doc in documents) if documents else 0
    total_entries = summary["total_index_entries"]
    total_matches = summary["total_index_matches"]
    match_pct = (
        f"{total_matches / total_entries * 100:.0f}%"
        if total_entries > 0
        else "n/a"
    )
    lines.append("## Riepilogo operativo")
    lines.append("")
    lines.append(f"- Dimensione totale fascicolo: {_format_size(total_size)}")
    lines.append(f"- Copertura indice: {match_pct} ({total_matches}/{total_entries} voci con match)")
    lines.append(f"- Warning totali: {summary['total_warnings']}")
    if summary["total_units"]:
        lines.append(f"- Unità documentali: {summary['total_units']}")
    lines.append("")

    return "\n".join(lines)


def write_casefile_analysis_markdown(
    analysis: CaseFileAnalysis,
    output_path: Path,
) -> Path:
    path = Path(output_path)
    if path.is_dir():
        raise IsADirectoryError(f"Il percorso di output è una cartella: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    content = format_casefile_analysis_markdown(analysis)
    path.write_text(content, encoding="utf-8")
    return output_path


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def _format_size(size_bytes: object) -> str:
    n = int(size_bytes) if size_bytes is not None else 0
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "#",
    "Tipo",
    "Confidenza",
    "File",
    "Dimensione (byte)",
    "Dimensione",
    "SHA-256",
]


def default_casefile_csv_path(output_dir: Path) -> Path:
    return Path(output_dir) / "fascicolo_index.csv"


def format_casefile_analysis_csv(analysis: CaseFileAnalysis) -> str:
    payload = casefile_analysis_to_dict(analysis)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for i, doc in enumerate(payload["documents"], 1):
        writer.writerow([
            i,
            str(doc["document_type"]),
            str(doc["type_confidence"]),
            str(doc["relative_path"]),
            int(doc["size_bytes"]),
            _format_size(doc["size_bytes"]),
            str(doc["sha256"] or ""),
        ])
    return buf.getvalue()


def write_casefile_analysis_csv(
    analysis: CaseFileAnalysis,
    output_path: Path,
) -> Path:
    path = Path(output_path)
    if path.is_dir():
        raise IsADirectoryError(f"Il percorso di output è una cartella: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    content = format_casefile_analysis_csv(analysis)
    path.write_text(content, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# CSV export – documentary units
# ---------------------------------------------------------------------------

_UNITS_CSV_COLUMNS = [
    "#",
    "ID unità",
    "PDF principale",
    "Dimensione (byte)",
    "Dimensione",
    "ListaAllegati",
    "COMPLETE",
    "File totali",
    "PDF",
    "Non PDF",
    "Warning",
    "SHA-256",
]


def default_casefile_units_csv_path(output_dir: Path) -> Path:
    return Path(output_dir) / "fascicolo_unita.csv"


def format_casefile_units_csv(analysis: CaseFileAnalysis) -> str:
    payload = casefile_analysis_to_dict(analysis)
    doc_sha_by_id: dict[str, str] = {}
    for doc in payload["documents"]:
        if doc["sha256"]:
            doc_sha_by_id[str(doc["id"])] = str(doc["sha256"])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_UNITS_CSV_COLUMNS)
    for i, unit in enumerate(payload["units"], 1):
        main_doc_id = _unit_main_document_id(analysis, str(unit["unit_id"]))
        sha256 = doc_sha_by_id.get(main_doc_id, "") if main_doc_id else ""
        writer.writerow([
            i,
            str(unit["unit_id"]),
            str(unit["main_pdf_path"] or ""),
            int(unit["size_bytes"]),
            _format_size(unit["size_bytes"]),
            str(unit["attachment_index_path"] or ""),
            "sì" if unit["complete_marker_path"] else "",
            int(unit["total_files"]),
            int(unit["total_pdf_files"]),
            int(unit["total_non_pdf_files"]),
            len(unit["warnings"]),
            sha256,
        ])
    return buf.getvalue()


def write_casefile_units_csv(
    analysis: CaseFileAnalysis,
    output_path: Path,
) -> Path:
    path = Path(output_path)
    if path.is_dir():
        raise IsADirectoryError(f"Il percorso di output è una cartella: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    content = format_casefile_units_csv(analysis)
    path.write_text(content, encoding="utf-8")
    return output_path


def _unit_main_document_id(
    analysis: CaseFileAnalysis,
    unit_id: str,
) -> str | None:
    for unit in analysis.units:
        if unit.unit_id == unit_id:
            return unit.main_document_id
    return None
