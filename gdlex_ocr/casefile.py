"""Pure local case-folder scanning primitives."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from gdlex_ocr.casefile_classify import classify_by_filename
from gdlex_ocr.manifest import file_sha256

PDF_EXTENSION = ".pdf"
DUPLICATE_FILE_WARNING = "duplicate_file"
COMPLETE_MARKER_FILENAME = "COMPLETE"
ATTACHMENT_INDEX_FILENAME = "ListaAllegati.html"

_FILE_ORDER_RE = re.compile(r"^(\d{1,6})(?:\D|$)")
_NUMERIC_DIR_RE = re.compile(r"^\d+$")

if TYPE_CHECKING:
    from gdlex_ocr.casefile_index import CaseFileIndexEntry


class DocumentType(Enum):
    SENTENZA = "sentenza"
    ORDINANZA = "ordinanza"
    DECRETO = "decreto"
    VERBALE_UDIENZA = "verbale_udienza"
    MEMORIA = "memoria"
    ISTANZA = "istanza"
    ALLEGATO = "allegato"
    MARKER_TECNICO = "marker_tecnico"
    SCONOSCIUTO = "sconosciuto"


@dataclass(frozen=True, slots=True)
class ExtractionWarning:
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class CaseFileDocument:
    id: str
    filename: str
    relative_path: str
    extension: str
    size_bytes: int
    file_order: int | None
    document_type: DocumentType
    type_confidence: str
    type_source: str
    sha256: str | None = None
    page_count: int | None = None
    is_searchable: bool | None = None
    markdown_path: str | None = None
    judgment_analysis_path: str | None = None
    warnings: tuple[ExtractionWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseFileIndex:
    relative_path: str
    extension: str
    confidence: str
    source: str
    detected_format: str
    warnings: tuple[ExtractionWarning, ...] = ()
    entries: tuple["CaseFileIndexEntry", ...] = ()


@dataclass(frozen=True, slots=True)
class CaseFileUnit:
    unit_id: str
    relative_dir: str
    main_document_id: str | None
    main_pdf_path: str | None
    attachment_index_path: str | None
    complete_marker_path: str | None
    total_files: int
    total_pdf_files: int
    total_non_pdf_files: int
    size_bytes: int
    warnings: tuple[ExtractionWarning, ...] = ()
    act_title: str | None = None
    act_number: str | None = None
    description: str | None = None
    index_date: str | None = None
    act_category: str | None = None
    act_category_confidence: str | None = None
    act_category_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CaseFileAnalysis:
    source_dir: str
    documents: tuple[CaseFileDocument, ...]
    total_files: int
    total_pdf_files: int
    total_non_pdf_files: int
    warnings: tuple[ExtractionWarning, ...]
    indexes: tuple[CaseFileIndex, ...] = ()
    units: tuple[CaseFileUnit, ...] = ()


def scan_directory(folder: Path, *, recursive: bool = True) -> tuple[Path, ...]:
    """Return visible local files from a folder in stable relative-path order."""
    root = _validate_folder(folder)
    if recursive:
        files = tuple(_walk_visible_files(root))
    else:
        files = tuple(
            path
            for path in sorted(root.iterdir(), key=_path_sort_key)
            if not _is_hidden(path)
            and path.is_file()
        )
    return tuple(sorted(files, key=lambda path: _relative_sort_key(root, path)))


def normalize_casefile_documents(
    folder: Path,
    paths: Iterable[Path],
    *,
    compute_hashes: bool = True,
) -> CaseFileAnalysis:
    """Build a privacy-safe case-file index from already discovered paths."""
    from gdlex_ocr.casefile_index import (
        MULTIPLE_CASEFILE_INDEXES_WARNING,
        detect_casefile_indexes,
        match_index_entries_to_documents,
        parse_detected_indexes,
    )

    root = _validate_folder(folder)
    normalized_paths = tuple(
        sorted(
            (Path(path) for path in paths),
            key=lambda path: _relative_sort_key(root, path),
        )
    )

    documents: list[CaseFileDocument] = []
    total_pdf_files = 0
    total_non_pdf_files = 0

    for path in normalized_paths:
        absolute_path = path if path.is_absolute() else root / path
        relative_path = _relative_path(root, absolute_path)
        extension = absolute_path.suffix.lower()
        if extension == PDF_EXTENSION:
            total_pdf_files += 1
        else:
            total_non_pdf_files += 1

        document_type, type_confidence, type_source = classify_by_filename(
            relative_path
        )
        documents.append(
            CaseFileDocument(
                id=_document_id(relative_path),
                filename=absolute_path.name,
                relative_path=relative_path,
                extension=extension,
                size_bytes=absolute_path.stat().st_size,
                file_order=_extract_file_order(absolute_path.name),
                document_type=document_type,
                type_confidence=type_confidence,
                type_source=type_source,
            )
        )

    indexes = parse_detected_indexes(
        root,
        detect_casefile_indexes(root, normalized_paths),
    )
    indexes = match_index_entries_to_documents(indexes, documents)
    warnings = ()
    global_high = sum(
        1 for index in indexes
        if index.confidence == "high" and not _is_local_unit_index(index)
    )
    if global_high > 1:
        warnings = (
            ExtractionWarning(
                code=MULTIPLE_CASEFILE_INDEXES_WARNING,
                message="Trovati più possibili indici fascicolo ad alta confidenza",
            ),
        )

    units = build_casefile_units(documents)
    units = enrich_units_from_indexes(root, units)
    units = classify_casefile_units(units)
    analysis = CaseFileAnalysis(
        source_dir=str(root),
        documents=tuple(documents),
        total_files=len(documents),
        total_pdf_files=total_pdf_files,
        total_non_pdf_files=total_non_pdf_files,
        warnings=warnings,
        indexes=indexes,
        units=units,
    )
    if not compute_hashes:
        return analysis
    return hash_casefile_documents(root, analysis)


def analyze_case_folder(
    folder: Path,
    *,
    recursive: bool = True,
    compute_hashes: bool = True,
) -> CaseFileAnalysis:
    """Scan and normalize a local case folder, hashing files by default."""
    root = _validate_folder(folder)
    return normalize_casefile_documents(
        root,
        scan_directory(root, recursive=recursive),
        compute_hashes=compute_hashes,
    )


def hash_casefile_documents(
    folder: Path,
    analysis: CaseFileAnalysis,
) -> CaseFileAnalysis:
    """Populate SHA-256 metadata and duplicate-file warnings for documents."""
    root = _validate_folder(folder)
    documents: list[CaseFileDocument] = []
    warnings = [
        warning
        for warning in analysis.warnings
        if warning.code != DUPLICATE_FILE_WARNING
    ]
    first_path_by_hash: dict[str, str] = {}

    for document in analysis.documents:
        path = root / document.relative_path
        digest = file_sha256(path)
        document_warnings = tuple(
            warning
            for warning in document.warnings
            if warning.code != DUPLICATE_FILE_WARNING
        )
        first_path = first_path_by_hash.get(digest)
        if first_path is None:
            first_path_by_hash[digest] = document.relative_path
        elif document.document_type != DocumentType.MARKER_TECNICO:
            warning = ExtractionWarning(
                code=DUPLICATE_FILE_WARNING,
                message=f"Documento duplicato di {first_path}",
                path=document.relative_path,
            )
            warnings.append(warning)
            document_warnings = document_warnings + (warning,)

        documents.append(
            replace(
                document,
                sha256=digest,
                warnings=document_warnings,
            )
        )

    return replace(
        analysis,
        source_dir=str(root),
        documents=tuple(documents),
        warnings=tuple(warnings),
    )


def build_casefile_units(
    documents: Iterable[CaseFileDocument],
) -> tuple[CaseFileUnit, ...]:
    """Detect PDP/TIAP ministerial documentary units from scanned documents."""
    dirs: dict[str, list[CaseFileDocument]] = {}
    for doc in documents:
        parts = doc.relative_path.split("/")
        if len(parts) >= 2 and _NUMERIC_DIR_RE.match(parts[0]):
            dirs.setdefault(parts[0], []).append(doc)

    units: list[CaseFileUnit] = []
    for dir_name, docs in dirs.items():
        pdf_count = sum(1 for d in docs if d.extension == PDF_EXTENSION)
        if pdf_count == 0:
            continue
        main_pdf_name = f"{dir_name}/{dir_name}.pdf"
        main_doc = next(
            (d for d in docs if d.relative_path == main_pdf_name), None
        )
        index_path = next(
            (
                d.relative_path
                for d in docs
                if d.filename == ATTACHMENT_INDEX_FILENAME
            ),
            None,
        )
        marker_path = next(
            (
                d.relative_path
                for d in docs
                if d.filename == COMPLETE_MARKER_FILENAME
            ),
            None,
        )
        non_pdf_count = len(docs) - pdf_count
        total_size = sum(d.size_bytes for d in docs)
        units.append(
            CaseFileUnit(
                unit_id=dir_name,
                relative_dir=dir_name,
                main_document_id=main_doc.id if main_doc else None,
                main_pdf_path=main_doc.relative_path if main_doc else None,
                attachment_index_path=index_path,
                complete_marker_path=marker_path,
                total_files=len(docs),
                total_pdf_files=pdf_count,
                total_non_pdf_files=non_pdf_count,
                size_bytes=total_size,
            )
        )

    def _sort_key(unit: CaseFileUnit) -> tuple[int, str]:
        try:
            return (0, str(int(unit.unit_id)).zfill(20))
        except ValueError:
            return (1, unit.unit_id)

    return tuple(sorted(units, key=_sort_key))


def enrich_units_from_indexes(
    folder: Path,
    units: tuple[CaseFileUnit, ...],
) -> tuple[CaseFileUnit, ...]:
    """Read each unit's ListaAllegati.html and populate act metadata fields."""
    from gdlex_ocr.casefile_index import parse_attachment_index_metadata

    enriched: list[CaseFileUnit] = []
    for unit in units:
        if unit.attachment_index_path is None:
            enriched.append(unit)
            continue
        html_path = folder / unit.attachment_index_path
        try:
            html = html_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                html = html_path.read_bytes().decode("latin-1")
            except Exception:
                enriched.append(unit)
                continue
        except Exception:
            enriched.append(unit)
            continue
        meta = parse_attachment_index_metadata(html)
        enriched.append(replace(
            unit,
            act_title=meta.act_title,
            act_number=meta.act_number,
            description=meta.description,
            index_date=meta.index_date,
        ))
    return tuple(enriched)


