"""Synthetic offline tests for judgment Markdown metadata extraction."""

from __future__ import annotations

import json
import unittest

from gdlex_ocr.judgments import (
    extract_judgment_metadata,
    format_judgment_summary,
    judgment_analysis_to_manifest_dict,
    prepend_judgment_summary,
)


TRIBUNALE_PADOVA_CONDANNA = """\
# Sentenza sintetica

## Blocco 1 - Pagine 1-2

TRIBUNALE DI PADOVA
Sezione penale - in composizione monocratica
Sentenza n. 123/2026
R.G. n. 456/2025

Il Giudice dott.ssa Maria Rossi ha pronunciato la seguente sentenza.
All'udienza del 18 giugno 2026 viene letto il dispositivo.

P.Q.M.
Dichiara l'imputato colpevole e lo condanna alla pena di mesi sei.
Motivazione riservata nel termine di 90 giorni.

Depositata in cancelleria il 20 giugno 2026.
"""

GIUDICE_PACE_VENEZIA_ASSOLUZIONE = """\
GIUDICE DI PACE DI VENEZIA

Sentenza n. 77/2026
Procedimento n. 88/2026

All'udienza del 10 maggio 2026 il Giudice dott. Luca Bianchi pronuncia
dispositivo e motivazione contestuale.

P.Q.M.
Assolve l'imputata perche' il fatto non sussiste.

Depositata il 10 maggio 2026.
"""

TRIBUNALE_TREVISO_AMBIGUO = """\
TRIBUNALE DI TREVISO
in composizione collegiale
Sentenza numero 41/2026
R.G.N.R. 222/2025

Il Collegio, all'udienza del 9 aprile 2026, pronuncia dispositivo.

P.Q.M.
Assolve Tizio dal capo A.
Condanna Tizio per il capo B.
Motivazione contestuale.
Depositata in cancelleria il 9 aprile 2026.
"""

CORTE_ASSISE_MILANO_NO_DEPOSIT = """\
CORTE DI ASSISE DI MILANO
Sentenza n. 9/2026
R.G. n. 10/2024

All'udienza del 3 marzo 2026 la Corte pronuncia il dispositivo.

P.Q.M.
Condanna l'imputato alla pena indicata in dispositivo.
Motivazione riservata in 60 giorni.
"""

TRIBUNALE_ORDINARIO_PADOVA = """\
TRIBUNALE ORDINARIO DI PADOVA
Sezione penale
Sentenza n. 201/2026
R.G. n. 300/2025

All'udienza del 10 giugno 2026
P.Q.M.
Condanna l'imputato alla pena di mesi tre.
Motivazione riservata in giorni novanta.
Depositata il 12 giugno 2026.
"""

CORTE_ASSISE_APPELLO_CONDANNA = """\
CORTE DI ASSISE D'APPELLO DI MILANO
Sentenza n. 7/2026
R.G. n. 15/2025

All'udienza del 5 marzo 2026
P.Q.M.
Condanna l'imputato.
Motivazione riservata nel termine di 90 giorni.
"""

CORTE_ASSISE_APPELLO_DI_FORM = """\
CORTE DI ASSISE DI APPELLO DI MILANO
Sentenza n. 7/2026

All'udienza del 5 marzo 2026
P.Q.M.
Condanna l'imputato.
"""

PRESCRIZIONE_OUTCOME = """\
TRIBUNALE DI PADOVA
Sentenza n. 88/2026

All'udienza del 5 maggio 2026
P.Q.M.
Dichiara estinto il reato per intervenuta prescrizione.
"""

ASSOLUZIONE_NON_AVER_COMMESSO = """\
TRIBUNALE DI PADOVA
Sentenza n. 70/2026

All'udienza del 5 maggio 2026
P.Q.M.
Assolve l'imputato per non aver commesso il fatto.
"""

FATTO_NON_PREVISTO = """\
TRIBUNALE DI PADOVA
Sentenza n. 71/2026

All'udienza del 5 maggio 2026
P.Q.M.
Assolve l'imputato perche' il fatto non e' previsto dalla legge come reato.
"""

OVERCAPTURE_AUTHORITY = """\
Il Tribunale di Padova ha emesso la seguente sentenza.
Sentenza n. 50/2026
All'udienza del 1 giugno 2026
P.Q.M.
Condanna l'imputato.
"""

