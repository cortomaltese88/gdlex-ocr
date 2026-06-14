"""Build content-aware PDF outlines from Docling Markdown."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from pypdf import PdfReader

from gdlex_ocr.pdf_outline import (
    PdfOutlineItem,
    add_outline_items,
    technical_fallback_items,
)


MAX_OUTLINE_ITEMS = 80
MIN_CONTENT_ITEMS = 3
MAX_TITLE_LENGTH = 100

_BLOCK_RE = re.compile(
    r"^#{1,6}\s+Blocco\s+(\d+)\s*-\s*Pagine\s+(\d+)\s*[-–]\s*(\d+)\s*$",
    re.IGNORECASE,
)
_COMMENT_BLOCK_RE = re.compile(
    r"^<!--\s*Blocco\s+(\d+):\s*pagine\s+originali\s+"
    r"(\d+)\s*[-–]\s*(\d+)\s*-->\s*$",
    re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_PAGE_NUMBER_RE = re.compile(
    r"^(?:pag(?:ina)?\.?\s*)?\d+(?:\s*(?:/|di)\s*\d+)?$",
    re.IGNORECASE,
)
_GENERIC_RE = re.compile(
    r"^(?:fascicolo ocr|indice|sommario|documento|allegato|"
    r"pagina|pagine|firma|firme|oggetto|data|protocollo)$",
    re.IGNORECASE,
)
_TITLE_PREFIX_RE = re.compile(
    r"^(?:oggetto|atto|documento)\s*:\s*$|"
    r"^(?:n(?:umero)?[.°º]?\s*)?\d+(?:[./-]\d+)*\s*[-:]\s*$",
    re.IGNORECASE,
)
_OFFICE_RE = re.compile(
    r"\b(?:tribunale|procura della repubblica|corte d['’]appello|"
    r"stazione carabinieri|questura|comando provinciale|"
    r"guardia di finanza)\b",
    re.IGNORECASE,
)
_ACT_RE = re.compile(
    r"\b(?:"
    r"annotazione(?:\s+di\s+p\.?\s*g\.?)?|"
    r"verbale(?:\s+di\s+(?:sommarie\s+informazioni|"
    r"identificazione|interrogatorio|sequestro|perquisizione))?|"
    r"richiesta\s+di\s+archiviazione|"
    r"avviso(?:\s+di\s+conclusione\s+delle\s+indagini)?|"
    r"decreto(?:\s+(?:penale|di\s+(?:citazione|sequestro|"
    r"perquisizione|archiviazione)))?|"
    r"nomina\s+(?:del\s+)?difensore|"
    r"relata\s+di\s+notifica|"
    r"comunicazione\s+(?:della\s+)?notizia\s+di\s+reato|"
    r"querela|memoria|istanza|provvedimento|"
    r"informativa(?:\s+di\s+reato)?|denuncia|esposto|ordinanza|"
    r"sentenza|atto\s+di\s+citazione|citazione\s+diretta|"
    r"procura\s+speciale|elezione\s+di\s+domicilio|"
    r"invito\s+a\s+presentarsi|conclusione\s+delle\s+indagini|"
    r"richiesta\s+di\s+rinvio\s+a\s+giudizio|"
    r"opposizione\s+alla\s+richiesta\s+di\s+archiviazione"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ActOutlineEntry:
    title: str
    page: int
    block: int


@dataclass(frozen=True, slots=True)
class OutlineResult:
    entries: tuple[ActOutlineEntry, ...]
    used_fallback: bool
    index_path: Path


def extract_act_titles(
    markdown: str,
    *,
    max_items: int = MAX_OUTLINE_ITEMS,
) -> list[ActOutlineEntry]:
    """Extract reliable act-title candidates from merged Docling Markdown."""
    if max_items < 1:
        raise ValueError("max_items deve essere almeno 1.")

    entries: list[ActOutlineEntry] = []
    current_block = 0
    current_page = 1

    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        marker = _BLOCK_RE.match(stripped) or _COMMENT_BLOCK_RE.match(stripped)
        if marker:
            current_block = int(marker.group(1))
            current_page = int(marker.group(2))
            continue
        if current_block == 0:
            continue

        title = _candidate_title(stripped)
        if title is None or _is_duplicate(title, entries):
            continue

        entries.append(ActOutlineEntry(title, current_page, current_block))
        if len(entries) >= max_items:
            break

    return entries


def create_content_aware_outline(
    pdf_path: str | Path,
    markdown_path: str | Path,
    block_size: int,
    total_pages: int | None = None,
    *,
    index_path: str | Path | None = None,
    min_content_items: int = MIN_CONTENT_ITEMS,
) -> OutlineResult:
    """Create a content-aware outline, with a technical range fallback."""
    if min_content_items < 1:
        raise ValueError("min_content_items deve essere almeno 1.")

    pdf = Path(pdf_path)
    markdown_file = Path(markdown_path)
    markdown = markdown_file.read_text(encoding="utf-8")
    entries = extract_act_titles(markdown)

    page_count = len(PdfReader(pdf).pages)
    n_pages = min(total_pages, page_count) if total_pages is not None else page_count
    valid_entries = [
        entry for entry in entries if 1 <= entry.page <= page_count
    ]
    used_fallback = len(valid_entries) < min_content_items

    if used_fallback:
        pdf_items = technical_fallback_items(block_size, n_pages)
        audit_entries = tuple(
            ActOutlineEntry(item.title, item.page_index + 1, index + 1)
            for index, item in enumerate(pdf_items)
        )
    else:
        pdf_items = [
            PdfOutlineItem(entry.title, entry.page - 1)
            for entry in valid_entries
        ]
        audit_entries = tuple(valid_entries)

    add_outline_items(pdf, pdf_items)
    destination = (
        Path(index_path)
        if index_path is not None
        else markdown_file.with_name(f"{markdown_file.stem}_index.md")
    )
    _write_index(destination, markdown_file.name, audit_entries, used_fallback)
    return OutlineResult(audit_entries, used_fallback, destination)


def _candidate_title(line: str) -> str | None:
    if not line or line.startswith("<!--") or line.startswith("|"):
        return None

    is_heading = bool(re.match(r"^#{1,6}\s+", line))
    cleaned = normalize_title(line)
    if not cleaned or _GENERIC_RE.fullmatch(cleaned):
        return None
    if _PAGE_NUMBER_RE.fullmatch(cleaned):
        return None

    match = _ACT_RE.search(cleaned)
    if match is None:
        return None

    words = cleaned.split()
    prefix = cleaned[:match.start()].strip()
    starts_as_title = match.start() == 0 or bool(_TITLE_PREFIX_RE.fullmatch(prefix))
    title_shape = (
        is_heading
        or starts_as_title
        or cleaned.isupper()
    )
    if not title_shape or len(words) > 18:
        return None
    if cleaned.endswith((".", ";")) and not is_heading:
        return None
    if _OFFICE_RE.search(cleaned) and match.start() > 20:
        return None
    return cleaned


def normalize_title(line: str, max_length: int = MAX_TITLE_LENGTH) -> str:
    """Remove Markdown and obvious OCR noise without inventing words."""
    text = html.unescape(line)
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", text)
    text = re.sub(r"^>\s*", "", text)
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _HTML_TAG_RE.sub("", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = "".join(
        char
        for char in text
        if char in "\t "
        or (
            unicodedata.category(char)[0] not in {"C", "S"}
            and char not in {"|", "�"}
        )
    )
    text = re.sub(r"([#*_=~^])\1+", " ", text)
    text = _SPACE_RE.sub(" ", text).strip(" \t-–—:;,.#*_=~")
    if len(text) > max_length:
        text = text[:max_length].rstrip(" \t-–—:;,.")
    return text


def _is_duplicate(
    title: str,
    entries: list[ActOutlineEntry],
) -> bool:
    key = _comparison_key(title)
    for entry in entries:
        existing = _comparison_key(entry.title)
        length_ratio = min(len(key), len(existing)) / max(len(key), len(existing))
        if key == existing:
            return True
        if length_ratio >= 0.8 and (
            key in existing
            or existing in key
            or SequenceMatcher(None, key, existing).ratio() >= 0.9
        ):
            return True
    return False


def _comparison_key(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title.casefold())
    return "".join(char for char in normalized if char.isalnum())


def _write_index(
    path: Path,
    markdown_name: str,
    entries: tuple[ActOutlineEntry, ...],
    used_fallback: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "fallback tecnico per intervalli" if used_fallback else "content-aware"
    lines = [
        "# Indice documenti",
        "",
        f"- Markdown sorgente: `{markdown_name}`",
        f"- Modalità outline: {mode}",
        "",
        "| Titolo | Pagina stimata | Blocco |",
        "|---|---:|---:|",
    ]
    lines.extend(
        f"| {entry.title.replace('|', '\\|')} | {entry.page} | {entry.block} |"
        for entry in entries
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
