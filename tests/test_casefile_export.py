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
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    default_casefile_csv_path,
    default_casefile_json_path,
    default_casefile_markdown_path,
    default_casefile_units_csv_path,
    format_casefile_analysis_csv,
    format_casefile_analysis_markdown,
    format_casefile_units_csv,
    write_casefile_analysis_csv,
    write_casefile_analysis_json,
    write_casefile_analysis_markdown,
    write_casefile_units_csv,
)
from gdlex_ocr.casefile_index import CaseFileIndexEntry, CaseFileIndexMatch
from gdlex_ocr.manifest import file_sha256


class CaseFileExportTest(unittest.TestCase):
    def test_write_casefile_analysis_json_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "out" / "fascicolo_index.json"

            returned_path = write_casefile_analysis_json(analysis, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(output_path, returned_path)
            self.assertEqual(
                {
                    "source_dir",
                    "casefile_profile",
                    "casefile_profile_confidence",
                    "casefile_profile_reason",
                    "summary",
                    "documents",
                    "indexes",
                    "warnings",
                    "units",
                },
                set(payload),
            )
            self.assertEqual(2, payload["summary"]["total_files"])

    def test_write_casefile_analysis_json_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "missing" / "nested" / "fascicolo_index.json"

            write_casefile_analysis_json(analysis, output_path)

            self.assertTrue(output_path.is_file())

    def test_write_casefile_analysis_json_uses_utf8_no_ascii_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "atti").mkdir()
            (root / "indice.html").write_text(
                '<a href="atti/001_memoria_è.pdf">Memòria difensiva</a>',
                encoding="utf-8",
            )
            (root / "atti" / "001_memoria_è.pdf").write_bytes(
                b"synthetic pdf"
            )
            output_path = root / "fascicolo_index.json"

            write_casefile_analysis_json(analyze_case_folder(root), output_path)
            serialized = output_path.read_text(encoding="utf-8")

            self.assertIn("001_memoria_è.pdf", serialized)
            self.assertIn("Memòria difensiva", serialized)
            self.assertNotIn("\\u00e8", serialized)
            self.assertNotIn("\\u00f2", serialized)

    def test_write_casefile_analysis_json_rejects_directory_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)

            with self.assertRaisesRegex(
                IsADirectoryError,
                "cartella",
            ):
                write_casefile_analysis_json(analysis, root)

    def test_default_casefile_json_path(self) -> None:
        self.assertEqual(
            Path("out") / "fascicolo_index.json",
            default_casefile_json_path(Path("out")),
        )

    def test_written_json_does_not_leak_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "fascicolo_index.json"

            write_casefile_analysis_json(analysis, output_path)
            serialized = output_path.read_text(encoding="utf-8")

            self.assertNotIn(str(root), serialized)
            self.assertNotIn(str(root).replace("/", "\\/"), serialized)

    def test_written_json_contains_index_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "atti").mkdir()
            (root / "indice.html").write_text(
                '<html><body><a href="atti/001_sentenza.pdf">'
                "Sentenza 001</a></body></html>",
                encoding="utf-8",
            )
            (root / "atti" / "001_sentenza.pdf").write_bytes(
                b"%PDF-1.4 synthetic"
            )
            output_path = root / "fascicolo_index.json"

            write_casefile_analysis_json(analyze_case_folder(root), output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            entry = payload["indexes"][0]["entries"][0]
            match = entry["matches"][0]

            self.assertEqual("atti/001_sentenza.pdf", entry["referenced_path"])
            self.assertEqual(
                "atti/001_sentenza.pdf",
                match["matched_relative_path"],
            )
            self.assertEqual("relative_path_exact", match["strategy"])

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
                    "total_units": 0,
                    "total_technical_files": 0,
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

    def test_export_safe_path_strips_relative_traversal(self) -> None:
        warning = ExtractionWarning(
            code="synthetic",
            message="Errore su ../../../etc/passwd e ../foo/bar.pdf",
            path="../../../etc/passwd",
        )
        match = CaseFileIndexMatch(
            entry_row_number=1,
            document_id="doc-1",
            entry_reference="../foo/bar.pdf",
            matched_relative_path="atti/../../segreto.pdf",
            confidence="high",
            strategy="basename_exact",
            warnings=(warning,),
        )
        entry = CaseFileIndexEntry(
            row_number=1,
            label="Documento",
            referenced_path="../foo/bar.pdf",
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
                    relative_path="indici/../../indice.html",
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

        serialized = json.dumps(
            casefile_analysis_to_dict(analysis),
            ensure_ascii=False,
        )
        markdown = format_casefile_analysis_markdown(analysis)

        for content in (serialized, markdown):
            self.assertNotIn("../", content)
            self.assertNotIn("..\\", content)
            self.assertNotIn("../../../etc/passwd", content)
            self.assertNotIn("atti/../../segreto.pdf", content)
            self.assertIn("passwd", content)
            self.assertIn("bar.pdf", content)

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

    # -- Markdown export tests --

    def test_format_casefile_analysis_markdown_contains_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("# Indice fascicolo", markdown)
            self.assertIn("## Riepilogo", markdown)
            self.assertIn("- File totali: 2", markdown)
            self.assertIn("- PDF: 1", markdown)
            self.assertIn("- Non PDF: 1", markdown)
            self.assertIn("- Indici rilevati: 1", markdown)
            self.assertIn("- Voci indice: 1", markdown)
            self.assertIn("- Match indice-documenti: 1", markdown)
            self.assertIn("- Warning: 0", markdown)

    def test_format_casefile_analysis_markdown_lists_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Documenti", markdown)
            self.assertIn("| # | Tipo | Conf. | File | Dimensione | SHA-256 |", markdown)
            self.assertIn("atti/001_sentenza.pdf", markdown)
            self.assertIn("indice.html", markdown)

    def test_format_casefile_analysis_markdown_lists_indexes_entries_and_matches(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Indici rilevati", markdown)
            self.assertIn("### indice.html", markdown)
            self.assertIn("- formato: html", markdown)
            self.assertIn("- confidenza: high", markdown)
            self.assertIn("- voci: 1", markdown)
            self.assertIn("| Riga | Etichetta | Riferimento | Match |", markdown)
            self.assertIn("atti/001_sentenza.pdf", markdown)

    def test_markdown_does_not_leak_absolute_paths(self) -> None:
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

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertNotIn(str(root), markdown)

    def test_markdown_truncates_long_labels_and_warnings(self) -> None:
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

        markdown = format_casefile_analysis_markdown(analysis)

        for line in markdown.splitlines():
            if "Sentenza" in line and "| 1 |" in line:
                cells = line.split("|")
                label_cell = cells[2].strip()
                self.assertLessEqual(len(label_cell), 160)
                self.assertTrue(label_cell.endswith("..."))
            if "long_warning" in line:
                self.assertLessEqual(len(line), 500)

    def test_write_casefile_analysis_markdown_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "out" / "fascicolo_index.md"

            returned_path = write_casefile_analysis_markdown(analysis, output_path)
            content = output_path.read_text(encoding="utf-8")

            self.assertEqual(output_path, returned_path)
            self.assertIn("# Indice fascicolo", content)
            self.assertIn("## Riepilogo", content)

    def test_write_casefile_analysis_markdown_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "missing" / "nested" / "fascicolo_index.md"

            write_casefile_analysis_markdown(analysis, output_path)

            self.assertTrue(output_path.is_file())

    def test_write_casefile_analysis_markdown_rejects_directory_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)

            with self.assertRaisesRegex(
                IsADirectoryError,
                "cartella",
            ):
                write_casefile_analysis_markdown(analysis, root)

    def test_default_casefile_markdown_path(self) -> None:
        self.assertEqual(
            Path("out") / "fascicolo_index.md",
            default_casefile_markdown_path(Path("out")),
        )

    # -- Markdown: File più grandi --

    def test_markdown_contains_largest_files_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## File più grandi", markdown)
            self.assertIn("| # | File | Dimensione | Tipo |", markdown)

    # -- Markdown: Riepilogo operativo --

    def test_markdown_contains_riepilogo_operativo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Riepilogo operativo", markdown)
            self.assertIn("Dimensione totale fascicolo:", markdown)
            self.assertIn("Copertura indice:", markdown)
            self.assertIn("1/1 voci con match", markdown)

    # -- CSV export tests --

    def test_default_casefile_csv_path(self) -> None:
        self.assertEqual(
            Path("out") / "fascicolo_index.csv",
            default_casefile_csv_path(Path("out")),
        )

    def test_format_casefile_analysis_csv_header_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            analysis = self._matched_analysis(Path(temporary_directory))

            csv_text = format_casefile_analysis_csv(analysis)
            lines = csv_text.strip().splitlines()

            self.assertEqual(3, len(lines))
            self.assertIn("#", lines[0])
            self.assertIn("Tipo", lines[0])
            self.assertIn("SHA-256", lines[0])

    def test_write_casefile_analysis_csv_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "out" / "fascicolo_index.csv"

            returned_path = write_casefile_analysis_csv(analysis, output_path)
            content = output_path.read_text(encoding="utf-8")

            self.assertEqual(output_path, returned_path)
            self.assertIn("001_sentenza.pdf", content)

    def test_write_casefile_analysis_csv_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)
            output_path = root / "missing" / "nested" / "fascicolo_index.csv"

            write_casefile_analysis_csv(analysis, output_path)

            self.assertTrue(output_path.is_file())

    def test_write_casefile_analysis_csv_rejects_directory_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)

            with self.assertRaisesRegex(IsADirectoryError, "cartella"):
                write_casefile_analysis_csv(analysis, root)

    def test_csv_does_not_leak_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            analysis = self._matched_analysis(root)

            csv_text = format_casefile_analysis_csv(analysis)

            self.assertNotIn(str(root), csv_text)

    # -- Units CSV export tests --

    def test_default_casefile_units_csv_path(self) -> None:
        self.assertEqual(
            Path("out") / "fascicolo_unita.csv",
            default_casefile_units_csv_path(Path("out")),
        )

    def test_format_casefile_units_csv_header_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            lines = csv_text.strip().splitlines()

            self.assertEqual(3, len(lines))
            self.assertIn("ID unità", lines[0])
            self.assertIn("PDF principale", lines[0])
            self.assertIn("SHA-256", lines[0])

    def test_format_casefile_units_csv_contains_unit_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertIn("100", csv_text)
            self.assertIn("200", csv_text)
            self.assertIn("100/100.pdf", csv_text)
            self.assertIn("ListaAllegati.html", csv_text)

    def test_format_casefile_units_csv_includes_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            main_pdf = root / "100" / "100.pdf"
            self.assertIn(file_sha256(main_pdf), csv_text)

    def test_format_casefile_units_csv_complete_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertIn("sì", csv_text)

    def test_format_casefile_units_csv_empty_when_no_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sentenza.pdf").write_bytes(b"%PDF-1.4")

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            lines = csv_text.strip().splitlines()

            self.assertEqual(1, len(lines))

    def test_write_casefile_units_csv_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)
            analysis = analyze_case_folder(root)
            output_path = root / "out" / "fascicolo_unita.csv"

            returned_path = write_casefile_units_csv(analysis, output_path)

            self.assertEqual(output_path, returned_path)
            self.assertTrue(output_path.is_file())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("100", content)

    def test_write_casefile_units_csv_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)
            analysis = analyze_case_folder(root)
            output_path = root / "missing" / "nested" / "fascicolo_unita.csv"

            write_casefile_units_csv(analysis, output_path)

            self.assertTrue(output_path.is_file())

    def test_write_casefile_units_csv_rejects_directory_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)
            analysis = analyze_case_folder(root)

            with self.assertRaisesRegex(IsADirectoryError, "cartella"):
                write_casefile_units_csv(analysis, root)

    def test_units_csv_does_not_leak_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_units_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertNotIn(str(root), csv_text)

    def _create_units_fixture(self, root: Path) -> None:
        for uid in ("100", "200"):
            d = root / uid
            d.mkdir()
            (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic-" + uid.encode())
            (d / "COMPLETE").write_bytes(b"")
            (d / "ListaAllegati.html").write_text(
                '<html><body><a href="doc.pdf">Doc</a></body></html>',
                encoding="utf-8",
            )

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