PATTEGGIAMENTO_FIXTURE = """\
TRIBUNALE DI PADOVA
Sentenza n. 99/2026

All'udienza del 5 maggio 2026
P.Q.M.
Applica la pena concordata di mesi quattro ex art. 444 c.p.p.
"""

REMISSIONE_QUERELA_FIXTURE = """\
TRIBUNALE DI PADOVA
Sentenza n. 33/2026

All'udienza del 5 maggio 2026
P.Q.M.
Dichiara non doversi procedere per intervenuta remissione della querela.
"""

DEADLINE_SPELLED_OUT = """\
TRIBUNALE DI PADOVA
Sentenza n. 40/2026

All'udienza del 1 giugno 2026
P.Q.M.
Condanna l'imputato.
Motivazione riservata in giorni novanta.
"""

ESTINTO_IL_REATO_FIXTURE = """\
TRIBUNALE DI PADOVA
Sentenza n. 89/2026

All'udienza del 5 maggio 2026
P.Q.M.
Dichiara estinto il reato.
"""

NOT_A_JUDGMENT = """\
# Appunti riunione

Promemoria interno su attivita' amministrative.
Non contiene un dispositivo e non contiene dati di una sentenza.
"""


class JudgmentExtractionTest(unittest.TestCase):
    def test_tribunale_condanna_with_reserved_motivation(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_PADOVA_CONDANNA)

        self.assertTrue(analysis.detected)
        self.assertEqual("TRIBUNALE DI PADOVA", analysis.authority.value)
        self.assertEqual("monocratica", analysis.composition.value)
        self.assertEqual("Maria Rossi", analysis.judge.value)
        self.assertEqual("123/2026", analysis.sentence_number.value)
        self.assertEqual("456/2025", analysis.proceeding_number.value)
        self.assertEqual("18 giugno 2026", analysis.hearing_or_decision_date.value)
        self.assertEqual("riservata", analysis.motivation_type.value)
        self.assertEqual("90 giorni", analysis.motivation_deadline.value)
        self.assertEqual("20 giugno 2026", analysis.deposit_date.value)
        self.assertEqual("condanna", analysis.outcome.value)
        self.assertNotIn("deposito", analysis.missing_fields)

    def test_giudice_di_pace_assoluzione(self) -> None:
        analysis = extract_judgment_metadata(GIUDICE_PACE_VENEZIA_ASSOLUZIONE)

        self.assertTrue(analysis.detected)
        self.assertEqual("GIUDICE DI PACE DI VENEZIA", analysis.authority.value)
        self.assertEqual("Giudice di Pace", analysis.composition.value)
        self.assertEqual("10 maggio 2026", analysis.hearing_or_decision_date.value)
        self.assertEqual("contestuale", analysis.motivation_type.value)
        self.assertEqual("10 maggio 2026", analysis.deposit_date.value)
        self.assertEqual("assoluzione", analysis.outcome.value)

    def test_collegial_tribunal_ambiguous_dispositive(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_TREVISO_AMBIGUO)

        self.assertTrue(analysis.detected)
        self.assertEqual("TRIBUNALE DI TREVISO", analysis.authority.value)
        self.assertEqual("collegiale", analysis.composition.value)
        self.assertEqual("9 aprile 2026", analysis.hearing_or_decision_date.value)
        self.assertEqual("ambiguo", analysis.outcome.value)
        self.assertIn("assolve", analysis.dispositive_keywords)
        self.assertIn("condanna", analysis.dispositive_keywords)

    def test_corte_assise_condanna_without_deposit(self) -> None:
        analysis = extract_judgment_metadata(CORTE_ASSISE_MILANO_NO_DEPOSIT)

        self.assertTrue(analysis.detected)
        self.assertEqual("CORTE DI ASSISE DI MILANO", analysis.authority.value)
        self.assertEqual("Corte d'Assise", analysis.composition.value)
        self.assertEqual("3 marzo 2026", analysis.hearing_or_decision_date.value)
        self.assertEqual("riservata", analysis.motivation_type.value)
        self.assertEqual("60 giorni", analysis.motivation_deadline.value)
        self.assertIsNone(analysis.deposit_date)
        self.assertIn("deposito", analysis.missing_fields)
        self.assertEqual("condanna", analysis.outcome.value)

    def test_non_judgment_is_not_detected(self) -> None:
        analysis = extract_judgment_metadata(NOT_A_JUDGMENT)

        self.assertFalse(analysis.detected)
        self.assertIsNone(analysis.authority)
        self.assertIsNone(analysis.outcome)

    def test_tribunale_ordinario_authority(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_ORDINARIO_PADOVA)

        self.assertTrue(analysis.detected)
        self.assertIsNotNone(analysis.authority)
        self.assertIn("PADOVA", analysis.authority.value.upper())
        self.assertEqual("high", analysis.authority.confidence)
        self.assertEqual("condanna", analysis.outcome.value)

    def test_corte_assise_appello_authority(self) -> None:
        analysis = extract_judgment_metadata(CORTE_ASSISE_APPELLO_CONDANNA)

        self.assertTrue(analysis.detected)
        self.assertIsNotNone(analysis.authority)
        self.assertIn("APPELLO", analysis.authority.value.upper())
        self.assertIn("ASSISE", analysis.authority.value.upper())
        self.assertEqual("condanna", analysis.outcome.value)

    def test_corte_assise_appello_di_form(self) -> None:
        analysis = extract_judgment_metadata(CORTE_ASSISE_APPELLO_DI_FORM)

        self.assertTrue(analysis.detected)
        self.assertIsNotNone(analysis.authority)
        self.assertIn("APPELLO", analysis.authority.value.upper())

    def test_prescrizione_outcome(self) -> None:
        analysis = extract_judgment_metadata(PRESCRIZIONE_OUTCOME)

        self.assertTrue(analysis.detected)
        self.assertEqual(
            "proscioglimento / non doversi procedere",
            analysis.outcome.value,
        )
        self.assertTrue(
            any("prescrizione" in kw for kw in analysis.dispositive_keywords)
        )

    def test_estinto_il_reato_outcome(self) -> None:
        analysis = extract_judgment_metadata(ESTINTO_IL_REATO_FIXTURE)

        self.assertTrue(analysis.detected)
        self.assertEqual(
            "proscioglimento / non doversi procedere",
            analysis.outcome.value,
        )

    def test_assoluzione_per_non_aver_commesso_il_fatto(self) -> None:
        analysis = extract_judgment_metadata(ASSOLUZIONE_NON_AVER_COMMESSO)

        self.assertTrue(analysis.detected)
        self.assertEqual("assoluzione", analysis.outcome.value)
        self.assertTrue(
            any("non aver commesso" in kw for kw in analysis.dispositive_keywords)
            or "assolve" in analysis.dispositive_keywords
        )

    def test_fatto_non_previsto_dalla_legge_come_reato(self) -> None:
        analysis = extract_judgment_metadata(FATTO_NON_PREVISTO)

        self.assertTrue(analysis.detected)
        self.assertEqual("assoluzione", analysis.outcome.value)

    def test_authority_overcapture_on_sentence_line(self) -> None:
        analysis = extract_judgment_metadata(OVERCAPTURE_AUTHORITY)

        self.assertTrue(analysis.detected)
        self.assertIsNotNone(analysis.authority)
        self.assertIn("Padova", analysis.authority.value)
        self.assertNotIn("emesso", analysis.authority.value)
        self.assertNotIn("seguente", analysis.authority.value)
        self.assertNotIn("sentenza", analysis.authority.value.lower())

    def test_patteggiamento_keyword_or_outcome(self) -> None:
        analysis = extract_judgment_metadata(PATTEGGIAMENTO_FIXTURE)

        self.assertTrue(analysis.detected)
        self.assertEqual("patteggiamento", analysis.outcome.value)

    def test_remissione_querela_outcome(self) -> None:
        analysis = extract_judgment_metadata(REMISSIONE_QUERELA_FIXTURE)

        self.assertTrue(analysis.detected)
        self.assertEqual(
            "proscioglimento / non doversi procedere",
            analysis.outcome.value,
        )
        self.assertTrue(
            any("remissione" in kw for kw in analysis.dispositive_keywords)
        )

    def test_deadline_spelled_out_number(self) -> None:
        analysis = extract_judgment_metadata(DEADLINE_SPELLED_OUT)

        self.assertTrue(analysis.detected)
        self.assertIsNotNone(analysis.motivation_deadline)
        self.assertEqual("90 giorni", analysis.motivation_deadline.value)
        self.assertEqual("riservata", analysis.motivation_type.value)

    def test_tribunale_ordinario_deadline_novanta(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_ORDINARIO_PADOVA)

        self.assertEqual("90 giorni", analysis.motivation_deadline.value)


