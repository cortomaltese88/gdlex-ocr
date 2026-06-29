"""Generate one bookmarked PDF from a reviewed case-file merge plan."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.casefile_merge_plan_export import (
    MERGE_PLAN_JSON_FILENAME,
    REVISED_MERGE_PLAN_JSON_FILENAME,
    CaseFileMergePlan,
    CaseFileMergePlanItem,
    load_casefile_merge_plan,
)

MERGED_PDF_FILENAME = "fascicolo_unico.pdf"
OPTIMIZED_PDF_FILENAME = "fascicolo_unico_light.pdf"
MERGE_REPORT_JSON_FILENAME = "fascicolo_unico_report.json"
MERGE_REPORT_MARKDOWN_FILENAME = "fascicolo_unico_report.md"
ESTIMATE_REPORT_JSON_FILENAME = "fascicolo_pdf_estimate.json"
ESTIMATE_REPORT_MARKDOWN_FILENAME = "fascicolo_pdf_estimate.md"
ESTIMATE_REPORT_CSV_FILENAME = "fascicolo_pdf_estimate.csv"
PDF_OPTIMIZATION_PROFILES = ("none", "balanced", "small", "screen")
_GHOSTSCRIPT_SETTINGS = {
    "balanced": "/printer",
    "small": "/ebook",
    "screen": "/screen",
}
OPTIMIZED_PDF_NOT_SMALLER_WARNING = (
    "Attenzione: il PDF ottimizzato è più grande dell’originale. "
    "Valutare l’uso del PDF originale."
)


class CaseFilePdfMergeError(ValueError):
    """Raised when a case-file PDF merge cannot be completed safely."""


class CaseFilePdfMergeCancelled(CaseFilePdfMergeError):
    """Raised when the user cancels a case-file PDF merge."""


CaseFilePdfMergeProgressCallback = Callable[[dict[str, object]], None]
CaseFilePdfMergeCancelCallback = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class CaseFilePdfMergeJob:
    casefile_root: Path
    output_dir: Path
    source_plan: Path
    plan: CaseFileMergePlan


@dataclass(frozen=True, slots=True)
class CaseFilePdfMergeResult:
    pdf_path: Path
    report_json_path: Path
    report_markdown_path: Path
    source_plan: Path
    total_items: int
    included_items: int
    excluded_items: int
    total_pages: int
    estimated_output_size_bytes: int = 0
    actual_output_size_bytes: int = 0
    optimization_profile: str = "none"
    optimized_pdf_path: Path | None = None
    optimized_output_size_bytes: int | None = None
    size_reduction_percent: float | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseFilePdfMergeSizeEstimate:
    included_pdf_count: int
    excluded_pdf_count: int
    source_size_bytes: int
    estimated_page_count: int | None
    average_bytes_per_page: float | None
    estimated_output_size_bytes: int


def estimate_casefile_pdf_merge(
    casefile_root: Path, output_dir: Path
) -> dict[str, object]:
    """Dry-run the case-file PDF merge without writing PDFs or reports."""
    job = build_casefile_pdf_merge_job(casefile_root, output_dir)
    included = sorted(
        (item for item in job.plan.items if item.include_in_merged_pdf),
        key=lambda item: (
            item.final_order is None,
            item.final_order if item.final_order is not None else 999_999,
        ),
    )
    excluded_plan_items = [
        item for item in job.plan.items if not item.include_in_merged_pdf
    ]
    items: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    warnings: list[str] = []
    total_size = 0
    total_pages = 0

    for item in included:
        source = resolve_safe_source_pdf(job.casefile_root, item.source_pdf)
        size = source.stat().st_size
        pages = item.total_pages
        if pages is None:
            try:
                reader = PdfReader(source)
                if reader.is_encrypted:
                    raise CaseFilePdfMergeError(
                        "PDF non leggibile o protetto da password: "
                        f"{item.source_pdf}"
                    )
                pages = len(reader.pages)
            except Exception as exc:
                if isinstance(exc, CaseFilePdfMergeError):
                    raise
                raise CaseFilePdfMergeError(
                    f"PDF sorgente non leggibile: {item.source_pdf}: {exc}"
                ) from exc
        if pages < 1:
            raise CaseFilePdfMergeError(f"PDF sorgente senza pagine: {item.source_pdf}")
        total_size += size
        total_pages += pages
        item_warnings = _merge_plan_item_warning_messages(item)
        warnings.extend(item_warnings)
        items.append({
            "final_order": item.final_order,
            "unit_id": item.unit_id,
            "source_pdf": _safe_report_path(item.source_pdf),
            "bookmark_label": item.bookmark_label,
            "estimated_pages": pages,
            "source_size_bytes": size,
            "source_size_human": format_bytes(size),
            "warnings": item_warnings,
        })

    for item in excluded_plan_items:
        item_warnings = _merge_plan_item_warning_messages(item)
        warnings.extend(item_warnings)
        excluded.append({
            "unit_id": item.unit_id,
            "source_pdf": _safe_report_path(item.source_pdf),
            "bookmark_label": item.bookmark_label,
            "exclude_reason": item.exclude_reason or "escluso",
            "warnings": item_warnings,
        })

    return {
        "source_plan": job.source_plan.name,
        "total_items": job.plan.total_items,
        "included_items": len(included),
        "excluded_items": len(excluded),
        "estimated_pages": total_pages,
        "estimated_source_size_bytes": total_size,
        "estimated_source_size_human": format_bytes(total_size),
        "warnings": warnings,
        "items": items,
        "excluded": excluded,
    }


def default_casefile_pdf_estimate_json_path(output_dir: Path) -> Path:
    return Path(output_dir) / ESTIMATE_REPORT_JSON_FILENAME


def default_casefile_pdf_estimate_md_path(output_dir: Path) -> Path:
    return Path(output_dir) / ESTIMATE_REPORT_MARKDOWN_FILENAME


def default_casefile_pdf_estimate_csv_path(output_dir: Path) -> Path:
    return Path(output_dir) / ESTIMATE_REPORT_CSV_FILENAME


def write_casefile_pdf_estimate_reports(
    estimate: dict[str, object],
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Write audit reports for a PDF merge estimate without creating PDFs."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = default_casefile_pdf_estimate_json_path(output)
    md_path = default_casefile_pdf_estimate_md_path(output)
    csv_path = default_casefile_pdf_estimate_csv_path(output)
    _atomic_write_text(
        json_path,
        json.dumps(estimate, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write_text(md_path, format_casefile_pdf_estimate_markdown(estimate))
    _atomic_write_text(csv_path, "\ufeff" + format_casefile_pdf_estimate_csv(estimate))
    return json_path, md_path, csv_path


def format_casefile_pdf_estimate_markdown(estimate: dict[str, object]) -> str:
    lines = [
        "# Stima PDF unico fascicolo", "",
        f"Piano usato: {estimate['source_plan']}",
        f"Atti inclusi: {estimate['included_items']}",
        f"Atti esclusi: {estimate['excluded_items']}",
        f"Pagine stimate: {estimate['estimated_pages']}",
        f"Dimensione stimata: {estimate['estimated_source_size_human']}",
        f"Warning: {len(estimate.get('warnings', []))}", "",
        "## Atti inclusi", "",
        "| Ordine | Titolo/segnalibro | PDF sorgente | Pagine | Dimensione | Warning |",
        "|---:|---|---|---:|---:|---|",
    ]
    for item in estimate.get("items", []):
        if not isinstance(item, dict):
            continue
        warnings = " | ".join(str(warning) for warning in item.get("warnings", []))
        lines.append(
            f"| {item.get('final_order') or ''} | "
            f"{_md(str(item.get('bookmark_label') or ''))} | "
            f"{_md(str(item.get('source_pdf') or ''))} | "
            f"{item.get('estimated_pages') or ''} | "
            f"{_md(str(item.get('source_size_human') or ''))} | "
            f"{_md(warnings)} |"
        )
    lines.extend([
        "",
        "## Atti esclusi",
        "",
        "| Motivo | Titolo/segnalibro | PDF sorgente | Atto | Warning |",
        "|---|---|---|---|---|",
    ])
    for item in estimate.get("excluded", []):
        if not isinstance(item, dict):
            continue
        warnings = " | ".join(str(warning) for warning in item.get("warnings", []))
        lines.append(
            f"| {_md(str(item.get('exclude_reason') or ''))} | "
            f"{_md(str(item.get('bookmark_label') or ''))} | "
            f"{_md(str(item.get('source_pdf') or ''))} | "
            f"{_md(str(item.get('unit_id') or ''))} | "
            f"{_md(warnings)} |"
        )
    lines.extend(["", "## Warning", ""])
    warnings = estimate.get("warnings", [])
    if warnings:
        lines.extend(f"- {_md(str(warning))}" for warning in warnings)
    else:
        lines.append("Nessun warning.")
    return "\n".join(lines) + "\n"


def format_casefile_pdf_estimate_csv(estimate: dict[str, object]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow((
        "order", "included", "title/bookmark", "source_pdf",
        "pages", "size_bytes", "warning", "reason",
    ))
    for item in estimate.get("items", []):
        if not isinstance(item, dict):
            continue
        writer.writerow((
            item.get("final_order") or "",
            "si",
            item.get("bookmark_label") or "",
            item.get("source_pdf") or "",
            item.get("estimated_pages") or "",
            item.get("source_size_bytes") or "",
            " | ".join(str(warning) for warning in item.get("warnings", [])),
            "",
        ))
    for item in estimate.get("excluded", []):
        if not isinstance(item, dict):
            continue
        writer.writerow((
            "",
            "no",
            item.get("bookmark_label") or "",
            item.get("source_pdf") or "",
            "",
            "",
            " | ".join(str(warning) for warning in item.get("warnings", [])),
            item.get("exclude_reason") or "",
        ))
    return output.getvalue()


def default_casefile_merged_pdf_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGED_PDF_FILENAME


def default_casefile_optimized_pdf_path(output_dir: Path) -> Path:
    return Path(output_dir) / OPTIMIZED_PDF_FILENAME


def select_casefile_pdf_for_ocr(
    output_dir: Path,
    mode: str | bool = "auto",
    *,
    prefer_light: bool | None = None,
) -> Path | None:
    """Select an existing merged PDF for OCR without opening or creating it."""
    output = Path(output_dir)
    if not output.is_dir():
        raise CaseFilePdfMergeError(
            f"Cartella output del fascicolo non trovata: {output}"
        )
    if prefer_light is not None:
        mode = "auto" if prefer_light else "original"
    elif isinstance(mode, bool):
        mode = "auto" if mode else "original"
    mode = str(mode).strip().lower()
    if mode not in {"auto", "light", "original"}:
        raise CaseFilePdfMergeError(
            f"Modalità PDF per OCR non valida: {mode or '<vuota>'}"
        )
    optimized = default_casefile_optimized_pdf_path(output)
    original = default_casefile_merged_pdf_path(output)
    if mode == "light":
        return optimized if optimized.is_file() else None
    if mode == "original":
        return original if original.is_file() else None
    if optimized.is_file():
        return optimized
    if original.is_file():
        return original
    return None


def default_casefile_pdf_merge_report_json_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGE_REPORT_JSON_FILENAME


def default_casefile_pdf_merge_report_md_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGE_REPORT_MARKDOWN_FILENAME


def select_casefile_merge_plan(output_dir: Path) -> Path:
    """Select the revised plan when present, otherwise the automatic plan."""
    output = Path(output_dir)
    revised = output / REVISED_MERGE_PLAN_JSON_FILENAME
    original = output / MERGE_PLAN_JSON_FILENAME
    if revised.is_file():
        return revised
    if original.is_file():
        return original
    raise CaseFilePdfMergeError(
        "Merge plan non trovato: attesi "
        f"{REVISED_MERGE_PLAN_JSON_FILENAME} o {MERGE_PLAN_JSON_FILENAME}."
    )


def load_merge_plan_for_pdf_merge(path: Path) -> CaseFileMergePlan:
    try:
        plan_path = Path(path)
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        plan = load_casefile_merge_plan(plan_path)
        raw_items = payload.get("items", [])
        items = []
        for item, raw in zip(plan.items, raw_items, strict=True):
            raw_order = raw.get("final_order") if isinstance(raw, dict) else None
            order = int(raw_order) if raw_order is not None else None
            label = str(raw.get("bookmark_label", "")).strip()
            items.append(replace(
                item,
                final_order=order,
                bookmark_label=label or item.bookmark_label,
            ))
        return CaseFileMergePlan(items=tuple(items))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CaseFilePdfMergeError(f"Merge plan non leggibile: {exc}") from exc


def build_casefile_pdf_merge_job(
    casefile_root: Path, output_dir: Path
) -> CaseFilePdfMergeJob:
    root = Path(casefile_root).expanduser()
    output = Path(output_dir).expanduser()
    if not root.is_dir():
        raise CaseFilePdfMergeError("La cartella del fascicolo non esiste.")
    if output.exists() and not output.is_dir():
        raise CaseFilePdfMergeError("Il percorso di output non è una cartella.")
    plan_path = select_casefile_merge_plan(output)
    plan = load_merge_plan_for_pdf_merge(plan_path)
    return CaseFilePdfMergeJob(root.resolve(), output, plan_path, plan)


def resolve_safe_source_pdf(casefile_root: Path, source_pdf: str) -> Path:
    """Resolve an existing relative PDF while containing symlinks below root."""
    normalized = str(source_pdf).strip().replace("\\", "/")
    relative = PurePosixPath(normalized)
    if (
        not normalized
        or relative.is_absolute()
        or ".." in relative.parts
        or (len(normalized) >= 3 and normalized[1:3] == ":/")
    ):
        raise CaseFilePdfMergeError("Il PDF sorgente deve essere un path relativo sicuro.")
    if relative.suffix.casefold() != ".pdf":
        raise CaseFilePdfMergeError(f"Il file sorgente non è un PDF: {normalized}")

    root = Path(casefile_root).resolve()
    candidate = (root / Path(*relative.parts)).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CaseFilePdfMergeError(
            f"Il PDF sorgente esce dalla cartella del fascicolo: {normalized}"
        ) from exc
    if not candidate.is_file():
        raise CaseFilePdfMergeError(f"PDF sorgente non trovato: {normalized}")
    return candidate


def format_bytes(value: int | float | None) -> str:
    """Format a byte count compactly using binary units."""
    if value is None:
        return "non disponibile"
    size = max(0.0, float(value))
    units = ("B", "KB", "MB", "GB", "TB")
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    if unit == "B":
        return f"{int(size)} B"
    digits = 0 if size >= 10 else 1
    return f"{size:.{digits}f} {unit}"


def estimate_casefile_pdf_merge_size(
    job: CaseFilePdfMergeJob,
) -> CaseFilePdfMergeSizeEstimate:
    """Estimate output size from included source files without reading PDF text."""
    included = [item for item in job.plan.items if item.include_in_merged_pdf]
    total_size = 0
    page_count = 0
    pages_available = True
    for item in included:
        source = resolve_safe_source_pdf(job.casefile_root, item.source_pdf)
        total_size += source.stat().st_size
        if item.total_pages is None:
            pages_available = False
        else:
            page_count += item.total_pages
    estimated_pages = page_count if pages_available else None
    average = (
        total_size / estimated_pages
        if estimated_pages is not None and estimated_pages > 0
        else None
    )
    return CaseFilePdfMergeSizeEstimate(
        included_pdf_count=len(included),
        excluded_pdf_count=job.plan.total_items - len(included),
        source_size_bytes=total_size,
        estimated_page_count=estimated_pages,
        average_bytes_per_page=average,
        estimated_output_size_bytes=total_size,
    )


def optimize_casefile_pdf(
    source_pdf: Path, output_pdf: Path, profile: str
) -> Path:
    """Create an optimized copy with local Ghostscript and publish atomically."""
    if profile == "none":
        return Path(source_pdf)
    if profile not in _GHOSTSCRIPT_SETTINGS:
        raise CaseFilePdfMergeError(f"Profilo ottimizzazione PDF non valido: {profile}")
    executable = shutil.which("gs")
    if executable is None:
        raise CaseFilePdfMergeError(
            "Ghostscript non disponibile: impossibile ottimizzare il PDF"
        )
    source = Path(source_pdf)
    output = Path(output_pdf)
    temporary = output.with_name(output.name + ".tmp")
    command = [
        executable,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.7",
        f"-dPDFSETTINGS={_GHOSTSCRIPT_SETTINGS[profile]}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={temporary}",
        str(source),
    ]
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "errore sconosciuto").strip()
            raise CaseFilePdfMergeError(
                f"Ottimizzazione PDF non riuscita (Ghostscript): {detail}"
            )
        if not temporary.is_file() or temporary.stat().st_size < 1:
            raise CaseFilePdfMergeError(
                "Ottimizzazione PDF non riuscita: output vuoto o mancante"
            )
        try:
            optimized_reader = PdfReader(temporary)
            source_reader = PdfReader(source)
            optimized_pages = len(optimized_reader.pages)
            source_pages = len(source_reader.pages)
            if optimized_pages < 1:
                raise ValueError("PDF senza pagine")
            if optimized_pages != source_pages:
                raise ValueError(
                    f"numero pagine diverso ({optimized_pages} invece di {source_pages})"
                )
            if len(optimized_reader.outline) != len(source_reader.outline):
                raise ValueError("numero segnalibri diverso dall'originale")
        except Exception as exc:
            raise CaseFilePdfMergeError(
                f"PDF ottimizzato non leggibile: {exc}"
            ) from exc
        os.replace(temporary, output)
        return output
    finally:
        temporary.unlink(missing_ok=True)


def merge_casefile_pdfs(
    job: CaseFilePdfMergeJob,
    optimization_profile: str = "none",
    progress_callback: CaseFilePdfMergeProgressCallback | None = None,
    cancel_callback: CaseFilePdfMergeCancelCallback | None = None,
) -> CaseFilePdfMergeResult:
    """Preflight all sources, merge them, and atomically publish the outputs."""
    def emit_progress(
        phase: str,
        current: int = 0,
        total: int = 0,
        source_pdf: str | None = None,
        bookmark_label: str | None = None,
        message: str | None = None,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback({
            "phase": phase,
            "current": current,
            "total": total,
            "source_pdf": source_pdf,
            "bookmark_label": bookmark_label,
            "message": message or "",
        })

    def check_cancelled() -> None:
        if cancel_callback is not None and cancel_callback():
            raise CaseFilePdfMergeCancelled(
                "Generazione PDF unico annullata dall’utente."
            )

    if optimization_profile not in PDF_OPTIMIZATION_PROFILES:
        raise CaseFilePdfMergeError(
            f"Profilo ottimizzazione PDF non valido: {optimization_profile}"
        )
    check_cancelled()
    emit_progress("prepare", 0, 0, message="Preparazione merge PDF...")
    estimate = estimate_casefile_pdf_merge_size(job)
    included = sorted(
        (item for item in job.plan.items if item.include_in_merged_pdf),
        key=lambda item: (
            item.final_order is None,
            item.final_order if item.final_order is not None else 999_999,
        ),
    )
    if not included:
        raise CaseFilePdfMergeError("Il merge plan non contiene PDF inclusi.")

    prepared: list[tuple[CaseFileMergePlanItem, Path, PdfReader, int]] = []
    for index, item in enumerate(included, start=1):
        check_cancelled()
        emit_progress(
            "prepare",
            index,
            len(included),
            source_pdf=item.source_pdf,
            bookmark_label=item.bookmark_label,
            message=f"Preparazione unità {index}/{len(included)}",
        )
        source = resolve_safe_source_pdf(job.casefile_root, item.source_pdf)
        try:
            reader = PdfReader(source)
            if reader.is_encrypted:
                raise CaseFilePdfMergeError(
                    "PDF non leggibile o protetto da password: "
                    f"{item.source_pdf}"
                )
            pages = len(reader.pages)
        except Exception as exc:
            if isinstance(exc, CaseFilePdfMergeError):
                raise
            raise CaseFilePdfMergeError(
                f"PDF sorgente non leggibile: {item.source_pdf}: {exc}"
            ) from exc
        if pages < 1:
            raise CaseFilePdfMergeError(f"PDF sorgente senza pagine: {item.source_pdf}")
        prepared.append((item, source, reader, pages))

    job.output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = default_casefile_merged_pdf_path(job.output_dir)
    json_path = default_casefile_pdf_merge_report_json_path(job.output_dir)
    md_path = default_casefile_pdf_merge_report_md_path(job.output_dir)
    pdf_tmp = pdf_path.with_name(pdf_path.name + ".tmp")
    optimized_path = default_casefile_optimized_pdf_path(job.output_dir)
    optimized_tmp = optimized_path.with_name(optimized_path.name + ".tmp")
    writer = PdfWriter()
    report_items: list[dict[str, object]] = []
    page_offset = 0
    actual_size = 0
    optimized_size: int | None = None
    optimized_result_tmp: Path | None = None
    try:
        for index, (item, _source, reader, pages) in enumerate(prepared, start=1):
            check_cancelled()
            label = item.bookmark_label or item.bookmark_title or item.source_pdf
            emit_progress(
                "merge",
                index,
                len(prepared),
                source_pdf=item.source_pdf,
                bookmark_label=label,
                message=f"Aggiunta unità {index}/{len(prepared)}",
            )
            start_index = page_offset
            for page in reader.pages:
                writer.add_page(page)
                page_offset += 1
            writer.add_outline_item(label, start_index)
            report_items.append({
                "final_order": item.final_order,
                "bookmark_label": label,
                "source_pdf": _safe_report_path(item.source_pdf),
                "pages": pages,
                "start_page": start_index + 1,
                "end_page": page_offset,
            })
        check_cancelled()
        emit_progress(
            "write",
            len(prepared),
            len(prepared),
            message="Scrittura PDF unico...",
        )
        with pdf_tmp.open("wb") as stream:
            writer.write(stream)
        check = PdfReader(pdf_tmp)
        if len(check.pages) != page_offset:
            raise CaseFilePdfMergeError("Verifica del PDF unito non riuscita.")
        actual_size = pdf_tmp.stat().st_size
        if optimization_profile != "none":
            check_cancelled()
            emit_progress(
                "optimize",
                len(prepared),
                len(prepared),
                message="Ottimizzazione PDF con Ghostscript...",
            )
            optimized_result_tmp = optimize_casefile_pdf(
                pdf_tmp,
                optimized_tmp,
                optimization_profile,
            )
            optimized_size = optimized_result_tmp.stat().st_size
        check_cancelled()
    except Exception as exc:
        pdf_tmp.unlink(missing_ok=True)
        optimized_tmp.unlink(missing_ok=True)
        if optimized_result_tmp is not None:
            optimized_result_tmp.unlink(missing_ok=True)
        if isinstance(exc, CaseFilePdfMergeError):
            raise
        raise CaseFilePdfMergeError(f"Creazione del PDF unico non riuscita: {exc}") from exc

    excluded = [
        {
            "unit_id": item.unit_id,
            "source_pdf": _safe_report_path(item.source_pdf),
            "exclude_reason": item.exclude_reason or "escluso",
        }
        for item in job.plan.items
        if not item.include_in_merged_pdf
    ]
    published_optimized_path: Path | None = None
    reduction: float | None = None
    warnings: list[str] = []
    if optimized_result_tmp is not None and optimized_size is not None:
        published_optimized_path = optimized_path
        if actual_size:
            reduction = round((actual_size - optimized_size) * 100 / actual_size, 1)
        if optimized_size >= actual_size:
            warnings.append(OPTIMIZED_PDF_NOT_SMALLER_WARNING)
    emit_progress(
        "report",
        len(prepared),
        len(prepared),
        message="Scrittura report PDF unico...",
    )
    report = {
        "source_plan": job.source_plan.name,
        "output_pdf": pdf_path.name,
        "total_items": job.plan.total_items,
        "included_items": len(included),
        "excluded_items": len(excluded),
        "total_pages": page_offset,
        "estimated_source_size_bytes": estimate.source_size_bytes,
        "estimated_source_size_human": format_bytes(estimate.source_size_bytes),
        "estimated_page_count": estimate.estimated_page_count,
        "average_bytes_per_page": estimate.average_bytes_per_page,
        "actual_output_size_bytes": actual_size,
        "actual_output_size_human": format_bytes(actual_size),
        "optimization_profile": optimization_profile,
        "optimized_output_pdf": (
            published_optimized_path.name if published_optimized_path else None
        ),
        "optimized_output_size_bytes": optimized_size,
        "optimized_output_size_human": format_bytes(optimized_size) if optimized_size is not None else None,
        "size_reduction_percent": reduction,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": report_items,
        "excluded": excluded,
        "warnings": warnings,
    }
    try:
        os.replace(pdf_tmp, pdf_path)
        if optimized_result_tmp is not None and published_optimized_path is not None:
            os.replace(optimized_result_tmp, published_optimized_path)
        _atomic_write_text(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        _atomic_write_text(md_path, format_casefile_pdf_merge_report(report))
    except Exception as exc:
        pdf_tmp.unlink(missing_ok=True)
        optimized_tmp.unlink(missing_ok=True)
        if optimized_result_tmp is not None:
            optimized_result_tmp.unlink(missing_ok=True)
        if isinstance(exc, CaseFilePdfMergeError):
            raise
        raise CaseFilePdfMergeError(f"Creazione del PDF unico non riuscita: {exc}") from exc
    emit_progress(
        "done",
        len(prepared),
        len(prepared),
        message="PDF unico generato.",
    )
    return CaseFilePdfMergeResult(
        pdf_path, json_path, md_path, job.source_plan, job.plan.total_items,
        len(included), len(excluded), page_offset,
        estimate.estimated_output_size_bytes, actual_size, optimization_profile,
        published_optimized_path, optimized_size, reduction, tuple(warnings),
    )


def format_casefile_pdf_merge_report(report: dict[str, object]) -> str:
    lines = [
        "# Report PDF unico fascicolo", "",
        f"- Piano usato: {report['source_plan']}",
        f"- PDF generato: {report['output_pdf']}",
        f"- Atti inclusi: {report['included_items']}",
        f"- Atti esclusi: {report['excluded_items']}",
        f"- Pagine totali: {report['total_pages']}", "",
        "## Dimensione PDF", "",
        "- Dimensione stimata da sorgenti inclusi: "
        f"{report['estimated_source_size_human']} (stima; il merge può aggiungere o rimuovere overhead)",
        f"- Dimensione PDF generato: {report['actual_output_size_human']}",
        f"- Profilo ottimizzazione: {report['optimization_profile']}",
        f"- PDF ottimizzato: {report['optimized_output_pdf'] or 'non generato'}",
        "- Dimensione PDF ottimizzato: "
        f"{report['optimized_output_size_human'] or 'non disponibile'}",
        "- Riduzione: "
        f"{str(report['size_reduction_percent']) + '%' if report['size_reduction_percent'] is not None else 'non disponibile'}",
        "",
        "## Atti inclusi", "",
        "| Ordine | Pagine | Segnalibro | PDF |",
        "|---:|---:|---|---|",
    ]
    for item in report["items"]:
        lines.append(
            f"| {item['final_order'] or ''} | {item['pages']} | "
            f"{_md(str(item['bookmark_label']))} | {_md(str(item['source_pdf']))} |"
        )
    lines.extend(["", "## Atti esclusi", "", "| Motivo | PDF | Atto |", "|---|---|---|"])
    for item in report["excluded"]:
        lines.append(
            f"| {_md(str(item['exclude_reason']))} | {_md(str(item['source_pdf']))} "
            f"| {_md(str(item['unit_id']))} |"
        )
    lines.extend(["", "## Warning", ""])
    warnings = report.get("warnings", [])
    lines.extend(f"- {_md(str(warning))}" for warning in warnings)
    if not warnings:
        lines.append("Nessun warning.")
    return "\n".join(lines) + "\n"


def _safe_report_path(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise CaseFilePdfMergeError("Path non sicuro nel report di merge.")
    return str(path).removeprefix("./")


def _merge_plan_item_warning_messages(item: CaseFileMergePlanItem) -> list[str]:
    messages: list[str] = []
    for warning in item.warnings:
        code = str(warning.code or "warning").strip()
        message = str(warning.message or "").strip()
        if message:
            messages.append(f"{code}: {message}" if code else message)
        elif code:
            messages.append(code)
    return messages


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
