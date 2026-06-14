"""Add PDF outline (bookmarks) to a PDF file using pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def add_block_bookmarks(
    pdf_path: str | Path,
    block_size: int,
    total_pages: int | None = None,
) -> None:
    """Add page-range bookmarks to *pdf_path*, replacing the file in-place.

    Creates entries like "Pagine 1–15", "Pagine 16–30", … using *block_size*
    as the interval. Compatible with standard PDF outline viewers (Okular,
    Evince, Adobe Reader, Firefox/Chrome).
    """
    if block_size < 1:
        raise ValueError("block_size deve essere almeno 1.")

    path = Path(pdf_path)
    reader = PdfReader(path)
    page_count = len(reader.pages)
    n_pages = min(total_pages, page_count) if total_pages is not None else page_count

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    for zero_start in range(0, n_pages, block_size):
        zero_end = min(zero_start + block_size, n_pages)
        title = f"Pagine {zero_start + 1}–{zero_end}"
        writer.add_outline_item(title, zero_start)

    tmp = path.with_suffix(".tmp_outline.pdf")
    replaced = False
    try:
        with tmp.open("wb") as fh:
            writer.write(fh)
        tmp.replace(path)
        replaced = True
    finally:
        if not replaced:
            tmp.unlink(missing_ok=True)
