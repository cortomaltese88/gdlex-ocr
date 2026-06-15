"""Standard output paths for a single OCR job."""

from __future__ import annotations

from pathlib import Path

MANIFEST_FILENAME = "manifest.json"
LOG_FILENAME = "run.log"


def build_job_output_dir(input_pdf: Path, output_root: Path) -> Path:
    """Return the deterministic base directory for a structured job."""
    return output_root / f"{input_pdf.stem}_ocr_job"


def make_unique_output_dir(base_dir: Path) -> Path:
    """Return the first available progressive directory without creating it."""
    if not base_dir.exists():
        return base_dir

    suffix = 2
    while True:
        candidate = base_dir.with_name(f"{base_dir.name}_{suffix}")
        if not candidate.exists():
            return candidate
        suffix += 1


def create_unique_output_dir(base_dir: Path) -> Path:
    """Create and return a progressive directory without overwriting one."""
    base_dir.parent.mkdir(parents=True, exist_ok=True)
    suffix = 1
    while True:
        candidate = (
            base_dir
            if suffix == 1
            else base_dir.with_name(f"{base_dir.name}_{suffix}")
        )
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            suffix += 1


def build_output_layout(
    input_pdf: Path,
    output_dir: Path,
    *,
    structured: bool = False,
) -> dict[str, Path]:
    """Return standard output paths, optionally in a structured job folder."""
    if structured:
        output_dir = make_unique_output_dir(
            build_job_output_dir(input_pdf, output_dir)
        )
    stem = input_pdf.stem
    return {
        "markdown": output_dir / f"{stem}_ocr.md",
        "index_markdown": output_dir / f"{stem}_ocr_index.md",
        "searchable_pdf": output_dir / f"{stem}_searchable.pdf",
        "run_log": output_dir / LOG_FILENAME,
        "manifest": output_dir / MANIFEST_FILENAME,
    }
