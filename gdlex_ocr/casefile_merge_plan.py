"""Deterministic merge-planning metadata for PDP/TIAP documentary units."""

from __future__ import annotations

from dataclasses import replace

from gdlex_ocr.casefile import CaseFileUnit

_MAX_BOOKMARK_TITLE_LENGTH = 100

SORT_GROUP_MAP: dict[str, tuple[str, int]] = {
    "querela_denuncia": ("querele_denunce", 10),
    "informativa": ("atti_pg", 20),
    "delega_indagini": ("atti_pg", 21),
    "annotazione": ("atti_pg", 22),
    "relazione_servizio": ("atti_pg", 23),
    "seguito_indagine": ("atti_pg", 24),
    "sit_sommarie_informazioni": ("atti_pg", 30),
    "verbale": ("verbali", 40),
    "certificato": ("certificati", 50),
    "documentazione_sanitaria": ("documentazione", 55),
    "documentazione_amministrativa": ("documentazione", 56),
    "notifica": ("notifiche", 60),
    "comunicazione": ("comunicazioni", 65),
    "elezione_domicilio": ("atti_difesa", 70),
    "nomina_difensore": ("atti_difesa", 71),
    "provvedimento_pm": ("provvedimenti", 80),
    "provvedimento_gip_gup": ("provvedimenti", 81),
    "altro": ("altro", 90),
}

SORT_GROUP_LABELS: dict[str, str] = {
    "querele_denunce": "Querele/Denunce",
    "atti_pg": "Atti PG",
    "atti_pg_sit": "SIT",
    "verbali": "Verbali",
    "certificati": "Certificati",
    "documentazione": "Documentazione",
    "notifiche": "Notifiche",
    "comunicazioni": "Comunicazioni",
    "atti_difesa": "Atti difesa",
    "provvedimenti": "Provvedimenti",
    "altro": "Altro",
}


def plan_merge_metadata(
    units: tuple[CaseFileUnit, ...],
) -> tuple[CaseFileUnit, ...]:
    """Compute bookmark_title, sort_group, sort_priority, suggested_order, merge_candidate."""
    result: list[CaseFileUnit] = []
    for i, unit in enumerate(units, 1):
        bookmark = _build_bookmark_title(unit)
        group, priority = _resolve_sort_group(unit)
        order = _resolve_suggested_order(unit, i)
        merge = unit.main_pdf_path is not None
        result.append(replace(
            unit,
            bookmark_title=bookmark,
            sort_group=group,
            sort_priority=priority,
            suggested_order=order,
            merge_candidate=merge,
        ))
    return tuple(result)


def _build_bookmark_title(unit: CaseFileUnit) -> str:
    parts: list[str] = []
    if unit.act_number is not None:
        parts.append(str(unit.act_number).zfill(3))
    if unit.act_title:
        parts.append(unit.act_title.strip())
    if not parts:
        parts.append(f"Unità {unit.unit_id}")
    title = " - ".join(parts)
    if len(title) > _MAX_BOOKMARK_TITLE_LENGTH:
        title = title[:_MAX_BOOKMARK_TITLE_LENGTH - 3] + "..."
    return title


def _resolve_sort_group(unit: CaseFileUnit) -> tuple[str, int]:
    cat = unit.act_category or "altro"
    return SORT_GROUP_MAP.get(cat, ("altro", 90))


def _resolve_suggested_order(unit: CaseFileUnit, fallback_index: int) -> int:
    if unit.act_number is not None:
        try:
            return int(unit.act_number)
        except (ValueError, TypeError):
            pass
    return fallback_index
