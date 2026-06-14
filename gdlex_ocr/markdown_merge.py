"""Merge block-level Markdown while retaining source page references."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class MarkdownMergeError(RuntimeError):
    """Raised when partial Markdown files cannot be merged."""


@dataclass(frozen=True, slots=True)
class MarkdownBlock:
    index: int
    start_page: int
    end_page: int
    path: Path


def merge_markdown(
    blocks: list[MarkdownBlock],
    output_path: str | Path,
    source_name: str,
) -> Path:
    if not blocks:
        raise MarkdownMergeError("Nessun output Markdown da unire.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with destination.open("w", encoding="utf-8", newline="\n") as merged:
            merged.write("# Fascicolo OCR\n\n")
            merged.write(f"<!-- Sorgente: {source_name} -->\n\n")

            for block in sorted(blocks, key=lambda item: item.index):
                content = block.path.read_text(encoding="utf-8").strip()
                merged.write(
                    f"<!-- Blocco {block.index}: pagine originali "
                    f"{block.start_page}-{block.end_page} -->\n\n"
                )
                merged.write(
                    f"## Blocco {block.index} - Pagine "
                    f"{block.start_page}-{block.end_page}\n\n"
                )
                merged.write(content)
                merged.write("\n\n")
        return destination
    except Exception as exc:
        raise MarkdownMergeError(
            f"Impossibile creare il Markdown finale: {exc}"
        ) from exc
