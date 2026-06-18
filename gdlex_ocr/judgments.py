"""Offline heuristic extraction for criminal judgment Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from gdlex_ocr.manifest import MANIFEST_FILENAME, load_manifest, safe_write_manifest

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
JUDGMENT_ANALYSIS_FILENAME = "sentenza_analysis.md"
SNIPPET_MAX_LENGTH = 150
MANIFEST_VALUE_MAX_LENGTH = 120
MANIFEST_WARNING_MAX_LENGTH = 240
MANIFEST_LIST_MAX_ITEMS = 20

_SPACE_RE = re.compile(r"\s+")
_BLOCK_RE = re.compile(
    r"^(?:#{1,6}\s*)?Blocco\s+\d+\s*-\s*Pagine\s+(\d+)\s*[-–]\s*\d+",
    re.IGNORECASE,
)
_COMMENT_BLOCK_RE = re.compile(
    r"^<!--\s*Blocco\s+\d+:\s*pagine\s+originali\s+(\d+)\s*[-–]\s*\d+\s*-->$",
    re.IGNORECASE,
)
_PAGE_RE = re.compile(r"\bpag(?:ina)?\.?\s+(\d+)\b", re.IGNORECASE)
_DATE_RE = re.compile(
    r"\b("
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}\s+"
    r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|"
    r"agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+\d{4}"
    r")\b",
    re.IGNORECASE,
)
_APOS = "'‘’"
_AUTHORITY_CITY_CHARS = "[A-Za-zÀ-ÿ" + _APOS + " ]+"
_D_APOS = "[" + _APOS + "]"
_AUTHORITY_RE = re.compile(
    r"\b("
    r"Corte\s+di\s+Assise\s+d" + _D_APOS + r"Appello\s+di\s+" + _AUTHORITY_CITY_CHARS + r"|"
    r"Corte\s+di\s+Assise\s+di\s+Appello\s+di\s+" + _AUTHORITY_CITY_CHARS + r"|"
    r"Corte\s+di\s+Assise\s+di\s+" + _AUTHORITY_CITY_CHARS + r"|"
    r"Corte\s+d" + _D_APOS + r"Appello\s+di\s+" + _AUTHORITY_CITY_CHARS + r"|"
    r"Giudice\s+di\s+Pace\s+di\s+" + _AUTHORITY_CITY_CHARS + r"|"
    r"Tribunale\s+(?:ordinario\s+)?di\s+" + _AUTHORITY_CITY_CHARS + r""
    r")",
    re.IGNORECASE,
)
_AUTHORITY_TRAILING_RE = re.compile(
    r"\s+(?:"
    r"sezione|in\s+composizione|composizione|penale|civile|"
    r"ha\b|pronuncia\b|emette\b|in\s+persona\b|nella\s+persona\b"
    r")\b.*$",
    re.IGNORECASE,
)
_SENTENCE_NUMBER_RE = re.compile(
    r"\bsentenza\s*(?:n\.?|numero)?\s*[:.]?\s*"
    r"([0-9]+(?:/[0-9]{2,4})?)\b",
    re.IGNORECASE,
)
_PROCEEDING_NUMBER_RE = re.compile(
    r"\b(?:"
    r"r\.?\s*g\.?\s*n\.?\s*r\.?|"
    r"r\.?\s*g\.?|"
    r"n\.?\s*r\.?\s*g\.?|"
    r"proc(?:edimento)?(?:\s+penale)?"
    r")\s*(?:n\.?|numero)?\s*[:.]?\s*"
    r"([0-9]+(?:/[0-9]{2,4})?)\b",
    re.IGNORECASE,
)
_JUDGE_RE = re.compile(
    r"\b(?:"
    r"giudice(?:\s+monocratico)?|"
    r"in\s+persona\s+del\s+giudice"
    r")\s+(?:dott\.ssa|dott\.?|dr\.ssa|dr\.?)?\s*"
    r"([A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’.-]+){0,3})",
    re.IGNORECASE,
)
_WORD_TO_DAYS: dict[str, str] = {
    "trenta": "30",
    "quarantacinque": "45",
    "sessanta": "60",
    "novanta": "90",
}
_DAYS_NUMBER = r"(?:[0-9]{1,3}|" + "|".join(_WORD_TO_DAYS) + r")"
_DEADLINE_RE = re.compile(
    r"\b(?:"
    r"(?:entro|in|nel\s+termine\s+di|termine\s+di|termine\s+per\s+il\s+"
    r"deposito\s+della\s+motivazione\s+di)\s+"
    r"(" + _DAYS_NUMBER + r")\s+giorni|"
    r"giorni\s+(" + _DAYS_NUMBER + r")"
    r")\b",
    re.IGNORECASE,
)
_DISPOSITIVE_START_RE = re.compile(
    r"^(?:p\.?\s*q\.?\s*m\.?|per\s+questi\s+motivi|dispositivo)\s*[:.]?$",
    re.IGNORECASE,
)
_CONDANNA_RE = re.compile(
    r"\b(?:condanna|condannato|dichiara\s+.+?\bcolpevole)\b",
    re.IGNORECASE,
)
_E_ACCENT = "[eéè" + _APOS + "]+"
_ASSOLUZIONE_RE = re.compile(
    r"\b(?:assolve|assolto|assoluzione|il\s+fatto\s+non\s+sussiste|"
    r"perch" + _E_ACCENT + r"\s+il\s+fatto\s+non\s+sussiste|"
    r"perch" + _E_ACCENT + r"\s+non\s+costituisce\s+reato|"
    r"per\s+non\s+aver\s+commesso\s+il\s+fatto|"
    r"il\s+fatto\s+non\s+" + _E_ACCENT + r"\s+previsto\s+dalla\s+legge\s+come\s+reato)\b",
    re.IGNORECASE,
)
_PROSCIOGLIMENTO_RE = re.compile(
    r"\b(?:proscioglie|proscioglimento|non\s+doversi\s+procedere|"
    r"estinzione\s+del\s+reato|estinto\s+il\s+reato|"
    r"prescrizione|"
    r"remissione\s+(?:della\s+)?querela|"
    r"difetto\s+di\s+querela)\b",
    re.IGNORECASE,
)
_PATTEGGIAMENTO_RE = re.compile(
    r"\b(?:patteggiamento|"
    r"pena\s+(?:concordata|su\s+richiesta)|"
    r"applica\s+la\s+pena\s+(?:concordata|su\s+richiesta)|"
    r"art\.?\s*444\s*c\.?\s*p\.?\s*p\.?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExtractedField:
    value: str
    confidence: str
    source: str


@dataclass(frozen=True, slots=True)
class JudgmentAnalysis:
    detected: bool
    authority: ExtractedField | None
    composition: ExtractedField | None
    judge: ExtractedField | None
    sentence_number: ExtractedField | None
    proceeding_number: ExtractedField | None
    hearing_or_decision_date: ExtractedField | None
    motivation_type: ExtractedField | None
    motivation_deadline: ExtractedField | None
    deposit_date: ExtractedField | None
    outcome: ExtractedField | None
    dispositive_keywords: tuple[str, ...]
    missing_fields: tuple[str, ...]
    warnings: tuple[str, ...]


_MANIFEST_FIELD_NAMES = (
    "authority",
    "composition",
    "judge",
    "sentence_number",
    "proceeding_number",
    "hearing_or_decision_date",
    "motivation_type",
    "motivation_deadline",
    "deposit_date",
    "outcome",
)


@dataclass(frozen=True, slots=True)
class _Line:
    number: int
    text: str
    page: int | None


def extract_judgment_metadata(markdown: str) -> JudgmentAnalysis:
    """Extract a conservative judgment profile from already-produced Markdown."""
    lines = _split_lines(markdown)
    authority = _extract_authority(lines)
    composition = _extract_composition(lines, authority)
    judge = _extract_judge(lines)
    sentence_number = _extract_sentence_number(lines)
    proceeding_number = _extract_proceeding_number(lines)
    hearing_or_decision_date = _extract_decision_date(lines)
    motivation_type, motivation_deadline = _extract_motivation(lines)
    deposit_date = _extract_deposit_date(lines)
    outcome, keywords = _extract_outcome(lines)
    detected = _looks_like_judgment(
        lines,
        authority,
        sentence_number,
        hearing_or_decision_date,
        outcome,
    )

    if not detected:
        return JudgmentAnalysis(
            detected=False,
            authority=None,
            composition=None,
            judge=None,
            sentence_number=None,
            proceeding_number=None,
            hearing_or_decision_date=None,
            motivation_type=None,
            motivation_deadline=None,
            deposit_date=None,
            outcome=None,
            dispositive_keywords=(),
            missing_fields=(),
            warnings=("Testo non riconosciuto come sentenza.",),
        )

    missing_fields = _missing_fields(
        authority=authority,
        composition=composition,
        judge=judge,
        sentence_number=sentence_number,
        proceeding_number=proceeding_number,
        hearing_or_decision_date=hearing_or_decision_date,
        motivation_type=motivation_type,
        motivation_deadline=motivation_deadline,
        deposit_date=deposit_date,
        outcome=outcome,
    )
    warnings = _warnings(motivation_type, motivation_deadline, deposit_date, outcome)

    return JudgmentAnalysis(
        detected=True,
        authority=authority,
        composition=composition,
        judge=judge,
        sentence_number=sentence_number,
        proceeding_number=proceeding_number,
        hearing_or_decision_date=hearing_or_decision_date,
        motivation_type=motivation_type,
        motivation_deadline=motivation_deadline,
        deposit_date=deposit_date,
        outcome=outcome,
        dispositive_keywords=tuple(keywords),
        missing_fields=tuple(missing_fields),
        warnings=tuple(warnings),
    )


def format_judgment_summary(analysis: JudgmentAnalysis) -> str:
    """Render a short Markdown card for review, without long source excerpts."""
    if not analysis.detected:
        return "\n".join(
            [
                "# Scheda sentenza",
                "",
                "Testo non riconosciuto come sentenza.",
            ]
        )

    missing = (
        ", ".join(analysis.missing_fields)
        if analysis.missing_fields
        else "nessuno tra i campi MVP"
    )
    keywords = (
        ", ".join(analysis.dispositive_keywords)
        if analysis.dispositive_keywords
        else "non rilevate"
    )
    alerts = list(analysis.warnings) or ["Nessun alert euristico rilevato."]
    alert_lines = [f"- {alert}" for alert in alerts]
    alert_lines.append(f"- Dati mancanti da verificare: {missing}")

    return "\n".join(
        [
            "# Scheda sentenza",
            "",
            "## Dati provvedimento",
            f"- Autorità giudiziaria: {_field_value(analysis.authority)}",
            f"- Composizione: {_field_value(analysis.composition)}",
            f"- Giudice: {_field_value(analysis.judge)}",
            f"- Numero sentenza: {_field_value(analysis.sentence_number)}",
            f"- Numero procedimento: {_field_value(analysis.proceeding_number)}",
            "",
            "## Date rilevanti",
            f"- Udienza / dispositivo: "
            f"{_field_value(analysis.hearing_or_decision_date)}",
            f"- Motivazione: {_field_value(analysis.motivation_type)}",
            f"- Termine motivazione: "
            f"{_field_value(analysis.motivation_deadline)}",
            f"- Deposito: {_field_value(analysis.deposit_date)}",
            "",
            "## Esito",
            f"- Dispositivo: {_field_value(analysis.outcome)}",
            f"- Parole chiave: {keywords}",
            "",
            "## Alert impugnazione",
            *alert_lines,
        ]
    )


def prepend_judgment_summary(markdown: str, analysis: JudgmentAnalysis) -> str:
    """Place the judgment card before the original Markdown text."""
    original = markdown.lstrip("\n")
    return f"{format_judgment_summary(analysis)}\n\n---\n\n{original}"


def write_judgment_analysis_for_markdown(
    markdown_path: Path,
    output_dir: Path | None = None,
    *,
    log_callback: Callable[[str], None] | None = print,
    update_manifest: bool = False,
    manifest: dict[str, Any] | None = None,
) -> Path:
    """Write a separate judgment-analysis card next to a Markdown output."""
    destination_dir = markdown_path.parent if output_dir is None else output_dir
    output_path = destination_dir / JUDGMENT_ANALYSIS_FILENAME

    if log_callback is not None:
        log_callback("Analisi sentenza richiesta.")
        log_callback(f"Markdown sentenza letto: {markdown_path}")

    markdown = markdown_path.read_text(encoding="utf-8")
    analysis = extract_judgment_metadata(markdown)
    summary = format_judgment_summary(analysis)

    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")

    if update_manifest:
        _update_judgment_analysis_manifest(
            destination_dir,
            analysis,
            output_path,
            log_callback=log_callback,
            manifest=manifest,
        )

    if log_callback is not None:
        if not analysis.detected:
            log_callback("Avviso: il testo non sembra una sentenza.")
        log_callback(f"Scheda sentenza scritta: {output_path}")

    return output_path


def _update_judgment_analysis_manifest(
    output_dir: Path,
    analysis: JudgmentAnalysis,
    output_path: Path,
    *,
    log_callback: Callable[[str], None] | None = print,
    manifest: dict[str, Any] | None = None,
) -> bool:
    manifest_path = output_dir / MANIFEST_FILENAME
    if manifest is None:
        try:
            manifest = load_manifest(manifest_path)
        except (OSError, ValueError) as exc:
            if log_callback is not None:
                log_callback(f"Avviso: manifest non aggiornato: {exc}")
            return False

    try:
        output_file = output_path.relative_to(output_dir)
    except ValueError:
        output_file = output_path
    manifest["judgment_analysis"] = judgment_analysis_to_manifest_dict(
        analysis,
        output_file,
    )
    written = safe_write_manifest(manifest, output_dir)
    if log_callback is not None:
        if written:
            log_callback(f"Manifest aggiornato: {manifest_path}")
        else:
            log_callback("Avviso: manifest non aggiornato per errore di scrittura.")
    return written


def judgment_analysis_to_manifest_dict(
    analysis: JudgmentAnalysis,
    output_path_relative: str | Path,
) -> dict[str, object]:
    """Return content-free judgment analysis metadata for manifest.json."""
    fields = {
        name: _manifest_field(getattr(analysis, name))
        for name in _MANIFEST_FIELD_NAMES
    }
    return {
        "enabled": True,
        "detected": analysis.detected,
        "output_file": _manifest_path(output_path_relative),
        "fields": fields,
        "dispositive_keywords": [
            keyword for keyword in _dedupe(
                _manifest_keyword(item)
                for item in analysis.dispositive_keywords
                if _manifest_keyword(item) is not None
            )
        ][:MANIFEST_LIST_MAX_ITEMS],
        "missing_fields": [
            item for item in (
                _manifest_short_text(value, MANIFEST_VALUE_MAX_LENGTH)
                for value in analysis.missing_fields
            )
            if item is not None
        ][:MANIFEST_LIST_MAX_ITEMS],
        "warnings": [
            item for item in (
                _manifest_short_text(value, MANIFEST_WARNING_MAX_LENGTH)
                for value in analysis.warnings
            )
            if item is not None
        ][:MANIFEST_LIST_MAX_ITEMS],
    }


def _split_lines(markdown: str) -> list[_Line]:
    lines: list[_Line] = []
    current_page: int | None = None
    for index, raw_line in enumerate(markdown.splitlines(), start=1):
        text = _clean_line(raw_line)
        block_match = _BLOCK_RE.match(text) or _COMMENT_BLOCK_RE.match(text)
        if block_match:
            current_page = int(block_match.group(1))
        elif page_match := _PAGE_RE.search(text):
            current_page = int(page_match.group(1))
        lines.append(_Line(index, text, current_page))
    return lines


def _extract_authority(lines: list[_Line]) -> ExtractedField | None:
    for line in lines:
        match = _AUTHORITY_RE.search(line.text)
        if not match:
            continue
        value = _AUTHORITY_TRAILING_RE.sub("", match.group(1))
        value = _clean_value(value)
        return ExtractedField(value, CONFIDENCE_HIGH, _source(line))
    return None


def _extract_composition(
    lines: list[_Line],
    authority: ExtractedField | None,
) -> ExtractedField | None:
    joined = "\n".join(line.text for line in lines[:40])
    source_line = _first_line_matching(
        lines,
        re.compile(r"\b(?:monocratica|monocratico)\b", re.IGNORECASE),
    )
    if source_line is not None:
        return ExtractedField("monocratica", CONFIDENCE_HIGH, _source(source_line))

    source_line = _first_line_matching(
        lines,
        re.compile(r"\bcollegiale\b", re.IGNORECASE),
    )
    if source_line is not None:
        return ExtractedField("collegiale", CONFIDENCE_HIGH, _source(source_line))

    if authority is not None:
        key = authority.value.casefold()
        if "giudice di pace" in key:
            return ExtractedField(
                "Giudice di Pace",
                CONFIDENCE_HIGH,
                authority.source,
            )
        if "corte di assise" in key:
            return ExtractedField(
                "Corte d'Assise",
                CONFIDENCE_HIGH,
                authority.source,
            )

    if re.search(r"\btribunale\b", joined, re.IGNORECASE):
        return ExtractedField(
            "non rilevata",
            CONFIDENCE_LOW,
            "intestazione sentenza senza composizione esplicita",
        )
    return None


def _extract_judge(lines: list[_Line]) -> ExtractedField | None:
    for line in lines:
        if "giudice di pace" in line.text.casefold():
            continue
        match = _JUDGE_RE.search(line.text)
        if not match:
            continue
        value = _clean_value(match.group(1))
        value = re.sub(
            r"\b(?:ha|pronunciato|emesso|la|seguente)\b.*$",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()
        if value and value.casefold() not in {"monocratico", "pace"}:
            return ExtractedField(value, CONFIDENCE_MEDIUM, _source(line))
    return None


def _extract_sentence_number(lines: list[_Line]) -> ExtractedField | None:
    for line in lines:
        match = _SENTENCE_NUMBER_RE.search(line.text)
        if match:
            return ExtractedField(match.group(1), CONFIDENCE_HIGH, _source(line))
    return None


def _extract_proceeding_number(lines: list[_Line]) -> ExtractedField | None:
    for line in lines:
        match = _PROCEEDING_NUMBER_RE.search(line.text)
        if match and "sentenza" not in line.text.casefold():
            return ExtractedField(match.group(1), CONFIDENCE_HIGH, _source(line))
    return None


def _extract_decision_date(lines: list[_Line]) -> ExtractedField | None:
    date_terms = re.compile(
        r"\b(?:udienza|pronuncia|dispositivo|deciso|decisione)\b",
        re.IGNORECASE,
    )
    fallback: ExtractedField | None = None
    for line in lines:
        date = _DATE_RE.search(line.text)
        if date is None:
            continue
        if date_terms.search(line.text):
            return ExtractedField(date.group(1), CONFIDENCE_HIGH, _source(line))
        if fallback is None:
            fallback = ExtractedField(date.group(1), CONFIDENCE_LOW, _source(line))
    return fallback


def _extract_motivation(
    lines: list[_Line],
) -> tuple[ExtractedField | None, ExtractedField | None]:
    motivation_type: ExtractedField | None = None
    motivation_deadline: ExtractedField | None = None
    for line in lines:
        text = line.text.casefold()
        if "motiv" not in text:
            continue
        deadline_match = _DEADLINE_RE.search(line.text)
        if deadline_match and motivation_deadline is None:
            raw = deadline_match.group(1) or deadline_match.group(2)
            value = _WORD_TO_DAYS.get(raw.casefold(), raw)
            motivation_deadline = ExtractedField(
                f"{value} giorni",
                CONFIDENCE_HIGH,
                _source(line),
            )
        if re.search(r"\briserv", text):
            motivation_type = ExtractedField(
                "riservata",
                CONFIDENCE_HIGH,
                _source(line),
            )
        elif re.search(r"\bcontestual", text):
            motivation_type = ExtractedField(
                "contestuale",
                CONFIDENCE_HIGH,
                _source(line),
            )

    if motivation_type is None:
        source = "nessuna formula di motivazione riconosciuta"
        motivation_type = ExtractedField("non rilevata", CONFIDENCE_LOW, source)
    return motivation_type, motivation_deadline


def _extract_deposit_date(lines: list[_Line]) -> ExtractedField | None:
    for line in lines:
        text = line.text.casefold()
        if not re.search(r"\bdeposit(?:ata|ato|o|ata\s+in\s+cancelleria)\b", text):
            continue
        if "termine" in text and "giorni" in text:
            continue
        date = _DATE_RE.search(line.text)
        if date:
            return ExtractedField(date.group(1), CONFIDENCE_HIGH, _source(line))
    return None


def _extract_outcome(
    lines: list[_Line],
) -> tuple[ExtractedField | None, list[str]]:
    dispositive_lines = _dispositive_lines(lines)
    if not dispositive_lines:
        return None, []
    text = "\n".join(line.text for line in dispositive_lines)
    matches: dict[str, list[str]] = {
        "condanna": _keywords(_CONDANNA_RE, text),
        "assoluzione": _keywords(_ASSOLUZIONE_RE, text),
        "proscioglimento / non doversi procedere": _keywords(
            _PROSCIOGLIMENTO_RE,
            text,
        ),
        "patteggiamento": _keywords(_PATTEGGIAMENTO_RE, text),
    }
    present = [name for name, values in matches.items() if values]
    keywords = _dedupe(
        keyword
        for values in matches.values()
        for keyword in values
    )
    source_line = dispositive_lines[0] if dispositive_lines else None

    if len(present) > 1:
        return (
            ExtractedField(
                "ambiguo",
                CONFIDENCE_LOW,
                _source(source_line) if source_line else "dispositivo non isolato",
            ),
            keywords,
        )
    if len(present) == 1:
        return (
            ExtractedField(
                present[0],
                CONFIDENCE_HIGH,
                _source(source_line) if source_line else "dispositivo non isolato",
            ),
            keywords,
        )
    if _DISPOSITIVE_START_RE.search(text):
        return (
            ExtractedField(
                "altro",
                CONFIDENCE_LOW,
                _source(source_line) if source_line else "dispositivo non isolato",
            ),
            keywords,
        )
    return None, keywords


def _looks_like_judgment(
    lines: list[_Line],
    authority: ExtractedField | None,
    sentence_number: ExtractedField | None,
    decision_date: ExtractedField | None,
    outcome: ExtractedField | None,
) -> bool:
    text = "\n".join(line.text for line in lines).casefold()
    score = 0
    if authority is not None:
        score += 2
    if sentence_number is not None:
        score += 1
    if decision_date is not None:
        score += 1
    if outcome is not None:
        score += 1
    if "sentenza" in text:
        score += 1
    if any(_DISPOSITIVE_START_RE.search(line.text) for line in lines):
        score += 1
    return score >= 3


def _missing_fields(
    *,
    authority: ExtractedField | None,
    composition: ExtractedField | None,
    judge: ExtractedField | None,
    sentence_number: ExtractedField | None,
    proceeding_number: ExtractedField | None,
    hearing_or_decision_date: ExtractedField | None,
    motivation_type: ExtractedField | None,
    motivation_deadline: ExtractedField | None,
    deposit_date: ExtractedField | None,
    outcome: ExtractedField | None,
) -> list[str]:
    missing: list[str] = []
    required = [
        ("autorità giudiziaria", authority),
        ("composizione", composition),
        ("giudice", judge),
        ("numero sentenza", sentence_number),
        ("numero procedimento", proceeding_number),
        ("udienza / dispositivo", hearing_or_decision_date),
        ("deposito", deposit_date),
        ("dispositivo", outcome),
    ]
    for label, field in required:
        if field is None or field.value == "non rilevata":
            missing.append(label)
    if motivation_type is None or motivation_type.value == "non rilevata":
        missing.append("motivazione")
    elif motivation_type.value == "riservata" and motivation_deadline is None:
        missing.append("termine motivazione")
    return missing


def _warnings(
    motivation_type: ExtractedField | None,
    motivation_deadline: ExtractedField | None,
    deposit_date: ExtractedField | None,
    outcome: ExtractedField | None,
) -> list[str]:
    warnings = [
        "Parser euristico: non calcola termini di impugnazione e non sostituisce "
        "la verifica legale.",
    ]
    if deposit_date is None:
        warnings.append(
            "Data di deposito assente: verificare fascicolo e cancelleria prima "
            "di valutare scadenze.",
        )
    if (
        motivation_type is not None
        and motivation_type.value == "riservata"
        and motivation_deadline is None
    ):
        warnings.append(
            "Motivazione riservata senza termine rilevato: dato da controllare "
            "sul provvedimento originale.",
        )
    if outcome is not None and outcome.value == "ambiguo":
        warnings.append(
            "Dispositivo con indicatori contrastanti o multipli: classificazione "
            "da verificare manualmente.",
        )
    return warnings


def _dispositive_lines(lines: list[_Line]) -> list[_Line]:
    start = None
    for index, line in enumerate(lines):
        if _DISPOSITIVE_START_RE.search(line.text):
            start = index
            break
    if start is None:
        return []
    selected: list[_Line] = []
    for line in lines[start:start + 35]:
        if selected and re.match(r"^#{1,6}\s+\S+", line.text):
            break
        selected.append(line)
    return selected


def _keywords(pattern: re.Pattern[str], text: str) -> list[str]:
    return [_clean_value(match.group(0).lower()) for match in pattern.finditer(text)]


def _dedupe(values: object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value)
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _first_line_matching(
    lines: list[_Line],
    pattern: re.Pattern[str],
) -> _Line | None:
    for line in lines:
        if pattern.search(line.text):
            return line
    return None


def _clean_line(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return _SPACE_RE.sub(" ", text).strip()


def _clean_value(text: str) -> str:
    text = _SPACE_RE.sub(" ", text).strip(" \t-–—:;,.")
    return text


def _source(line: _Line) -> str:
    where = f"riga {line.number}"
    if line.page is not None:
        where = f"pagina {line.page}, {where}"
    return f"{where}: {_snippet(line.text)}"


def _snippet(text: str) -> str:
    text = _clean_value(text)
    if len(text) <= SNIPPET_MAX_LENGTH:
        return text
    return text[:SNIPPET_MAX_LENGTH - 1].rstrip() + "…"


def _field_value(field: ExtractedField | None) -> str:
    if field is None:
        return "non rilevato"
    if field.confidence == CONFIDENCE_HIGH:
        return field.value
    return f"{field.value} ({field.confidence})"


def _manifest_field(field: ExtractedField | None) -> dict[str, str | None]:
    if field is None:
        return {
            "value": None,
            "confidence": CONFIDENCE_LOW,
        }
    return {
        "value": _manifest_short_text(field.value, MANIFEST_VALUE_MAX_LENGTH),
        "confidence": field.confidence,
    }


def _manifest_path(path: str | Path) -> str:
    if isinstance(path, Path):
        return path.as_posix()
    return str(path)


def _manifest_short_text(value: str, max_length: int) -> str | None:
    text = _clean_value(value)
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return text[:max_length - 3].rstrip() + "..."


def _manifest_keyword(value: str) -> str | None:
    text = _clean_value(value).casefold()
    if not text:
        return None
    if "condann" in text:
        return "condanna"
    if "colpevole" in text:
        return "colpevole"
    if "assolv" in text:
        return "assoluzione"
    if "fatto non sussiste" in text:
        return "fatto non sussiste"
    if "non costituisce reato" in text:
        return "non costituisce reato"
    if "non aver commesso il fatto" in text:
        return "non aver commesso il fatto"
    if "non" in text and "previsto" in text and "legge" in text:
        return "fatto non previsto dalla legge come reato"
    if "prosciogl" in text:
        return "proscioglimento"
    if "non doversi procedere" in text:
        return "non doversi procedere"
    if "estinzione" in text and "reato" in text:
        return "estinzione reato"
    if "estinto" in text and "reato" in text:
        return "estinzione reato"
    if "prescrizione" in text:
        return "prescrizione"
    if "remissione" in text and "querela" in text:
        return "remissione querela"
    if "difetto" in text and "querela" in text:
        return "difetto di querela"
    if "patteggiamento" in text:
        return "patteggiamento"
    if "pena concordata" in text or "pena su richiesta" in text:
        return "patteggiamento"
    if "art" in text and "444" in text:
        return "patteggiamento"
    return _manifest_short_text(text, 40)
