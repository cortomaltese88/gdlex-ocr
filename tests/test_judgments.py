"""Synthetic offline tests for judgment Markdown metadata extraction."""

from __future__ import annotations

import unittest

from gdlex_ocr.judgments import (
    extract_judgment_metadata,
    format_judgment_summary,
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


if __name__ == "__main__":
    unittest.main()
