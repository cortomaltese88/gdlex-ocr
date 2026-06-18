"""Offline tests for privacy-safe case-file export."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from gdlex_ocr.casefile import (
    CaseFileAnalysis,
    CaseFileDocument,
    CaseFileIndex,
    DocumentType,
    ExtractionWarning,
    analyze_case_folder,
)
from gdlex_ocr.casefile_export import casefile_analysis_to_dict
from gdlex_ocr.casefile_index import CaseFileIndexEntry, CaseFileIndexMatch
from gdlex_ocr.manifest import file_sha256


class CaseFileExportTest(unittest.TestCase):
    def test_casefile_analysis_to_dict_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            payload = casefile_analysis_to_dict(analysis)

            json.dumps(payload, ensure_ascii=False)

    def test_export_summary_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            summary = casefile_analysis_to_dict(analysis)["summary"]

            self.assertEqual(
                {
                    "total_files": 2,
                    "total_pdf_files": 1,
                    "total_non_pdf_files": 1,
                    "total_indexes": 1,
                    "total_index_entries": 1,
                    "total_index_matches": 1,
                    "total_warnings": 0,
                },
                summary,
            )

    def test_export_documents_include_hash_and_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "001_sentenza.pdf"
            pdf.write_bytes(b"synthetic pdf")

            payload = casefile_analysis_to_dict(analyze_case_folder(root))
            document = self._document_payload(payload, "001_sentenza.pdf")

            self.assertEqual(file_sha256(pdf), document["sha256"])
            self.assertEqual("sentenza", document["document_type"])
            self.assertIsInstance(document["document_type"], str)

    def test_export_indexes_include_entries_and_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            payload = casefile_analysis_to_dict(analysis)
            index = payload["indexes"][0]
            entry = index["entries"][0]
            match = entry["matches"][0]

            self.assertEqual("indice.html", index["relative_path"])
            self.assertEqual("atti/001_sentenza.pdf", entry["referenced_path"])
            self.assertEqual("atti/001_sentenza.pdf", match["matched_relative_path"])
            self.assertEqual("relative_path_exact", match["strategy"])

    def test_export_does_not_leak_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            absolute_markdown = str(root / "out" / "analysis.md")
            document = replace(
                analysis.documents[0],
                markdown_path=absolute_markdown,
            )
            analysis = replace(
                analysis,
                documents=(document, *analysis.documents[1:]),
                warnings=(
                    ExtractionWarning(
                        code="synthetic",
                        message=f"Errore su {absolute_markdown}",
                        path=absolute_markdown,
                    ),
                ),
            )

            serialized = json.dumps(
                casefile_analysis_to_dict(analysis),
                ensure_ascii=False,
            )

            self.assertNotIn(str(root), serialized)
            self.assertNotIn(str(root).replace("/", "\\/"), serialized)

    def test_export_truncates_long_labels_and_warnings(self) -> None:
        long_label = "Sentenza " * 40
        long_message = "Warning " * 60
        warning = ExtractionWarning(
            code="long_warning",
            message=long_message,
            path=None,
        )
        match = CaseFileIndexMatch(
            entry_row_number=1,
            document_id="doc-1",
            entry_reference="sentenza.pdf",
            matched_relative_path="sentenza.pdf",
            confidence="high",
            strategy="relative_path_exact",
            warnings=(warning,),
        )
        entry = CaseFileIndexEntry(
            row_number=1,
            label=long_label,
            referenced_path="sentenza.pdf",
            document_date=None,
            document_type_hint=None,
            confidence="high",
            source="test",
            warnings=(warning,),
            matches=(match,),
        )
        analysis = self._manual_analysis(
            indexes=(
                CaseFileIndex(
                    relative_path="indice.html",
                    extension=".html",
                    confidence="high",
                    source="test",
                    detected_format="html",
                    warnings=(warning,),
                    entries=(entry,),
                ),
            ),
            warnings=(warning,),
        )

        payload = casefile_analysis_to_dict(analysis)
        exported_warning = payload["warnings"][0]
        exported_entry = payload["indexes"][0]["entries"][0]
        exported_match_warning = exported_entry["matches"][0]["warnings"][0]

        self.assertLessEqual(len(exported_entry["label"]), 160)
        self.assertTrue(exported_entry["label"].endswith("..."))
        self.assertLessEqual(len(exported_warning["message"]), 240)
        self.assertTrue(exported_warning["message"].endswith("..."))
        self.assertLessEqual(len(exported_match_warning["message"]), 240)

    def test_export_duplicate_warning_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "001_original.pdf").write_bytes(b"same content")
            (root / "002_copy.pdf").write_bytes(b"same content")

            payload = casefile_analysis_to_dict(analyze_case_folder(root))

            self.assertIn(
                "duplicate_file",
                [warning["code"] for warning in payload["warnings"]],
            )
            copy_document = self._document_payload(payload, "002_copy.pdf")
            self.assertIn(
                "duplicate_file",
                [warning["code"] for warning in copy_document["warnings"]],
            )

    def test_export_unknown_type_as_string(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "documento.pdf").write_bytes(b"synthetic pdf")

            payload = casefile_analysis_to_dict(analyze_case_folder(root))
            document = self._document_payload(payload, "documento.pdf")

            self.assertEqual("sconosciuto", document["document_type"])
            json.dumps(payload, ensure_ascii=False)

    def _matched_analysis(self, root: Path) -> CaseFileAnalysis:
        (root / "atti").mkdir()
        (root / "indice.html").write_text(
            '<a href="atti/001_sentenza.pdf">Sentenza</a>',
            encoding="utf-8",
        )
        (root / "atti" / "001_sentenza.pdf").write_bytes(b"synthetic pdf")
        return analyze_case_folder(root)

    def _manual_analysis(
        self,
        *,
        indexes: tuple[CaseFileIndex, ...] = (),
        warnings: tuple[ExtractionWarning, ...] = (),
    ) -> CaseFileAnalysis:
        document = CaseFileDocument(
            id="doc-1",
            filename="sentenza.pdf",
            relative_path="sentenza.pdf",
            extension=".pdf",
            size_bytes=1,
            file_order=None,
            document_type=DocumentType.SENTENZA,
            type_confidence="high",
            type_source="test",
            sha256="0" * 64,
        )
        return CaseFileAnalysis(
            source_dir="/tmp/synthetic-case",
            documents=(document,),
            total_files=1,
            total_pdf_files=1,
            total_non_pdf_files=0,
            warnings=warnings,
            indexes=indexes,
        )

    def _document_payload(
        self,
        payload: dict[str, object],
        relative_path: str,
    ) -> dict[str, object]:
        for document in payload["documents"]:
            if document["relative_path"] == relative_path:
                return document
        self.fail(f"Documento esportato non trovato: {relative_path}")


if __name__ == "__main__":
    unittest.main()
