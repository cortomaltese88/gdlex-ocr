"""Filename-only case-file index detection and light index parsing."""

from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from posixpath import basename
from typing import Iterable
from urllib.parse import urlsplit

from gdlex_ocr.casefile import CaseFileIndex, ExtractionWarning
from gdlex_ocr.casefile_classify import classify_by_filename

MULTIPLE_CASEFILE_INDEXES_WARNING = "multiple_casefile_indexes"
INDEX_TOO_LARGE_WARNING = "index_too_large"
INDEX_PARSE_ERROR_WARNING = "index_parse_error"

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
    except (OSError, UnicodeError, csv.Error, ET.ParseError, ValueError) as exc:
        return _with_index_warning(
            index,
            INDEX_PARSE_ERROR_WARNING,
            "Parsing leggero dell'indice fascicolo non riuscito",
            exc,
        )

    return replace(index, entries=entries)


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
        referenced_path = _first_pdf_path(" ".join(cells))
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
        referenced_path = href.strip()
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
        referenced_path = _first_pdf_path(row)
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
            referenced_path = _first_pdf_path(value)
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
    referenced_path = _first_pdf_path(line)
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
