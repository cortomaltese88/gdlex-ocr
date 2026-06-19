"""Build and export a reviewable, privacy-safe case-file merge plan."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from gdlex_ocr.casefile import CaseFileAnalysis, ExtractionWarning
from gdlex_ocr.casefile_export import casefile_warning_to_dict

MERGE_PLAN_JSON_FILENAME = "fascicolo_merge_plan.json"
MERGE_PLAN_CSV_FILENAME = "fascicolo_merge_plan.csv"
MERGE_PLAN_MARKDOWN_FILENAME = "fascicolo_merge_plan.md"

EXCLUDE_REASONS = (
    "duplicato",
    "tecnico",
    "irrilevante",
    "escluso_manualmente",
)

_NUMERIC_PREFIX_RE = re.compile(r"^\s*\d+\s*(?:[-–—.:)]\s*)+")
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_BOOKMARK_TITLE_LENGTH = 100


@dataclass(frozen=True, slots=True)
class CaseFileMergePlanItem:
    final_order: int | None
    unit_id: str
    source_pdf: str
    include_in_merged_pdf: bool
    exclude_reason: str | None
    merge_candidate: bool
    bookmark_title: str
    bookmark_label: str
    act_title: str | None
    act_number: str | None
    act_category: str | None
    suggested_order: int | None
    sort_group: str | None
    sort_priority: int | None
    faldone_number: int | None
    index_date: str | None
    pg_progressive: int | None
    total_pages: int | None
    warnings: tuple[ExtractionWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseFileMergePlan:
    items: tuple[CaseFileMergePlanItem, ...]

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_merge_candidates(self) -> int:
        return sum(item.merge_candidate for item in self.items)

    @property
    def total_included(self) -> int:
        return sum(item.include_in_merged_pdf for item in self.items)

    @property
    def total_excluded(self) -> int:
        return self.total_items - self.total_included

    @property
    def estimated_total_pages(self) -> int | None:
        pages = [
            item.total_pages
            for item in self.items
            if item.include_in_merged_pdf and item.total_pages is not None
        ]
        return sum(pages) if pages else None


def build_casefile_merge_plan(analysis: CaseFileAnalysis) -> CaseFileMergePlan:
    """Create the initial editable plan without opening or merging any PDF."""
    units = [unit for unit in analysis.units if unit.main_pdf_path is not None]
    units.sort(key=lambda unit: (
        unit.suggested_order if unit.suggested_order is not None else 999_999,
        unit.faldone_number if unit.faldone_number is not None else 999_999,
        unit.index_date or "9999-99-99",
        unit.pg_progressive if unit.pg_progressive is not None else 999_999,
        _unit_id_key(unit.unit_id),
    ))

    items: list[CaseFileMergePlanItem] = []
    for final_order, unit in enumerate(units, 1):
        title = _bookmark_title(unit.act_title, unit.unit_id)
        items.append(CaseFileMergePlanItem(
            final_order=final_order,
            unit_id=str(unit.unit_id),
            source_pdf=_safe_relative_path(unit.main_pdf_path),
            include_in_merged_pdf=True,
            exclude_reason=None,
            merge_candidate=True,
            bookmark_title=title,
            bookmark_label=f"{final_order:03d} - {title}",
            act_title=unit.act_title,
            act_number=unit.act_number,
            act_category=unit.act_category,
            suggested_order=unit.suggested_order,
            sort_group=unit.sort_group,
            sort_priority=unit.sort_priority,
            faldone_number=unit.faldone_number,
            index_date=unit.index_date,
            pg_progressive=unit.pg_progressive,
            total_pages=unit.total_pages,
            warnings=unit.warnings,
        ))
    return CaseFileMergePlan(items=tuple(items))


def default_casefile_merge_plan_json_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGE_PLAN_JSON_FILENAME


def default_casefile_merge_plan_csv_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGE_PLAN_CSV_FILENAME


def default_casefile_merge_plan_markdown_path(output_dir: Path) -> Path:
    return Path(output_dir) / MERGE_PLAN_MARKDOWN_FILENAME


# Compatibility aliases for the names used during the initial development pass.
default_merge_plan_json_path = default_casefile_merge_plan_json_path
default_merge_plan_csv_path = default_casefile_merge_plan_csv_path
default_merge_plan_markdown_path = default_casefile_merge_plan_markdown_path


def merge_plan_to_dict(plan: CaseFileMergePlan) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for item in plan.items:
        payload = asdict(item)
        payload["source_pdf"] = _safe_relative_path(item.source_pdf)
        payload["warnings"] = [casefile_warning_to_dict(w) for w in item.warnings]
        items.append(payload)
    return {
        "summary": {
            "total_items": plan.total_items,
            "included": plan.total_included,
            "excluded": plan.total_excluded,
            "merge_candidates": plan.total_merge_candidates,
            "estimated_total_pages": plan.estimated_total_pages,
        },
        "exclude_reason_values": list(EXCLUDE_REASONS),
        "items": items,
    }


def write_casefile_merge_plan_json(
    plan: CaseFileMergePlan, output_path: Path, *, indent: int = 2
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(merge_plan_to_dict(plan), ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )
    return path


def format_casefile_merge_plan_csv(plan: CaseFileMergePlan) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow((
        "Ordine finale", "Ordine suggerito", "Candidato merge", "Includi",
        "Motivo esclusione", "Segnalibro",
        "PDF sorgente", "Unità", "Atto", "Numero atto ministeriale",
        "Categoria", "Faldone", "Data atto", "Progressivo PG", "Pagine",
        "Gruppo ordinamento", "Priorità ordinamento", "Warning",
    ))
    for item in plan.items:
        writer.writerow((
            item.final_order or "",
            item.suggested_order if item.suggested_order is not None else "",
            "sì" if item.merge_candidate else "no",
            "sì" if item.include_in_merged_pdf else "no",
            item.exclude_reason or "", item.bookmark_label,
            _safe_relative_path(item.source_pdf), item.unit_id, item.act_title or "",
            item.act_number or "", item.act_category or "",
            item.faldone_number if item.faldone_number is not None else "",
            item.index_date or "",
            item.pg_progressive if item.pg_progressive is not None else "",
            item.total_pages if item.total_pages is not None else "",
            item.sort_group or "",
            item.sort_priority if item.sort_priority is not None else "",
            " | ".join(_warning_text(w) for w in item.warnings),
        ))
    return output.getvalue()


def write_casefile_merge_plan_csv(plan: CaseFileMergePlan, output_path: Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_casefile_merge_plan_csv(plan), encoding="utf-8-sig")
    return path


def format_casefile_merge_plan_markdown(plan: CaseFileMergePlan) -> str:
    pages = plan.estimated_total_pages
    lines = [
        "# Piano merge fascicolo", "", "## Riepilogo merge plan", "",
        f"- Totale item: {plan.total_items}",
        f"- Inclusi: {plan.total_included}",
        f"- Esclusi: {plan.total_excluded}",
        f"- Candidati merge: {plan.total_merge_candidates}",
        f"- Pagine totali stimate: {pages if pages is not None else 'non disponibili'}",
        "", "## Piano", "",
        "| Ordine finale | Includi | Motivo esclusione | Segnalibro | Categoria | PDF | Pagine | Warning |",
        "|---:|:---:|---|---|---|---|---:|---|",
    ]
    for item in plan.items:
        warnings = "<br>".join(_md(_warning_text(w)) for w in item.warnings)
        lines.append(
            f"| {item.final_order or ''} | {'sì' if item.include_in_merged_pdf else 'no'} "
            f"| {_md(item.exclude_reason or '')} | {_md(item.bookmark_label)} "
            f"| {_md(item.act_category or '')} "
            f"| {_md(_safe_relative_path(item.source_pdf))} "
            f"| {item.total_pages if item.total_pages is not None else ''} | {warnings} |"
        )
    return "\n".join(lines) + "\n"


def write_casefile_merge_plan_markdown(plan: CaseFileMergePlan, output_path: Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_casefile_merge_plan_markdown(plan), encoding="utf-8")
    return path


def _bookmark_title(act_title: str | None, unit_id: str) -> str:
    title = _clean_text(act_title or "")
    title = _NUMERIC_PREFIX_RE.sub("", title).strip(" -–—.:)")
    title = title or f"Unità {unit_id}"
    if len(title) > _MAX_BOOKMARK_TITLE_LENGTH:
        return title[: _MAX_BOOKMARK_TITLE_LENGTH - 3].rstrip() + "..."
    return title


def _unit_id_key(unit_id: str) -> tuple[int, int | str]:
    text = str(unit_id)
    return (0, int(text)) if text.isdigit() else (1, text.casefold())


def _safe_optional_path(value: str | None) -> str | None:
    return None if value is None else _safe_relative_path(value)


def _safe_relative_path(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:/", normalized):
        return path.name
    return str(path).removeprefix("./")


def _clean_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value)).strip()


def _warning_text(warning: ExtractionWarning) -> str:
    return str(casefile_warning_to_dict(warning)["message"])


def _md(value: object) -> str:
    return _clean_text(str(value)).replace("|", "\\|").replace("\n", " ")
