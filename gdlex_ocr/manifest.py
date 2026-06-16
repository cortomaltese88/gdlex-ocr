"""Auditable job manifest written for each OCR/convert run."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gdlex_ocr.markdown_structure import STRUCTURE_STRATEGY
from gdlex_ocr.output_layout import MANIFEST_FILENAME, build_output_layout

SCHEMA_VERSION = 1
OUTPUT_KEYS = (
    "markdown",
    "run_log",
    "manifest",
    "searchable_pdf",
    "index_markdown",
)


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


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a manifest JSON object from *path*."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Il manifest deve contenere un oggetto JSON.")
    return manifest


def verify_manifest_outputs(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Check declared output paths without reading their file contents."""
    job = manifest.get("job")
    outputs = manifest.get("outputs")
    processing = manifest.get("processing")
    status = job.get("status") if isinstance(job, dict) else None
    output_values = outputs if isinstance(outputs, dict) else {}
    processing_values = processing if isinstance(processing, dict) else {}
    searchable_requested = bool(
        processing_values.get("ocr_searchable_pdf_requested", False)
    )

    checked: list[dict[str, Any]] = []
    missing: list[str] = []
    warnings: list[str] = []

    for key in OUTPUT_KEYS:
        raw_path = output_values.get(key)
        declared = isinstance(raw_path, str) and bool(raw_path.strip())
        required = _output_is_required(key, status, declared)
        path = Path(raw_path) if declared else None
        exists = path.is_file() if path is not None else False
        item: dict[str, Any] = {
            "key": key,
            "path": str(path) if path is not None else None,
            "required": required,
            "exists": exists,
        }
        if exists and path is not None:
            try:
                item["size_bytes"] = path.stat().st_size
            except OSError:
                item["exists"] = False
                exists = False
        checked.append(item)
        if required and not exists:
            missing.append(key)

    checked_by_key = {item["key"]: item for item in checked}
    if (
        searchable_requested
        and not checked_by_key["searchable_pdf"]["exists"]
    ):
        warnings.append("PDF ricercabile richiesto ma non presente")
    if (
        checked_by_key["searchable_pdf"]["exists"]
        and not checked_by_key["index_markdown"]["exists"]
    ):
        warnings.append("Indice Markdown del PDF ricercabile non presente")

    return {
        "ok": not missing,
        "checked": checked,
        "missing": missing,
        "warnings": warnings,
    }


def format_manifest_verification(report: dict[str, Any]) -> str:
    """Return a short Italian summary of an output verification report."""
    checked = report.get("checked", [])
    required = [
        item for item in checked
        if isinstance(item, dict) and item.get("required")
    ]
    present = sum(bool(item.get("exists")) for item in required)
    lines = [f"Output verificati: {present}/{len(required)}"]
    missing = report.get("missing", [])
    if missing:
        lines.append(f"Manca: {', '.join(str(key) for key in missing)}")
    for warning in report.get("warnings", []):
        lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def _output_is_required(
    key: str,
    status: Any,
    declared: bool,
) -> bool:
    if key == "markdown":
        return status == "success"
    if key in {"run_log", "manifest"}:
        return declared or status == "success"
    return False


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
    structured_output: bool = False,
    ocr_backend: str = "auto",
    external_ocr_command: str | None = None,
    use_searchable_as_source: bool = False,
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

    layout = build_output_layout(pdf_path, output_dir)
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
                "structure_markdown": profile.structure_markdown,
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
            "run_log": str(layout["run_log"]),
            "manifest": str(layout["manifest"]),
        },
        "output_layout": {
            "structured": structured_output,
            "job_output_dir": str(output_dir),
        },
        "bookmarks": {
            "strategy": None,
            "count": 0,
            "fallback": False,
            "warnings": [],
            "reason": (
                None
                if create_searchable
                else "searchable_pdf_not_requested"
            ),
        },
        "markdown_structure": {
            "enabled": profile.structure_markdown,
            "post_processed": False,
            "headings_added": 0,
            "strategy": (
                STRUCTURE_STRATEGY
                if profile.structure_markdown
                else None
            ),
            "warnings": [],
        },
        "ocr_backend": {
            "requested": ocr_backend,
            "name": None,
            "command": external_ocr_command,
            "available": False,
            "used": False,
            "use_as_source": use_searchable_as_source,
            "warnings": [],
        },
        "output_sha256": {
            "markdown": None,
            "searchable_pdf": None,
            "index_markdown": None,
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
