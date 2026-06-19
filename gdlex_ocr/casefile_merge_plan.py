"""Deterministic merge-planning metadata for PDP/TIAP documentary units."""

from __future__ import annotations

import logging
import re
from dataclasses import replace

from gdlex_ocr.casefile import CaseFileUnit, ExtractionWarning

_MAX_BOOKMARK_TITLE_LENGTH = 100

_PLAUSIBLE_YEAR_MIN = 1950
_PLAUSIBLE_YEAR_MAX = 2099
_DATE_DMY_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_DATE_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

ANOMALOUS_DATE_WARNING = "anomalous_date"

logger = logging.getLogger(__name__)

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
    ordered = _compute_suggested_order(units)
    result: list[CaseFileUnit] = []
    for unit, (order, source_kind, source_value, source_confidence, extra_warnings) in zip(
        units, ordered
    ):
        bookmark = _build_bookmark_title(unit)
        group, priority = _resolve_sort_group(unit)
        merge = unit.main_pdf_path is not None
        warnings = unit.warnings + extra_warnings
        result.append(replace(
            unit,
            bookmark_title=bookmark,
            sort_group=group,
            sort_priority=priority,
            suggested_order=order,
            order_source_kind=source_kind,
            order_source_value=source_value,
            order_source_confidence=source_confidence,
            merge_candidate=merge,
            warnings=warnings,
        ))
    return tuple(result)


def _compute_suggested_order(
    units: tuple[CaseFileUnit, ...],
) -> list[tuple[int, str, str, str, tuple[ExtractionWarning, ...]]]:
    """Assign suggested_order using a conservative hierarchy.

    Priority: faldone_number → index_date (parsed) → pg_progressive → unit_id.
    """
    keyed: list[tuple[tuple[int, int, int, int], int, str, str, str, tuple[ExtractionWarning, ...]]] = []

    for i, unit in enumerate(units):
        faldone_key = unit.faldone_number if unit.faldone_number is not None else 0
        date_key, date_anomaly = _parse_date_sort_key(unit.index_date)
        pg_key = unit.pg_progressive if unit.pg_progressive is not None else 999_999
        unit_id_key = _numeric_unit_id(unit.unit_id)

        extra_warnings: tuple[ExtractionWarning, ...] = ()
        confidence = "high"

        if date_anomaly:
            extra_warnings = (ExtractionWarning(
                code=ANOMALOUS_DATE_WARNING,
                message=f"Data atto anomala: {unit.index_date}",
                path=unit.attachment_index_path,
            ),)
            confidence = "low"
            logger.warning(
                "Anomalous date %s in unit %s", unit.index_date, unit.unit_id
            )

        if unit.faldone_number is not None:
            source_kind = "faldone+data+pg+unit_id"
        elif date_key < (9999, 99, 99):
            source_kind = "data+pg+unit_id"
        elif unit.pg_progressive is not None:
            source_kind = "pg+unit_id"
        else:
            source_kind = "unit_id"
            confidence = "low"

        sort_key = (faldone_key, *date_key, pg_key, unit_id_key)
        source_value = (
            f"faldone={faldone_key} "
            f"date={date_key} "
            f"pg={pg_key} "
            f"uid={unit_id_key}"
        )
        keyed.append((sort_key, i, source_kind, source_value, confidence, extra_warnings))

    keyed.sort(key=lambda x: x[0])

    result: list[tuple[int, str, str, str, tuple[ExtractionWarning, ...]]] = [
        (0, "", "", "", ()) for _ in units
    ]
    for order, (_, original_index, source_kind, source_value, confidence, extra_warnings) in enumerate(
        keyed, 1
    ):
        result[original_index] = (order, source_kind, source_value, confidence, extra_warnings)

    return result


def _parse_date_sort_key(
    date_str: str | None,
) -> tuple[tuple[int, int, int], bool]:
    """Parse a date string into (year, month, day) for sorting.

    Returns ((9999, 99, 99), False) if unparseable, and flags anomalous years.
    """
    if not date_str:
        return (9999, 99, 99), False

    match = _DATE_DMY_RE.match(date_str.strip())
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        anomaly = year < _PLAUSIBLE_YEAR_MIN or year > _PLAUSIBLE_YEAR_MAX
        return (year, month, day), anomaly

    match = _DATE_ISO_RE.match(date_str.strip())
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        anomaly = year < _PLAUSIBLE_YEAR_MIN or year > _PLAUSIBLE_YEAR_MAX
        return (year, month, day), anomaly

    return (9999, 99, 99), False


def _numeric_unit_id(unit_id: str) -> int:
    try:
        return int(unit_id)
    except (ValueError, TypeError):
        return 999_999_999


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
