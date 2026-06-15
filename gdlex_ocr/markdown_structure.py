"""Conservative structural post-processing for OCR Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

STRUCTURE_STRATEGY = "conservative_heading_detection"
MAX_HEADING_LENGTH = 120
NEARBY_DUPLICATE_LINES = 12

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_EXISTING_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_MAJOR_RE = re.compile(
    r"^(?:PARTE|TITOLO|CAPITOLO|SEZIONE|ALLEGATO|APPENDICE)\b",
    re.IGNORECASE,
)
_ARTICLE_RE = re.compile(
    r"^(?:ART\.?\s*\d+[A-Z/-]*|ARTICOLO\s+\d+[A-Z/-]*)\b",
    re.IGNORECASE,
)
_NUMBERED_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)+[.)]?\s+\S|"
    r"\d+[.)]\s+\S|"
    r"[IVXLCDM]+[.)]\s+\S|"
    r"[A-Z][)]\s+\S"
    r")",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_HASH_RE = re.compile(r"\b[0-9a-f]{24,}\b", re.IGNORECASE)
_BASE64_RE = re.compile(r"(?:data:image/|;base64,)", re.IGNORECASE)
_BASE64_RUN_RE = re.compile(r"[A-Za-z0-9+/_=-]{60,}")
_SETEXT_RE = re.compile(r"^\s*(?:=+|-+)\s*$")
_TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)+\s*\|?\s*$"
)


@dataclass(frozen=True, slots=True)
class MarkdownStructureResult:
    markdown: str
    headings_added: int
    strategy: str = STRUCTURE_STRATEGY
    warnings: tuple[str, ...] = ()


def add_conservative_headings(markdown: str) -> MarkdownStructureResult:
    """Promote only isolated, high-confidence title lines to headings."""
    lines = markdown.splitlines(keepends=True)
    output: list[str] = []
    recent_headings: list[tuple[int, str]] = []
    headings_added = 0
    fence_marker: str | None = None

    for index, line in enumerate(lines):
        content, newline = _split_newline(line)
        stripped = content.strip()
        fence = _FENCE_RE.match(content)
        if fence:
            marker = fence.group(1)[0]
            if fence_marker is None:
                fence_marker = marker
            elif fence_marker == marker:
                fence_marker = None
            output.append(line)
            continue
        if fence_marker is not None:
            output.append(line)
            continue

        existing = _EXISTING_HEADING_RE.match(stripped)
        if existing:
            recent_headings.append((index, _title_key(existing.group(1))))
            output.append(line)
            continue

        level = _heading_level(lines, index, content)
        key = _title_key(stripped)
        if (
            level is None
            or not key
            or _is_nearby_duplicate(key, index, recent_headings)
        ):
            output.append(line)
            continue

        output.append(f"{'#' * level} {stripped}{newline}")
        recent_headings.append((index, key))
        headings_added += 1

    return MarkdownStructureResult(
        markdown="".join(output),
        headings_added=headings_added,
    )


def structure_markdown_file(path: str | Path) -> MarkdownStructureResult:
    """Post-process a UTF-8 Markdown file in place."""
    markdown_path = Path(path)
    original = markdown_path.read_text(encoding="utf-8")
    result = add_conservative_headings(original)
    if result.markdown != original:
        markdown_path.write_text(result.markdown, encoding="utf-8")
    return result


def _heading_level(
    lines: list[str],
    index: int,
    content: str,
) -> int | None:
    stripped = content.strip()
    if not _is_safe_candidate(lines, index, content):
        return None
    if _MAJOR_RE.match(stripped):
        return 2
    if _ARTICLE_RE.match(stripped) or _NUMBERED_RE.match(stripped):
        return 3
    if _looks_like_uppercase_title(stripped):
        return 2
    return None


def _is_safe_candidate(
    lines: list[str],
    index: int,
    content: str,
) -> bool:
    stripped = content.strip()
    if not stripped or content != stripped:
        return False
    if len(stripped) > MAX_HEADING_LENGTH:
        return False
    if stripped.startswith(("#", ">", "-", "*", "+", "<!--")):
        return False
    if _looks_like_table_line(stripped):
        return False
    if _URL_RE.search(stripped) or _EMAIL_RE.search(stripped):
        return False
    if _HASH_RE.search(stripped) or _looks_like_base64(stripped):
        return False
    if _SETEXT_RE.fullmatch(stripped):
        return False
    if not _is_isolated(lines, index):
        return False
    digits = sum(char.isdigit() for char in stripped)
    visible = sum(not char.isspace() for char in stripped)
    if visible and digits / visible > 0.35:
        return False
    return True


def _is_isolated(lines: list[str], index: int) -> bool:
    previous = lines[index - 1].strip() if index > 0 else ""
    following = lines[index + 1].strip() if index + 1 < len(lines) else ""
    if following and _SETEXT_RE.fullmatch(following):
        return False
    return not previous and not following


def _looks_like_uppercase_title(text: str) -> bool:
    if text.endswith((".", ";", ",")):
        return False
    words = text.split()
    if len(words) < 2 or len(words) > 16:
        return False
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 6:
        return False
    uppercase = sum(char.isupper() for char in letters)
    return uppercase / len(letters) >= 0.85


def _looks_like_table_line(text: str) -> bool:
    return (
        text.startswith("|")
        or text.endswith("|")
        or text.count("|") >= 2
        or bool(_TABLE_SEPARATOR_RE.fullmatch(text))
    )


def _looks_like_base64(text: str) -> bool:
    if _BASE64_RE.search(text):
        return True
    match = _BASE64_RUN_RE.fullmatch(text)
    return match is not None and len(text) >= 60


def _is_nearby_duplicate(
    key: str,
    index: int,
    recent_headings: list[tuple[int, str]],
) -> bool:
    recent_headings[:] = [
        item
        for item in recent_headings
        if index - item[0] <= NEARBY_DUPLICATE_LINES
    ]
    return any(existing == key for _, existing in recent_headings)


def _title_key(title: str) -> str:
    return "".join(char for char in title.casefold() if char.isalnum())


def _split_newline(line: str) -> tuple[str, str]:
    content = line.rstrip("\r\n")
    return content, line[len(content):]
