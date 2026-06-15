"""Progressive bookmark selection for searchable PDF and Markdown index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gdlex_ocr.act_outline import normalize_title
from gdlex_ocr.pdf_outline import (
    PdfOutlineItem,
    extract_outline_items,
    technical_fallback_items,
)

MAX_BOOKMARKS = 80
MAX_TITLE_LENGTH = 100

_BLOCK_RE = re.compile(
    r"^(?:<!--\s*)?(?:#{1,6}\s+)?Blocco\s+(\d+)"
    r"(?:\s*:|\s*-\s*)\s*[Pp]agine(?:\s+originali)?\s+"
    r"(\d+)\s*[-–]\s*(\d+)(?:\s*-->)?\s*$",
)
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+?)\s*#*\s*$")
_DOCUMENT_TITLE_RE = re.compile(
    r"^(?:fascicolo ocr|indice|sommario|documento)$",
    re.IGNORECASE,
)
_TECHNICAL_HEADING_RE = re.compile(
    r"^blocco\s+\d+\s*-\s*pagine\s+\d+\s*[-–]\s*\d+$",
    re.IGNORECASE,
)
_HEURISTIC_PREFIX_RE = re.compile(
    r"^(?:"
    r"(?:CAPITOLO|SEZIONE|PARTE|ALLEGATO|APPENDICE)\b|"
    r"(?:ART\.?|ARTICOLO)\s+\d+\b|"
    r"\d+(?:\.\d+)*[.)]\s+\S|"
    r"[IVXLCDM]+[.)]\s+\S|"
    r"[A-Z][)]\s+\S"
    r")",
    re.IGNORECASE,
)
_BASE64_RE = re.compile(r"(?:data:image/|;base64,)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class BookmarkSelection:
    strategy: str
    items: tuple[PdfOutlineItem, ...]
    fallback: bool
    warnings: tuple[str, ...] = ()


def select_bookmarks(
    source_pdf: str | Path,
    markdown_path: str | Path,
    *,
    block_size: int,
    total_pages: int,
) -> BookmarkSelection:
    """Select the first useful bookmark strategy in priority order."""
    warnings: list[str] = []
    try:
        native = _deduplicate(extract_outline_items(source_pdf), total_pages)
    except Exception as exc:
        native = []
        warnings.append(f"Outline PDF originale non leggibile: {exc}")
    if native:
        return BookmarkSelection("pdf_outline", tuple(native), False, tuple(warnings))

    markdown = Path(markdown_path).read_text(encoding="utf-8")
    headings = _markdown_heading_items(markdown, total_pages)
    if headings:
        return BookmarkSelection(
            "markdown_headings",
            tuple(headings),
            False,
            tuple(warnings),
        )

    heuristic = _text_heuristic_items(markdown, total_pages)
    if heuristic:
        return BookmarkSelection(
            "text_heuristics",
            tuple(heuristic),
            False,
            tuple(warnings),
        )

    warnings.append(
        "Nessun titolo documentale affidabile; usato fallback tecnico per pagine."
    )
    fallback = technical_fallback_items(block_size, total_pages)
    return BookmarkSelection("page_chunks", tuple(fallback), True, tuple(warnings))


def write_bookmark_index(
    markdown_path: str | Path,
    selection: BookmarkSelection,
    *,
    index_path: str | Path | None = None,
) -> Path:
    """Write an auditable Markdown index for the selected strategy."""
    source = Path(markdown_path)
    destination = (
        Path(index_path)
        if index_path is not None
        else source.with_name(f"{source.stem}_index.md")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Indice documentale",
        "",
        f"- Markdown sorgente: `{source.name}`",
        f"- Strategia segnalibri: `{selection.strategy}`",
        f"- Fallback tecnico: {'sì' if selection.fallback else 'no'}",
        "- Le pagine derivate dal Markdown indicano l'inizio del blocco Docling.",
        "",
        "| Titolo | Pagina |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {item.title.replace('|', '\\|')} | {item.page_index + 1} |"
        for item in selection.items
    )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _markdown_heading_items(
    markdown: str,
    total_pages: int,
) -> list[PdfOutlineItem]:
    items: list[PdfOutlineItem] = []
    current_page: int | None = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        marker = _BLOCK_RE.match(line)
        if marker:
            current_page = int(marker.group(2)) - 1
            continue
        match = _HEADING_RE.match(line)
        if match is None or current_page is None:
            continue
        title = normalize_title(match.group(1), MAX_TITLE_LENGTH)
        if not _plausible_title(title) or _TECHNICAL_HEADING_RE.fullmatch(title):
            continue
        items.append(PdfOutlineItem(title, current_page))
        if len(items) >= MAX_BOOKMARKS:
            break
    return _deduplicate(items, total_pages, unique_titles=True)


def _text_heuristic_items(
    markdown: str,
    total_pages: int,
) -> list[PdfOutlineItem]:
    items: list[PdfOutlineItem] = []
    current_page: int | None = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        marker = _BLOCK_RE.match(line)
        if marker:
            current_page = int(marker.group(2)) - 1
            continue
        if current_page is None or line.startswith(("#", "<!--", "|")):
            continue
        if _BASE64_RE.search(line) or not _HEURISTIC_PREFIX_RE.match(line):
            continue
        title = normalize_title(line, MAX_TITLE_LENGTH)
        if not _plausible_title(title):
            continue
        items.append(PdfOutlineItem(title, current_page))
        if len(items) >= MAX_BOOKMARKS:
            break
    return _deduplicate(items, total_pages, unique_titles=True)


def _plausible_title(title: str) -> bool:
    if not title or _DOCUMENT_TITLE_RE.fullmatch(title):
        return False
    if len(title) > MAX_TITLE_LENGTH or len(title.split()) > 18:
        return False
    if _BASE64_RE.search(title):
        return False
    return not title.endswith((".", ";"))


def _deduplicate(
    items: list[PdfOutlineItem],
    total_pages: int,
    *,
    unique_titles: bool = False,
) -> list[PdfOutlineItem]:
    result: list[PdfOutlineItem] = []
    seen: set[tuple[str, int]] = set()
    for item in items:
        if item.page_index < 0 or item.page_index >= total_pages:
            continue
        title_key = "".join(item.title.casefold().split())
        key = (title_key, -1 if unique_titles else item.page_index)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