def classify_casefile_units(
    units: tuple[CaseFileUnit, ...],
) -> tuple[CaseFileUnit, ...]:
    """Apply deterministic act-type classification to enriched units."""
    from gdlex_ocr.casefile_unit_classify import classify_act_metadata

    classified: list[CaseFileUnit] = []
    for unit in units:
        result = classify_act_metadata(unit.act_title, unit.description)
        classified.append(replace(
            unit,
            act_category=result.category,
            act_category_confidence=result.confidence,
            act_category_reason=result.reason,
        ))
    return tuple(classified)


def _is_local_unit_index(index: CaseFileIndex) -> bool:
    parts = index.relative_path.split("/")
    return (
        len(parts) == 2
        and _NUMERIC_DIR_RE.match(parts[0]) is not None
        and parts[1] == ATTACHMENT_INDEX_FILENAME
    )


def _validate_folder(folder: Path) -> Path:
    path = Path(folder).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"La cartella non esiste: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Il percorso non è una cartella: {path}")
    return path.resolve()


def _walk_visible_files(folder: Path) -> Iterable[Path]:
    for child in sorted(folder.iterdir(), key=_path_sort_key):
        if _is_hidden(child):
            continue
        if child.is_symlink() and child.is_dir():
            continue
        if child.is_dir():
            yield from _walk_visible_files(child)
        elif child.is_file():
            yield child


def _is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def _path_sort_key(path: Path) -> tuple[str, str]:
    return (path.name.casefold(), path.name)


def _relative_sort_key(root: Path, path: Path) -> tuple[str, str]:
    relative_path = _relative_path(root, path)
    return (relative_path.casefold(), relative_path)


def _relative_path(root: Path, path: Path) -> str:
    absolute_path = path if path.is_absolute() else root / path
    return absolute_path.relative_to(root).as_posix()


def _document_id(relative_path: str) -> str:
    normalized_path = relative_path.replace("\\", "/")
    digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()
    return f"doc-{digest[:12]}"


def _extract_file_order(filename: str) -> int | None:
    match = _FILE_ORDER_RE.match(filename)
    if match is None:
        return None
    return int(match.group(1))
