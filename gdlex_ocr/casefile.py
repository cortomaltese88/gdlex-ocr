"""Pure local case-folder scanning primitives."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Iterable

from gdlex_ocr.casefile_classify import classify_by_filename
from gdlex_ocr.manifest import file_sha256

PDF_EXTENSION = ".pdf"
DUPLICATE_FILE_WARNING = "duplicate_file"

_FILE_ORDER_RE = re.compile(r"^(\d{1,6})(?:\D|$)")


class DocumentType(Enum):
    SENTENZA = "sentenza"
    ORDINANZA = "ordinanza"
    DECRETO = "decreto"
    VERBALE_UDIENZA = "verbale_udienza"
    MEMORIA = "memoria"
    ISTANZA = "istanza"
    ALLEGATO = "allegato"
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


@dataclass(frozen=True, slots=True)
class CaseFileAnalysis:
    source_dir: str
    documents: tuple[CaseFileDocument, ...]
    total_files: int
    total_pdf_files: int
    total_non_pdf_files: int
    warnings: tuple[ExtractionWarning, ...]
    indexes: tuple[CaseFileIndex, ...] = ()


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

    indexes = detect_casefile_indexes(root, normalized_paths)
    warnings = ()
    if sum(1 for index in indexes if index.confidence == "high") > 1:
        warnings = (
            ExtractionWarning(
                code=MULTIPLE_CASEFILE_INDEXES_WARNING,
                message="Trovati più possibili indici fascicolo ad alta confidenza",
            ),
        )

    analysis = CaseFileAnalysis(
        source_dir=str(root),
        documents=tuple(documents),
        total_files=len(documents),
        total_pdf_files=total_pdf_files,
        total_non_pdf_files=total_non_pdf_files,
        warnings=warnings,
        indexes=indexes,
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
        else:
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
