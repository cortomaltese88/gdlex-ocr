"""Remove embedded image payloads from block-level Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


IMAGE_PLACEHOLDER = "[immagine rimossa - contenuto non testuale]"
DEFAULT_MAX_LINE_LENGTH = 20_000

_MEDIA_TYPE = r"data:image/[a-z0-9.+-]+"
_PARAMETERS = r"(?:;[a-z0-9.+-]+=[^;,\s]+)*"
_BASE64_PAYLOAD = r"[a-z0-9+/_=-]+"
_DATA_IMAGE_URI = (
    rf"{_MEDIA_TYPE}{_PARAMETERS};base64,{_BASE64_PAYLOAD}"
)

_MARKDOWN_IMAGE_RE = re.compile(
    rf"!\[[^\r\n]*?\]\(\s*{_DATA_IMAGE_URI}\s*\)",
    re.IGNORECASE,
)
_HTML_IMAGE_RE = re.compile(
    rf"<img\b[^>]*?\bsrc\s*=\s*([\"']){_DATA_IMAGE_URI}\1[^>]*>",
    re.IGNORECASE,
)
_DATA_IMAGE_URI_RE = re.compile(_DATA_IMAGE_URI, re.IGNORECASE)
_BASE64_RUN_RE = re.compile(r"[a-z0-9+/_=-]+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SanitizeResult:
    markdown: str
    embedded_images_removed: int
    long_base64_lines_removed: int

    @property
    def total_removed(self) -> int:
        return (
            self.embedded_images_removed
            + self.long_base64_lines_removed
        )


def sanitize_markdown(
    markdown: str,
    max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
) -> SanitizeResult:
    """Replace embedded image data and pathological base64-like lines."""
    if max_line_length < 1:
        raise ValueError("max_line_length deve essere maggiore di zero.")

    sanitized, markdown_images = _MARKDOWN_IMAGE_RE.subn(
        IMAGE_PLACEHOLDER,
        markdown,
    )
    sanitized, html_images = _HTML_IMAGE_RE.subn(
        IMAGE_PLACEHOLDER,
        sanitized,
    )
    sanitized, raw_uris = _DATA_IMAGE_URI_RE.subn(
        IMAGE_PLACEHOLDER,
        sanitized,
    )

    output_lines: list[str] = []
    long_lines_removed = 0
    for line in sanitized.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if (
            len(content) > max_line_length
            and _looks_like_base64(content)
        ):
            newline = line[len(content):]
            output_lines.append(IMAGE_PLACEHOLDER + newline)
            long_lines_removed += 1
        else:
            output_lines.append(line)

    return SanitizeResult(
        markdown="".join(output_lines),
        embedded_images_removed=markdown_images + html_images + raw_uris,
        long_base64_lines_removed=long_lines_removed,
    )


def sanitize_markdown_file(
    path: str | Path,
    max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
) -> SanitizeResult:
    """Sanitize a UTF-8 Markdown file in place and return removal counts."""
    markdown_path = Path(path)
    original = markdown_path.read_text(encoding="utf-8")
    result = sanitize_markdown(original, max_line_length)
    if result.markdown != original:
        markdown_path.write_text(result.markdown, encoding="utf-8")
    return result


def _looks_like_base64(line: str) -> bool:
    longest_run = max(
        (len(match.group(0)) for match in _BASE64_RUN_RE.finditer(line)),
        default=0,
    )
    return longest_run >= len(line) * 0.9
