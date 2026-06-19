"""Tests for deterministic PDP/TIAP act-type classification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    format_casefile_analysis_markdown,
    format_casefile_units_csv,
)
from gdlex_ocr.casefile_unit_classify import ActClassification, classify_act_metadata


class ClassifyActMetadataTest(unittest.TestCase):
    def test_certificato_penale(self) -> None:
        r = classify_act_metadata("CERTIFICATO PENALE", None)
        self.assertEqual("certificato", r.category)
        self.assertEqual("high", r.confidence)

    def test_certificato_carico_pendente(self) -> None:
        r = classify_act_metadata("CERTIFICATO CARICO PENDENTE", None)
        self.assertEqual("certificato", r.category)
        self.assertEqual("high", r.confidence)

    def test_certificato_carichi_pendenti(self) -> None:
        r = classify_act_metadata("CERTIFICATO CARICHI PENDENTI", None)
        self.assertEqual("certificato", r.category)
        self.assertEqual("high", r.confidence)

    def test_nomina_difensore(self) -> None:
        r = classify_act_metadata("NOMINA DIFENSORE", None)
        self.assertEqual("nomina_difensore", r.category)
        self.assertEqual("high", r.confidence)

    def test_difensore_d_ufficio(self) -> None:
        r = classify_act_metadata("DIFENSORE D'UFFICIO", None)
        self.assertEqual("nomina_difensore", r.category)
        self.assertEqual("high", r.confidence)

    def test_verbale(self) -> None:
        r = classify_act_metadata("VERBALE", None)
        self.assertEqual("verbale", r.category)
        self.assertEqual("high", r.confidence)

    def test_verbale_di_arresto(self) -> None:
        r = classify_act_metadata("VERBALE DI ARRESTO", None)
        self.assertEqual("verbale", r.category)
        self.assertEqual("high", r.confidence)

    def test_verbale_di_sequestro(self) -> None:
        r = classify_act_metadata("VERBALE DI SEQUESTRO", None)
        self.assertEqual("verbale", r.category)
        self.assertEqual("high", r.confidence)

    def test_sommarie_informazioni(self) -> None:
        r = classify_act_metadata("SOMMARIE INFORMAZIONI", None)
        self.assertEqual("sit_sommarie_informazioni", r.category)
        self.assertEqual("high", r.confidence)

    def test_sit_abbreviation(self) -> None:
        r = classify_act_metadata("S.I.T.", None)
        self.assertEqual("sit_sommarie_informazioni", r.category)

    def test_persona_informata_sui_fatti(self) -> None:
        r = classify_act_metadata("PERSONA INFORMATA SUI FATTI", None)
        self.assertEqual("sit_sommarie_informazioni", r.category)
        self.assertEqual("high", r.confidence)

    def test_annotazione(self) -> None:
        r = classify_act_metadata("ANNOTAZIONE", None)
        self.assertEqual("annotazione", r.category)
        self.assertEqual("high", r.confidence)

    def test_delega_indagini(self) -> None:
        r = classify_act_metadata("DELEGA INDAGINI", None)
        self.assertEqual("delega_indagini", r.category)
        self.assertEqual("high", r.confidence)

    def test_delega_alone(self) -> None:
        r = classify_act_metadata("DELEGA", None)
        self.assertEqual("delega_indagini", r.category)

    def test_querela(self) -> None:
        r = classify_act_metadata("QUERELA", None)
        self.assertEqual("querela_denuncia", r.category)
        self.assertEqual("high", r.confidence)

    def test_denuncia(self) -> None:
        r = classify_act_metadata("DENUNCIA", None)
        self.assertEqual("querela_denuncia", r.category)
        self.assertEqual("high", r.confidence)

    def test_informativa_di_reato(self) -> None:
        r = classify_act_metadata("INFORMATIVA DI REATO", None)
        self.assertEqual("informativa", r.category)
        self.assertEqual("high", r.confidence)

    def test_informativa_alone(self) -> None:
        r = classify_act_metadata("INFORMATIVA", None)
        self.assertEqual("informativa", r.category)

    def test_notifica(self) -> None:
        r = classify_act_metadata("NOTIFICA", None)
        self.assertEqual("notifica", r.category)
        self.assertEqual("high", r.confidence)

    def test_avviso(self) -> None:
        r = classify_act_metadata("AVVISO", None)
        self.assertEqual("notifica", r.category)

    def test_comunicazione_415bis(self) -> None:
        r = classify_act_metadata("COMUNICAZIONE 415 BIS", None)
        self.assertEqual("comunicazione", r.category)
        self.assertEqual("high", r.confidence)

    def test_comunicazione_alone(self) -> None:
        r = classify_act_metadata("COMUNICAZIONE", None)
        self.assertEqual("comunicazione", r.category)

    def test_elezione_domicilio(self) -> None:
        r = classify_act_metadata("ELEZIONE DI DOMICILIO", None)
        self.assertEqual("elezione_domicilio", r.category)
        self.assertEqual("high", r.confidence)

    def test_provvedimento_gip(self) -> None:
        r = classify_act_metadata("DECRETO GIP", None)
        self.assertEqual("provvedimento_gip_gup", r.category)
        self.assertEqual("high", r.confidence)

    def test_convalida(self) -> None:
        r = classify_act_metadata("CONVALIDA", None)
        self.assertEqual("provvedimento_gip_gup", r.category)

    def test_decreto_sequestro_pm(self) -> None:
        r = classify_act_metadata("DECRETO DI SEQUESTRO", None)
        self.assertEqual("provvedimento_pm", r.category)
        self.assertEqual("high", r.confidence)

    def test_relazione_servizio(self) -> None:
        r = classify_act_metadata("RELAZIONE DI SERVIZIO", None)
        self.assertEqual("relazione_servizio", r.category)
        self.assertEqual("high", r.confidence)

    def test_documentazione_sanitaria_referto(self) -> None:
        r = classify_act_metadata("REFERTO", None)
        self.assertEqual("documentazione_sanitaria", r.category)
        self.assertEqual("high", r.confidence)

    def test_documentazione_amministrativa(self) -> None:
        r = classify_act_metadata("VISURA CAMERALE", None)
        self.assertEqual("documentazione_amministrativa", r.category)

    def test_unknown_title_is_altro(self) -> None:
        r = classify_act_metadata("SOMETHING UNKNOWN", None)
        self.assertEqual("altro", r.category)
        self.assertEqual("low", r.confidence)

    def test_none_title_is_altro(self) -> None:
        r = classify_act_metadata(None, None)
        self.assertEqual("altro", r.category)
        self.assertEqual("low", r.confidence)
        self.assertEqual("fallback", r.reason)

    def test_empty_title_is_altro(self) -> None:
        r = classify_act_metadata("", None)
        self.assertEqual("altro", r.category)
        self.assertEqual("low", r.confidence)

    def test_case_insensitive(self) -> None:
        r = classify_act_metadata("certificato penale", None)
        self.assertEqual("certificato", r.category)
        self.assertEqual("high", r.confidence)

    def test_accent_insensitive(self) -> None:
        r = classify_act_metadata("VERBALE DI PERQUISIZIONÉ", None)
        self.assertEqual("verbale", r.category)

    def test_mixed_case_and_accents(self) -> None:
        r = classify_act_metadata("Nomina Difensore d'Ufficio", None)
        self.assertEqual("nomina_difensore", r.category)

    def test_description_contributes_to_classification(self) -> None:
        r = classify_act_metadata("ALTRO", "TRASMISSIONE ATTI QUERELA")
        self.assertEqual("querela_denuncia", r.category)

    def test_seguito_indagine(self) -> None:
        r = classify_act_metadata("SEGUITO D'INDAGINE", None)
        self.assertEqual("informativa", r.category)

    def test_returns_act_classification_dataclass(self) -> None:
        r = classify_act_metadata("VERBALE", None)
        self.assertIsInstance(r, ActClassification)
        self.assertIsNotNone(r.reason)


class IntegrationClassificationTest(unittest.TestCase):
    """Test classification integrated into the full analysis pipeline."""

    _MINISTERIAL_HTML = (
        '<html><head><title>Documento : 021 - CERTIFICATO PENALE</title></head>'
        '<body><li><strong>Data</strong> : 08/11/2024</li></body></html>'
    )

    def _create_classified_fixture(self, root: Path) -> None:
        titles = {
            "100": "CERTIFICATO PENALE",
            "200": "VERBALE DI ARRESTO",
            "300": "NOMINA DIFENSORE",
        }
        for uid, title in titles.items():
            d = root / uid
            d.mkdir()
            (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic-" + uid.encode())
            (d / "COMPLETE").write_bytes(b"")
            (d / "ListaAllegati.html").write_text(
                f'<html><head><title>Documento : 001 - {title}</title></head>'
                f'<body><li><strong>Data</strong> : 01/01/2025</li></body></html>',
                encoding="utf-8",
            )

    def test_units_have_act_category_after_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)

            for unit in analysis.units:
                self.assertIsNotNone(unit.act_category)
                self.assertIsNotNone(unit.act_category_confidence)
                self.assertIsNotNone(unit.act_category_reason)

    def test_json_contains_category_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)

            for unit in payload["units"]:
                self.assertIn("act_category", unit)
                self.assertIn("act_category_confidence", unit)
                self.assertIn("act_category_reason", unit)
            json.dumps(payload, ensure_ascii=False)

    def test_json_unit_has_correct_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)

            cert_unit = next(
                u for u in payload["units"] if u["unit_id"] == "100"
            )
            self.assertEqual("certificato", cert_unit["act_category"])

    def test_markdown_has_categoria_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("Categoria", markdown)
            self.assertIn("Certificato", markdown)

    def test_markdown_has_categorie_atti_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Categorie atti", markdown)
            self.assertIn("Certificato", markdown)
            self.assertIn("Verbale", markdown)

    def test_units_csv_has_categoria_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            header = csv_text.strip().splitlines()[0]

            self.assertIn("Categoria", header)
            self.assertIn("Confidenza categoria", header)

    def test_units_csv_contains_category_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertIn("Certificato", csv_text)
            self.assertIn("Verbale", csv_text)

    def test_units_csv_no_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_classified_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertNotIn(str(root), csv_text)

    def test_unit_without_title_gets_altro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "999"
            d.mkdir()
            (d / "999.pdf").write_bytes(b"%PDF-synthetic")

            analysis = analyze_case_folder(root)
            unit = analysis.units[0]

            self.assertEqual("altro", unit.act_category)
            self.assertEqual("low", unit.act_category_confidence)


if __name__ == "__main__":
    unittest.main()
