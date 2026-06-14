"""Auditable job manifest written for each OCR/convert run."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MANIFEST_FILENAME = "manifest.json"


def file_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    """Return the current UTC time as ISO-8601 with timezone."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_job_id() -> str:
    return str(uuid.uuid4())


def build_initial_manifest(
    *,
    pdf_path: Path,
    output_dir: Path,
    profile: Any,
    pages_per_block: int,
    create_searchable: bool,
    ocr_language: str,
    app_version: str,
) -> dict[str, Any]:
    """Return a new manifest dict at job start.

    SHA-256 and file size are computed here; page count is filled in later
    once the PDF has been inspected.
    """
    try:
        sha256 = file_sha256(pdf_path)
    except OSError:
        sha256 = ""

    try:
        size_bytes = pdf_path.stat().st_size
    except OSError:
        size_bytes = 0

    return {
        "schema_version": SCHEMA_VERSION,
        "app": {
            "name": "GD LEX OCR",
            "version": app_version,
        },
        "job": {
            "id": _new_job_id(),
            "started_at": utc_now_iso(),
            "finished_at": None,
            "duration_seconds": None,
            "status": "running",
        },
        "input": {
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "page_count": None,
        },
        "profile": {
            "name": profile.name,
            "options": {
                "block_size": profile.block_size,
                "num_threads": profile.num_threads,
                "page_batch_size": profile.page_batch_size,
                "enable_ocr": profile.enable_ocr,
                "table_mode": profile.table_mode,
                "enrich_picture": profile.enrich_picture,
                "enrich_chart": profile.enrich_chart,
            },
        },
        "processing": {
            "block_size": pages_per_block,
            "blocks_total": None,
            "blocks_completed": 0,
            "ocr_searchable_pdf_requested": create_searchable,
            "ocr_language": ocr_language,
        },
        "outputs": {
            "output_dir": str(output_dir),
            "markdown": None,
            "index_markdown": None,
            "searchable_pdf": None,
            "run_log": str(output_dir / "run.log"),
            "manifest": str(output_dir / MANIFEST_FILENAME),
        },
        "warnings": [],
        "errors": [],
    }


def write_manifest(manifest: dict[str, Any], output_dir: Path) -> Path:
    """Write *manifest* as indented UTF-8 JSON. Returns the path written."""
    path = output_dir / MANIFEST_FILENAME
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def safe_write_manifest(manifest: dict[str, Any], output_dir: Path) -> bool:
    """Write manifest, returning False silently on any OS error."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_manifest(manifest, output_dir)
        return True
    except OSError:
        return False