class JudgmentSummaryTest(unittest.TestCase):
    def test_summary_contains_expected_sections(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_PADOVA_CONDANNA)

        summary = format_judgment_summary(analysis)

        self.assertIn("# Scheda sentenza", summary)
        self.assertIn("## Dati provvedimento", summary)
        self.assertIn("## Date rilevanti", summary)
        self.assertIn("## Esito", summary)
        self.assertIn("## Alert impugnazione", summary)
        self.assertIn("- Dispositivo: condanna", summary)
        self.assertIn("- Termine motivazione: 90 giorni", summary)

    def test_prepend_inserts_summary_before_original_markdown(self) -> None:
        analysis = extract_judgment_metadata(GIUDICE_PACE_VENEZIA_ASSOLUZIONE)

        merged = prepend_judgment_summary(
            GIUDICE_PACE_VENEZIA_ASSOLUZIONE,
            analysis,
        )

        self.assertTrue(merged.startswith("# Scheda sentenza"))
        self.assertIn("\n---\n\nGIUDICE DI PACE DI VENEZIA", merged)
        self.assertTrue(merged.endswith(GIUDICE_PACE_VENEZIA_ASSOLUZIONE))


class JudgmentManifestTest(unittest.TestCase):
    def test_manifest_dict_contains_privacy_safe_analysis(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_PADOVA_CONDANNA)

        manifest = judgment_analysis_to_manifest_dict(
            analysis,
            "sentenza_analysis.md",
        )

        self.assertTrue(manifest["enabled"])
        self.assertTrue(manifest["detected"])
        self.assertEqual("sentenza_analysis.md", manifest["output_file"])
        fields = manifest["fields"]
        for name in (
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
        ):
            with self.subTest(name=name):
                self.assertIn("value", fields[name])
                self.assertIn("confidence", fields[name])
        self.assertEqual("TRIBUNALE DI PADOVA", fields["authority"]["value"])
        self.assertEqual("high", fields["authority"]["confidence"])
        self.assertEqual("condanna", fields["outcome"]["value"])
        self.assertIn("condanna", manifest["dispositive_keywords"])
        self.assertIn("colpevole", manifest["dispositive_keywords"])
        self.assertIn("warnings", manifest)
        serialized = str(manifest)
        self.assertNotIn("source", serialized)
        self.assertNotIn("Dichiara l'imputato colpevole", serialized)
        self.assertNotIn("alla pena di mesi sei", serialized)

    def test_manifest_dict_for_non_judgment_has_disabled_content_fields(self) -> None:
        analysis = extract_judgment_metadata(NOT_A_JUDGMENT)

        manifest = judgment_analysis_to_manifest_dict(
            analysis,
            "sentenza_analysis.md",
        )

        self.assertTrue(manifest["enabled"])
        self.assertFalse(manifest["detected"])
        self.assertIsNone(manifest["fields"]["authority"]["value"])
        self.assertEqual("low", manifest["fields"]["authority"]["confidence"])
        self.assertEqual([], manifest["dispositive_keywords"])
        self.assertIn("Testo non riconosciuto", " ".join(manifest["warnings"]))

    def test_manifest_no_source_prefixes_in_json(self) -> None:
        analysis = extract_judgment_metadata(TRIBUNALE_PADOVA_CONDANNA)

        manifest = judgment_analysis_to_manifest_dict(
            analysis,
            "sentenza_analysis.md",
        )
        serialized = json.dumps(manifest, ensure_ascii=False)

        self.assertNotIn("riga ", serialized)
        self.assertNotIn("pagina ", serialized)
        self.assertNotIn("Dichiara l'imputato colpevole", serialized)
        self.assertNotIn("alla pena di mesi sei", serialized)
        self.assertNotIn("ha pronunciato la seguente", serialized)

    def test_manifest_patteggiamento_keywords_normalized(self) -> None:
        analysis = extract_judgment_metadata(PATTEGGIAMENTO_FIXTURE)

        manifest = judgment_analysis_to_manifest_dict(
            analysis,
            "sentenza_analysis.md",
        )

        self.assertIn("patteggiamento", manifest["dispositive_keywords"])
        serialized = json.dumps(manifest, ensure_ascii=False)
        self.assertNotIn("Applica la pena concordata", serialized)

    def test_manifest_prescrizione_keywords_normalized(self) -> None:
        analysis = extract_judgment_metadata(PRESCRIZIONE_OUTCOME)

        manifest = judgment_analysis_to_manifest_dict(
            analysis,
            "sentenza_analysis.md",
        )

        self.assertIn("prescrizione", manifest["dispositive_keywords"])


if __name__ == "__main__":
    unittest.main()
