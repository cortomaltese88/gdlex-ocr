"""PDF page counting and non-destructive splitting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter


class PdfSplitError(RuntimeError):
    """Raised when the input PDF cannot be read or split."""


@dataclass(frozen=True, slots=True)
class PdfBlock:
    index: int
    start_page: int
    end_page: int
    path: Path

    @property
    def page_count(self) -> int:
        return self.end_page - self.start_page + 1


def count_pdf_pages(pdf_path: str | Path) -> int:
    """Return the number of pages without modifying the source PDF."""
    path = Path(pdf_path)
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise PdfSplitError("Il PDF è protetto da password.")
        return len(reader.pages)
    except PdfSplitError:
        raise
    except Exception as exc:
        raise PdfSplitError(f"Impossibile leggere il PDF: {exc}") from exc


def split_pdf(
    pdf_path: str | Path,
    destination: str | Path,
    pages_per_block: int = 5,
    on_block_created: Callable[[PdfBlock], None] | None = None,
) -> list[PdfBlock]:
    """Split a PDF into page blocks, leaving the source untouched."""
    if pages_per_block < 1:
        raise ValueError("Il numero di pagine per blocco deve essere almeno 1.")

    source = Path(pdf_path)
    output_dir = Path(destination)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise PdfSplitError("Il PDF è protetto da password.")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise PdfSplitError("Il PDF non contiene pagine.")

        blocks: list[PdfBlock] = []
        for zero_based_start in range(0, total_pages, pages_per_block):
            zero_based_end = min(zero_based_start + pages_per_block, total_pages)
            index = len(blocks) + 1
            start_page = zero_based_start + 1
            end_page = zero_based_end
            block_path = output_dir / (
                f"blocco_{index:04d}_pagine_{start_page:04d}-{end_page:04d}.pdf"
            )

            writer = PdfWriter()
            for page_number in range(zero_based_start, zero_based_end):
                writer.add_page(reader.pages[page_number])
            with block_path.open("wb") as output_file:
                writer.write(output_file)

            block = PdfBlock(index, start_page, end_page, block_path)
            blocks.append(block)
            if on_block_created is not None:
                on_block_created(block)

        return blocks
    except PdfSplitError:
        raise
    except Exception as exc:
        raise PdfSplitError(f"Errore durante la suddivisione del PDF: {exc}") from exc
