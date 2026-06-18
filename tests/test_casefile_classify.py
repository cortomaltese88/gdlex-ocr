"""Offline tests for filename-only case-file document classification."""

from __future__ import annotations

import unittest

from gdlex_ocr.casefile import DocumentType
from gdlex_ocr.casefile_classify import classify_by_filename


class CaseFileClassifyTest(unittest.TestCase):
    def test_classifies_required_mvp_patterns(self) -> None:
        cases = (
            ("001_sentenza.pdf", DocumentType.SENTENZA, "high"),
            ("02 - ordinanza.pdf", DocumentType.ORDINANZA, "high"),
            ("decreto fissazione udienza.pdf", DocumentType.DECRETO, "high"),
            (
                "verbale_udienza_12-5-2026.pdf",
                DocumentType.VERBALE_UDIENZA,
                "high",
            ),
            ("memoria difensiva.pdf", DocumentType.MEMORIA, "medium"),
            ("istanza rinvio.pdf", DocumentType.ISTANZA, "medium"),
            ("documento generico.pdf", DocumentType.SCONOSCIUTO, "low"),
            ("SENTENZA.PDF", DocumentType.SENTENZA, "high"),
            (
                "cartella/spazi e accenti/memòria difensìva.pdf",
                DocumentType.MEMORIA,
                "medium",
            ),
        )

        for filename, expected_type, expected_confidence in cases:
            with self.subTest(filename=filename):
                document_type, confidence, source = classify_by_filename(filename)

                self.assertEqual(expected_type, document_type)
                self.assertEqual(expected_confidence, confidence)
                self.assertEqual("filename", source)

    def test_allegato_is_low_or_medium_confidence(self) -> None:
        document_type, confidence, source = classify_by_filename("allegato 1.pdf")

        self.assertEqual(DocumentType.ALLEGATO, document_type)
        self.assertIn(confidence, {"low", "medium"})
        self.assertEqual("filename", source)

    def test_abbreviations_accept_dot_underscore_and_dash(self) -> None:
        cases = (
            ("sent. primo grado.pdf", DocumentType.SENTENZA, "high"),
            ("sent_2026.pdf", DocumentType.SENTENZA, "high"),
            ("sent-2026.pdf", DocumentType.SENTENZA, "high"),
            ("ord. cautelare.pdf", DocumentType.ORDINANZA, "high"),
            ("ord_2026.pdf", DocumentType.ORDINANZA, "high"),
            ("decr. fissazione.pdf", DocumentType.DECRETO, "high"),
            ("decr_2026.pdf", DocumentType.DECRETO, "high"),
            ("all. 1.pdf", DocumentType.ALLEGATO, "low"),
            ("all_2.pdf", DocumentType.ALLEGATO, "low"),
        )

        for filename, expected_type, expected_confidence in cases:
            with self.subTest(filename=filename):
                document_type, confidence, source = classify_by_filename(filename)

                self.assertEqual(expected_type, document_type)
                self.assertEqual(expected_confidence, confidence)
                self.assertEqual("filename", source)

    def test_udienza_alone_is_medium_verbale_udienza(self) -> None:
        document_type, confidence, source = classify_by_filename(
            "rinvio udienza.pdf"
        )

        self.assertEqual(DocumentType.VERBALE_UDIENZA, document_type)
        self.assertEqual("medium", confidence)
        self.assertEqual("filename", source)

    def test_note_and_richiesta_patterns(self) -> None:
        cases = (
            ("note difensive.pdf", DocumentType.MEMORIA, "medium"),
            ("note autorizzate.pdf", DocumentType.MEMORIA, "medium"),
            ("richiesta copie.pdf", DocumentType.ISTANZA, "medium"),
        )

        for filename, expected_type, expected_confidence in cases:
            with self.subTest(filename=filename):
                document_type, confidence, source = classify_by_filename(filename)

                self.assertEqual(expected_type, document_type)
                self.assertEqual(expected_confidence, confidence)
                self.assertEqual("filename", source)


if __name__ == "__main__":
    unittest.main()
