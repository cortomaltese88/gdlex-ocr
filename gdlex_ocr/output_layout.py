"""Standard output paths for a single OCR job."""

from __future__ import annotations

from pathlib import Path


def build_output_layout(
    input_pdf: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Return the standard, non-progressive output paths for a job."""
    stem = input_pdf.stem
    return {
        "markdown": output_dir / f"{stem}_ocr.md",
        "index_markdown": output_dir / f"{stem}_ocr_index.md",
        "searchable_pdf": output_dir / f"{stem}_searchable.pdf",
        "run_log": output_dir / "run.log",
        "manifest": output_dir / "manifest.json",
    }
