"""Filename-only case-file index detection and light index parsing."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from posixpath import basename
from typing import Callable, Iterable
from urllib.parse import unquote, urlsplit

import defusedxml.ElementTree as ET
from defusedxml.common import DefusedXmlException

from gdlex_ocr.casefile import (
    ATTACHMENT_INDEX_FILENAME,
    CaseFileDocument,
    CaseFileIndex,
    ExtractionWarning,
)
from gdlex_ocr.casefile_classify import classify_by_filename

MULTIPLE_CASEFILE_INDEXES_WARNING = "multiple_casefile_indexes"
INDEX_TOO_LARGE_WARNING = "index_too_large"
INDEX_PARSE_ERROR_WARNING = "index_parse_error"
AMBIGUOUS_INDEX_MATCH_WARNING = "ambiguous_index_match"
UNMATCHED_INDEX_ENTRY_WARNING = "unmatched_index_entry"

_INDEX_EXTENSIONS = {".html", ".htm", ".xml", ".txt", ".csv"}
_HIGH_TERMS = ("indice", "index")
_MEDIUM_TERMS = ("fascicolo", "elenco", "documenti", "atti")
_LOW_TERMS = ("pdp", "tiap")
_ALL_TERMS = _HIGH_TERMS + _MEDIUM_TERMS + _LOW_TERMS
_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
_MAX_INDEX_SIZE_BYTES = 2 * 1024 * 1024
_MAX_LABEL_LENGTH = 160
_MIN_TEXT_LABEL_LENGTH = 4
_DATE_RE = re.compile(
    r"\b(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b"
)
_PDF_PATH_RE = re.compile(r"(?i)([^\s\"'<>;]+?\.pdf)\b")
_ABSOLUTE_REFERENCE_RE = re.compile(r"^(?:/|[a-zA-Z]:[\\/])")
_BASENAME_SEPARATOR_RE = re.compile(r"[\s_-]+")


@dataclass(frozen=True, slots=True)
class CaseFileIndexMatch:
    entry_row_number: int
    document_id: str
    entry_reference: str | None
    matched_relative_path: str
    confidence: str
    strategy: str
    warnings: tuple[ExtractionWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseFileIndexEntry:
    row_number: int
    label: str
    referenced_path: str | None
    document_date: str | None
    document_type_hint: str | None
    confidence: str
    source: str
    warnings: tuple[ExtractionWarning, ...] = ()
    matches: tuple[CaseFileIndexMatch, ...] = ()


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


def parse_detected_indexes(
    folder: Path,
    indexes: Iterable[CaseFileIndex],
) -> tuple[CaseFileIndex, ...]:
    """Parse already detected index files without affecting folder analysis."""
    root = Path(folder).expanduser().resolve()
    return tuple(parse_casefile_index(root, index) for index in indexes)


def match_index_entries_to_documents(
    indexes: Iterable[CaseFileIndex],
    documents: Iterable[CaseFileDocument],
) -> tuple[CaseFileIndex, ...]:
    """Attach conservative, in-memory index-entry matches to documents."""
    document_tuple = tuple(documents)
    exact_paths = _group_documents(
        document_tuple,
        lambda document: _normalize_reference_path(document.relative_path).casefold(),
    )
    exact_basenames = _group_documents(
        document_tuple,
        lambda document: _reference_basename(document.relative_path).casefold(),
    )
    normalized_basenames = _group_documents(
        document_tuple,
        lambda document: _normalize_basename(document.relative_path),
    )

    matched_indexes: list[CaseFileIndex] = []
    for index in indexes:
        entries = tuple(
            _match_index_entry(
                entry,
                exact_paths,
                exact_basenames,
                normalized_basenames,
            )
            for entry in index.entries
        )
        matched_indexes.append(replace(index, entries=entries))
    return tuple(matched_indexes)


def parse_casefile_index(folder: Path, index: CaseFileIndex) -> CaseFileIndex:
    """Populate lightweight entries for one detected index file, if possible."""
    root = Path(folder).expanduser().resolve()
    path = root / index.relative_path

    try:
        path.resolve().relative_to(root)
        size_bytes = path.stat().st_size
    except (OSError, ValueError) as exc:
        return _with_index_warning(
            index,
            INDEX_PARSE_ERROR_WARNING,
            "Impossibile leggere l'indice fascicolo",
            exc,
        )

    if size_bytes > _MAX_INDEX_SIZE_BYTES:
        return _with_index_warning(
            index,
            INDEX_TOO_LARGE_WARNING,
            "Indice fascicolo oltre il limite prudente di lettura",
        )

    try:
        payload = path.read_bytes()
        text = _decode_index_payload(payload)
        entries = _parse_index_text(index.detected_format, text)
    except (
        OSError,
        UnicodeError,
        csv.Error,
        ET.ParseError,
        DefusedXmlException,
        ValueError,
    ) as exc:
        return _with_index_warning(
            index,
            INDEX_PARSE_ERROR_WARNING,
            "Parsing leggero dell'indice fascicolo non riuscito",
            exc,
        )

    return replace(index, entries=entries)


def _match_index_entry(
    entry: CaseFileIndexEntry,
    exact_paths: dict[str, tuple[CaseFileDocument, ...]],
    exact_basenames: dict[str, tuple[CaseFileDocument, ...]],
    normalized_basenames: dict[str, tuple[CaseFileDocument, ...]],
) -> CaseFileIndexEntry:
    if entry.referenced_path is None:
        return replace(entry, matches=())

    reference_path = _normalize_reference_path(entry.referenced_path)
    candidates = exact_paths.get(reference_path.casefold(), ())
    matched = _match_candidates(
        entry,
        candidates,
        strategy="relative_path_exact",
        unique_confidence="high",
        ambiguous_message="Riferimento indice ambiguo sul percorso relativo",
    )
    if matched is not None:
        return matched

    reference_basename = _reference_basename(reference_path)
    candidates = exact_basenames.get(reference_basename.casefold(), ())
    matched = _match_candidates(
        entry,
        candidates,
        strategy="basename_exact",
        unique_confidence="high",
        ambiguous_message="Riferimento indice ambiguo sul nome file",
    )
    if matched is not None:
        return matched

    normalized_basename = _normalize_basename(reference_path)
    candidates = normalized_basenames.get(normalized_basename, ())
    matched = _match_candidates(
        entry,
        candidates,
        strategy="normalized_basename",
        unique_confidence="medium",
        ambiguous_message="Riferimento indice ambiguo sul nome file normalizzato",
    )
    if matched is not None:
        return matched

    return _entry_with_warning(
        entry,
        UNMATCHED_INDEX_ENTRY_WARNING,
        "Voce indice non collegata ad alcun documento",
    )


def _match_candidates(
    entry: CaseFileIndexEntry,
    candidates: tuple[CaseFileDocument, ...],
    *,
    strategy: str,
    unique_confidence: str,
    ambiguous_message: str,
) -> CaseFileIndexEntry | None:
    if not candidates:
        return None
    if len(candidates) > 1:
        return _entry_with_warning(
            entry,
            AMBIGUOUS_INDEX_MATCH_WARNING,
            ambiguous_message,
        )

    document = candidates[0]
    match = CaseFileIndexMatch(
        entry_row_number=entry.row_number,
        document_id=document.id,
        entry_reference=_safe_entry_reference(entry.referenced_path),
        matched_relative_path=document.relative_path,
        confidence=unique_confidence,
        strategy=strategy,
    )
    return replace(entry, matches=(match,))


def _entry_with_warning(
    entry: CaseFileIndexEntry,
    code: str,
    message: str,
) -> CaseFileIndexEntry:
    warning = ExtractionWarning(
        code=code,
        message=message,
        path=_safe_entry_reference(entry.referenced_path),
    )
    return replace(entry, warnings=entry.warnings + (warning,), matches=())


def _group_documents(
    documents: tuple[CaseFileDocument, ...],
    key_factory: Callable[[CaseFileDocument], str],
) -> dict[str, tuple[CaseFileDocument, ...]]:
    grouped: dict[str, list[CaseFileDocument]] = {}
    for document in documents:
        key = key_factory(document)
        grouped.setdefault(key, []).append(document)
    return {key: tuple(values) for key, values in grouped.items()}


def _normalize_reference_path(value: str) -> str:
    parsed = urlsplit(value.strip().replace("\\", "/"))
    path = parsed.path if parsed.path else value
    return unquote(path).strip().replace("\\", "/")


def _reference_basename(value: str) -> str:
    return basename(_normalize_reference_path(value))


def _normalize_basename(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", _reference_basename(value))
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    folded = without_accents.casefold()
    return _BASENAME_SEPARATOR_RE.sub(" ", folded).strip()


def _safe_entry_reference(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_reference_path(value)
    parsed = urlsplit(value.strip())
    if parsed.scheme or parsed.netloc or _ABSOLUTE_REFERENCE_RE.match(normalized):
        return _safe_basename(normalized) or None
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if _has_parent_segment(normalized):
        return _safe_basename(normalized) or None
    return normalized or None


def _has_parent_segment(value: str) -> bool:
    return ".." in value.replace("\\", "/").split("/")


def _safe_basename(value: str) -> str:
    normalized = _normalize_reference_path(value).rstrip("/")
    for part in reversed(normalized.split("/")):
        if part and part not in {".", ".."}:
            return part
    return ""


def _detect_index(root: Path, path: Path) -> CaseFileIndex | None:
    absolute_path = path if path.is_absolute() else root / path
    extension = absolute_path.suffix.lower()
    if extension not in _INDEX_EXTENSIONS:
        return None

    if absolute_path.name == ATTACHMENT_INDEX_FILENAME:
        relative = _relative_path(root, absolute_path)
        parent = absolute_path.parent.name
        confidence = "high" if re.match(r"^\d+$", parent) else "medium"
        return CaseFileIndex(
            relative_path=relative,
            extension=extension,
            confidence=confidence,
            source="filename",
            detected_format=_detected_format(extension),
        )

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


def _decode_index_payload(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1")


def _parse_index_text(
    detected_format: str,
    text: str,
) -> tuple[CaseFileIndexEntry, ...]:
    if detected_format == "csv":
        return _parse_csv_index(text)
    if detected_format == "html":
        return _parse_html_index(text)
    if detected_format == "xml":
        return _parse_xml_index(text)
    return _parse_text_index(text)


def _parse_text_index(text: str) -> tuple[CaseFileIndexEntry, ...]:
    entries: list[CaseFileIndexEntry] = []
    for line in text.splitlines():
        entry = _entry_from_text(line, len(entries) + 1, source="text")
        if entry is not None:
            entries.append(entry)
    return tuple(entries)


def _parse_csv_index(text: str) -> tuple[CaseFileIndexEntry, ...]:
    entries: list[CaseFileIndexEntry] = []
    reader = csv.reader(StringIO(text), delimiter=_sniff_csv_delimiter(text))
    for row in reader:
        cells = [_clean_text(cell) for cell in row]
        if not any(cells) or _is_probable_csv_header(cells, entries):
            continue
        referenced_path = _safe_entry_reference(_first_pdf_path(" ".join(cells)))
        label = _csv_label(cells, referenced_path)
        if label is None:
            continue
        entries.append(
            CaseFileIndexEntry(
                row_number=len(entries) + 1,
                label=label,
                referenced_path=referenced_path,
                document_date=_first_date(" ".join(cells)),
                document_type_hint=_document_type_hint(
                    referenced_path or label
                ),
                confidence="medium" if referenced_path else "low",
                source="csv",
            )
        )
    return tuple(entries)


def _parse_html_index(text: str) -> tuple[CaseFileIndexEntry, ...]:
    parser = _LightHtmlIndexParser()
    parser.feed(text)
    parser.close()

    entries: list[CaseFileIndexEntry] = []
    seen_paths: set[str] = set()

    for href, link_text in parser.links:
        if ".pdf" not in href.casefold():
            continue
        referenced_path = _safe_entry_reference(href)
        if referenced_path is None:
            continue
        seen_paths.add(referenced_path)
        label = _short_label(link_text) or _basename_label(referenced_path)
        entries.append(
            CaseFileIndexEntry(
                row_number=len(entries) + 1,
                label=label,
                referenced_path=referenced_path,
                document_date=_first_date(f"{link_text} {href}"),
                document_type_hint=_document_type_hint(
                    referenced_path or label
                ),
                confidence="high",
                source="html",
            )
        )

    for row in parser.rows:
        referenced_path = _safe_entry_reference(_first_pdf_path(row))
        if referenced_path is None or referenced_path in seen_paths:
            continue
        entry = _entry_from_text(
            row,
            len(entries) + 1,
            source="html",
            confidence="low",
        )
        if entry is not None:
            entries.append(entry)

    return tuple(entries)


def _parse_xml_index(text: str) -> tuple[CaseFileIndexEntry, ...]:
    root = ET.fromstring(text)
    entries: list[CaseFileIndexEntry] = []
    seen_paths: set[str] = set()

    for element in root.iter():
        element_text = _clean_text(" ".join(element.itertext()))
        for value in (*element.attrib.values(), element_text):
            referenced_path = _safe_entry_reference(_first_pdf_path(value))
            if referenced_path is None or referenced_path in seen_paths:
                continue
            seen_paths.add(referenced_path)
            label = _short_label(element_text) or _basename_label(referenced_path)
            entries.append(
                CaseFileIndexEntry(
                    row_number=len(entries) + 1,
                    label=label,
                    referenced_path=referenced_path,
                    document_date=_first_date(f"{element_text} {value}"),
                    document_type_hint=_document_type_hint(
                        referenced_path or label
                    ),
                    confidence="medium",
                    source="xml",
                )
            )

    return tuple(entries)


def _entry_from_text(
    line: str,
    row_number: int,
    *,
    source: str,
    confidence: str | None = None,
) -> CaseFileIndexEntry | None:
    label = _short_label(line)
    referenced_path = _safe_entry_reference(_first_pdf_path(line))
    if referenced_path is None and len(label) < _MIN_TEXT_LABEL_LENGTH:
        return None
    if not label and referenced_path is not None:
        label = _basename_label(referenced_path)

    return CaseFileIndexEntry(
        row_number=row_number,
        label=label,
        referenced_path=referenced_path,
        document_date=_first_date(line),
        document_type_hint=_document_type_hint(referenced_path or label),
        confidence=confidence or ("medium" if referenced_path else "low"),
        source=source,
    )


class _LightHtmlIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.rows: list[str] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []
        self._in_row = False
        self._row_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() == "a":
            attributes = dict(attrs)
            self._link_href = attributes.get("href")
            self._link_text = []
        elif tag.casefold() == "tr":
            self._in_row = True
            self._row_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._link_href is not None:
            self.links.append((self._link_href, _clean_text(" ".join(self._link_text))))
            self._link_href = None
            self._link_text = []
        elif tag.casefold() == "tr" and self._in_row:
            row = _clean_text(" ".join(self._row_text))
            if row:
                self.rows.append(row)
            self._in_row = False
            self._row_text = []

    def handle_data(self, data: str) -> None:
        if self._link_href is not None:
            self._link_text.append(data)
        if self._in_row:
            self._row_text.append(data)


def _sniff_csv_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:5])
    return ";" if sample.count(";") > sample.count(",") else ","


def _is_probable_csv_header(
    cells: list[str],
    entries: list[CaseFileIndexEntry],
) -> bool:
    if entries:
        return False
    normalized = {cell.casefold() for cell in cells if cell}
    header_terms = {
        "data",
        "date",
        "documento",
        "file",
        "filename",
        "nome",
        "path",
        "percorso",
        "tipo",
    }
    return bool(normalized & header_terms) and _first_pdf_path(" ".join(cells)) is None


def _csv_label(cells: list[str], referenced_path: str | None) -> str | None:
    if referenced_path is not None:
        for cell in cells:
            if referenced_path in cell:
                return _short_label(cell) or _basename_label(referenced_path)
    significant = [cell for cell in cells if cell]
    if not significant:
        return None
    return _short_label(" - ".join(significant[:4]))


def _first_pdf_path(text: str) -> str | None:
    match = _PDF_PATH_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip(".,:;()[]{}")


def _first_date(text: str) -> str | None:
    match = _DATE_RE.search(text)
    if match is None:
        return None
    return match.group(0)


def _document_type_hint(value: str) -> str | None:
    document_type, confidence, _source = classify_by_filename(value)
    if confidence == "low" and document_type.value == "sconosciuto":
        return None
    return document_type.value


def _basename_label(path: str) -> str:
    parsed_path = urlsplit(path).path
    return _short_label(basename(parsed_path) or path)


def _short_label(text: str) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= _MAX_LABEL_LENGTH:
        return cleaned
    return f"{cleaned[: _MAX_LABEL_LENGTH - 3]}..."


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _with_index_warning(
    index: CaseFileIndex,
    code: str,
    message: str,
    exc: BaseException | None = None,
) -> CaseFileIndex:
    if exc is not None:
        message = f"{message}: {exc.__class__.__name__}"
    warning = ExtractionWarning(
        code=code,
        message=message,
        path=index.relative_path,
    )
    return replace(
        index,
        warnings=index.warnings + (warning,),
        entries=(),
    )


# ---------------------------------------------------------------------------
# Ministerial ListaAllegati.html metadata extraction
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(
    r"Documento\s*:\s*(\d{1,4})\s*-\s*(.+)",
    re.IGNORECASE,
)
_METADATA_PRIVACY_KEYS = frozenset({
    "soggetto cognome/nome",
    "indagato",
})

_FALDONE_NUMBER_RE = re.compile(r"\d+")
_PG_PROGRESSIVE_RE = re.compile(
    r"[Nn]\s*\d+/\d+-(\d+)(?:/\d{4})?\b"
)


@dataclass(frozen=True, slots=True)
class AttachmentIndexMetadata:
    act_title: str | None = None
    act_number: str | None = None
    description: str | None = None
    index_date: str | None = None
    faldone: str | None = None
    faldone_number: int | None = None
    total_pages: int | None = None
    insertion_date: str | None = None
    pg_protocol: str | None = None
    pg_progressive: int | None = None
    notes: str | None = None
    extra_description: str | None = None


def parse_attachment_index_metadata(html: str) -> AttachmentIndexMetadata:
    """Extract privacy-safe act metadata from a ministerial ListaAllegati.html."""
    parser = _AttachmentMetadataParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return AttachmentIndexMetadata()

    act_title: str | None = None
    act_number: str | None = None
    if parser.title:
        match = _TITLE_RE.search(parser.title)
        if match:
            act_number = match.group(1)
            act_title = _clean_text(match.group(2))

    index_date: str | None = None
    faldone: str | None = None
    faldone_number: int | None = None
    total_pages: int | None = None
    insertion_date: str | None = None
    pg_protocol: str | None = None
    pg_progressive: int | None = None
    notes: str | None = None
    extra_description: str | None = None

    for key, value in parser.metadata:
        key_lower = key.casefold().strip()
        candidate = _clean_text(value)
        if not candidate:
            continue

        if key_lower == "data":
            index_date = candidate
        elif key_lower == "faldone":
            faldone = candidate
            faldone_number = _extract_faldone_number(candidate)
        elif key_lower == "tot. pagine":
            try:
                total_pages = int(candidate)
            except ValueError:
                pass
        elif key_lower == "data inserimento":
            insertion_date = candidate
        elif key_lower == "nr. fascicolo":
            pg_protocol = _short_label(candidate)
            pg_progressive = _extract_pg_progressive(candidate)
        elif key_lower in {"note", "note:"}:
            notes = _short_label(candidate)
        elif key_lower == "altro":
            extra_description = _short_label(candidate)
        elif key_lower in _METADATA_PRIVACY_KEYS:
            pass
        else:
            if extra_description is None:
                extra_description = _short_label(candidate)

    description = pg_protocol or extra_description or notes

    return AttachmentIndexMetadata(
        act_title=act_title,
        act_number=act_number,
        description=description,
        index_date=index_date,
        faldone=faldone,
        faldone_number=faldone_number,
        total_pages=total_pages,
        insertion_date=insertion_date,
        pg_protocol=pg_protocol,
        pg_progressive=pg_progressive,
        notes=notes,
        extra_description=extra_description,
    )


def _extract_faldone_number(raw: str) -> int | None:
    """Normalize faldone number from patterns like 'FALDONE 1-FALDONE 1'."""
    numbers = _FALDONE_NUMBER_RE.findall(raw)
    if not numbers:
        return None
    return int(numbers[0])


def _extract_pg_progressive(raw: str) -> int | None:
    """Extract progressive number from PG protocol, e.g. 'N 266/3-16/2024' → 16."""
    match = _PG_PROGRESSIVE_RE.search(raw)
    if match is None:
        return None
    return int(match.group(1))


class _AttachmentMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self.metadata: list[tuple[str, str]] = []
        self._in_title = False
        self._title_parts: list[str] = []
        self._in_strong = False
        self._strong_text: list[str] = []
        self._in_li = False
        self._li_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lower = tag.casefold()
        if lower == "title":
            self._in_title = True
            self._title_parts = []
        elif lower == "strong":
            self._in_strong = True
            self._strong_text = []
        elif lower == "li":
            self._in_li = True
            self._li_text = []

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if lower == "title" and self._in_title:
            self.title = _clean_text(" ".join(self._title_parts))
            self._in_title = False
        elif lower == "strong" and self._in_strong:
            self._in_strong = False
        elif lower == "li" and self._in_li:
            key = _clean_text(" ".join(self._strong_text))
            full_text = _clean_text(" ".join(self._li_text))
            if key and full_text:
                sep = f"{key} :"
                idx = full_text.find(sep)
                if idx >= 0:
                    value = full_text[idx + len(sep):].strip()
                else:
                    value = full_text[len(key):].strip().lstrip(":")
                self.metadata.append((key, value))
            self._in_li = False
            self._strong_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._in_strong:
            self._strong_text.append(data)
        if self._in_li:
            self._li_text.append(data)
