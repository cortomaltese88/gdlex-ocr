"""Deterministic, offline act-type classification for PDP/TIAP documentary units."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_SEPARATORS_RE = re.compile(r"[^a-z0-9àèéìòù']+")

CATEGORY_LABELS: dict[str, str] = {
    "certificato": "Certificato",
    "informativa": "Informativa",
    "nomina_difensore": "Nomina difensore",
    "verbale": "Verbale",
    "notifica": "Notifica/Avviso",
    "annotazione": "Annotazione",
    "sit_sommarie_informazioni": "Sommarie informazioni",
    "delega_indagini": "Delega indagini",
    "comunicazione": "Comunicazione",
    "provvedimento_pm": "Provvedimento PM",
    "provvedimento_gip_gup": "Provvedimento GIP/GUP",
    "elezione_domicilio": "Elezione domicilio",
    "querela_denuncia": "Querela/Denuncia",
    "relazione_servizio": "Relazione di servizio",
    "documentazione_sanitaria": "Documentazione sanitaria",
    "documentazione_amministrativa": "Documentazione amministrativa",
    "altro": "Altro",
}


@dataclass(frozen=True, slots=True)
class ActClassification:
    category: str
    confidence: str
    reason: str


def classify_act_metadata(
    title: str | None,
    description: str | None,
) -> ActClassification:
    """Classify a PDP/TIAP act based on title and description text.

    Returns an ActClassification with category, confidence, and reason.
    Classification is deterministic, offline, and based on keyword rules.
    """
    norm_title = _normalize(title)
    norm_desc = _normalize(description)
    combined = f"{norm_title} {norm_desc}".strip()

    if not combined:
        return ActClassification("altro", "low", "fallback")

    for rule in _RULES:
        result = rule(norm_title, norm_desc, combined)
        if result is not None:
            return result

    return ActClassification("altro", "low", "fallback")


def _normalize(text: str | None) -> str:
    if not text or not text.strip():
        return ""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return _SEPARATORS_RE.sub(" ", without_accents).strip()


def _phrase(haystack: str, phrase: str) -> bool:
    return f" {phrase} " in f" {haystack} "


def _any_phrase(haystack: str, phrases: tuple[str, ...]) -> bool:
    return any(_phrase(haystack, p) for p in phrases)


def _word(haystack: str, w: str) -> bool:
    return _phrase(haystack, w)


def _rule_certificato(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "certificato penale",
        "certificato carichi pendenti",
        "certificato carico pendente",
        "certificato casellario",
        "certificato anagrafico",
        "certificato di residenza",
        "certificato medico",
    )):
        return ActClassification("certificato", "high", "matched certificato specifico")
    if _word(combined, "certificato"):
        return ActClassification("certificato", "medium", "matched certificato")
    return None


def _rule_elezione_domicilio(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "elezione di domicilio",
        "elezione domicilio",
        "dichiarazione di domicilio",
        "dichiarazione domicilio",
    )):
        return ActClassification("elezione_domicilio", "high", "matched elezione domicilio")
    return None


def _rule_nomina_difensore(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "nomina difensore",
        "nomina del difensore",
        "difensore d'ufficio",
        "difensore d ufficio",
        "nomina avvocato",
        "designazione difensore",
    )):
        return ActClassification("nomina_difensore", "high", "matched nomina difensore")
    return None


def _rule_sit(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "sommarie informazioni",
        "s i t",
        "persona informata sui fatti",
        "persona informata",
        "sommarie informazioni testimoniali",
    )):
        return ActClassification(
            "sit_sommarie_informazioni", "high", "matched sommarie informazioni",
        )
    if _phrase(combined, "sit"):
        return ActClassification(
            "sit_sommarie_informazioni", "medium", "matched sit",
        )
    return None


def _rule_querela_denuncia(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "querela",
        "denuncia querela",
        "denuncia",
        "esposto",
    )):
        return ActClassification("querela_denuncia", "high", "matched querela/denuncia")
    return None


def _rule_informativa(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "informativa di reato",
        "informativa",
        "cnr",
        "comunicazione notizia di reato",
    )):
        return ActClassification("informativa", "high", "matched informativa")
    return None


def _rule_delega(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "delega indagini",
        "delega di indagini",
        "delega alle indagini",
        "delega",
    )):
        return ActClassification("delega_indagini", "high", "matched delega indagini")
    return None


def _rule_annotazione(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _word(combined, "annotazione") or _word(combined, "annotazioni"):
        return ActClassification("annotazione", "high", "matched annotazione")
    return None


def _rule_comunicazione(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "comunicazione 415 bis",
        "avviso 415 bis",
        "avviso di conclusione",
        "avviso conclusione indagini",
    )):
        return ActClassification("comunicazione", "high", "matched comunicazione 415bis")
    if _any_phrase(combined, (
        "trasmissione atti",
        "trasmissione degli atti",
    )):
        return ActClassification("comunicazione", "medium", "matched trasmissione atti")
    if _word(combined, "comunicazione"):
        return ActClassification("comunicazione", "medium", "matched comunicazione")
    return None


def _rule_notifica(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "notifica",
        "notificazione",
        "avviso di garanzia",
        "avviso",
    )):
        return ActClassification("notifica", "high", "matched notifica/avviso")
    return None


def _rule_verbale(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "verbale di arresto",
        "verbale di sequestro",
        "verbale di perquisizione",
        "verbale di ispezione",
        "verbale di conferimento",
        "verbale di ricognizione",
        "verbale di consegna",
        "verbale di ricezione",
        "verbale di identificazione",
        "verbale di elezione",
        "verbale di udienza",
        "verbale udienza",
    )):
        return ActClassification("verbale", "high", "matched verbale specifico")
    if _word(combined, "verbale"):
        return ActClassification("verbale", "high", "matched verbale")
    return None


def _rule_provvedimento_gip_gup(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    gip_gup = _any_phrase(combined, ("gip", "gup", "giudice", "g i p", "g u p"))
    if gip_gup and _any_phrase(combined, (
        "decreto",
        "ordinanza",
        "provvedimento",
        "convalida",
        "misura cautelare",
        "misura",
        "ammissione",
    )):
        return ActClassification(
            "provvedimento_gip_gup", "high", "matched provvedimento gip/gup",
        )
    if _any_phrase(combined, (
        "decreto gip",
        "decreto gup",
        "ordinanza gip",
        "ordinanza gup",
        "ordinanza del g i p",
        "ordinanza del g u p",
        "convalida",
        "incidente probatorio",
    )):
        return ActClassification(
            "provvedimento_gip_gup", "high", "matched provvedimento gip/gup",
        )
    return None


def _rule_provvedimento_pm(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "decreto di sequestro",
        "decreto sequestro",
        "decreto di perquisizione",
        "decreto perquisizione",
        "decreto di iscrizione",
        "iscrizione",
        "decreto di archiviazione",
        "richiesta di archiviazione",
        "richiesta di rinvio a giudizio",
        "decreto di ispezione",
        "decreto acquisizione",
        "decreto di effettuazione",
        "dissequestro",
    )):
        return ActClassification("provvedimento_pm", "high", "matched provvedimento pm")
    pm = _any_phrase(combined, (
        "pm", "p m", "pubblico ministero", "procura",
    ))
    if pm and _any_phrase(combined, (
        "decreto", "provvedimento", "ordine", "richiesta",
    )):
        return ActClassification(
            "provvedimento_pm", "medium", "matched provvedimento pm",
        )
    return None


def _rule_relazione_servizio(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "relazione di servizio",
        "relazione servizio",
    )):
        return ActClassification(
            "relazione_servizio", "high", "matched relazione di servizio",
        )
    return None


def _rule_documentazione_sanitaria(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "documentazione sanitaria",
        "referto",
        "referto medico",
        "cartella clinica",
        "certificato medico",
        "pronto soccorso",
        "perizia medico legale",
    )):
        return ActClassification(
            "documentazione_sanitaria", "high",
            "matched documentazione sanitaria",
        )
    return None


def _rule_documentazione_amministrativa(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "documentazione amministrativa",
        "visura camerale",
        "visura catastale",
        "documentazione",
    )):
        return ActClassification(
            "documentazione_amministrativa", "medium",
            "matched documentazione amministrativa",
        )
    return None


def _rule_seguito_indagine(
    title: str, desc: str, combined: str,
) -> ActClassification | None:
    if _any_phrase(combined, (
        "seguito d indagine",
        "seguito d'indagine",
        "seguito indagine",
        "seguito di indagine",
        "atti di indagine",
    )):
        return ActClassification("informativa", "medium", "matched seguito indagine")
    return None


_RULES: tuple[
    ...,
] = (
    _rule_certificato,
    _rule_elezione_domicilio,
    _rule_nomina_difensore,
    _rule_sit,
    _rule_querela_denuncia,
    _rule_informativa,
    _rule_seguito_indagine,
    _rule_delega,
    _rule_annotazione,
    _rule_comunicazione,
    _rule_notifica,
    _rule_verbale,
    _rule_provvedimento_gip_gup,
    _rule_provvedimento_pm,
    _rule_relazione_servizio,
    _rule_documentazione_sanitaria,
    _rule_documentazione_amministrativa,
)
