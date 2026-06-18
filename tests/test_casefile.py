"""Offline tests for local case-folder scanning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import (
    DocumentType,
    analyze_case_folder,
    normalize_casefile_documents,
    scan_directory,
)
from gdlex_ocr.manifest import file_sha256


class CaseFileTest(unittest.TestCase):
    def test_scan_directory_lists_files_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "002_root.pdf").write_bytes(b"root")
            nested = root / "sub"
            nested.mkdir()
            (nested / "001_nested.pdf").write_bytes(b"nested")

            paths = scan_directory(root)

            self.assertEqual(
                ["002_root.pdf", "sub/001_nested.pdf"],
                [path.relative_to(root).as_posix() for path in paths],
            )

    def test_scan_directory_ignores_hidden_files_and_hidden_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / ".hidden.pdf").write_bytes(b"hidden")
            (root / "visible.pdf").write_bytes(b"visible")
            hidden_dir = root / ".hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / "file.pdf").write_bytes(b"hidden")

            paths = scan_directory(root)

            self.assertEqual(
                ["visible.pdf"],
                [path.relative_to(root).as_posix() for path in paths],
            )

    def test_scan_directory_does_not_follow_directory_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "target"
            target.mkdir()
            (target / "inside.pdf").write_bytes(b"target")
            link = root / "linked"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Symlink non supportati: {exc}")

            paths = scan_directory(root)

            self.assertEqual(
                ["target/inside.pdf"],
                [path.relative_to(root).as_posix() for path in paths],
            )

    def test_normalize_counts_pdf_and_non_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lower = root / "one.pdf"
            upper = root / "two.PDF"
            text = root / "notes.txt"
            for path in (lower, upper, text):
                path.write_bytes(b"x")

            analysis = normalize_casefile_documents(root, (lower, upper, text))

            self.assertEqual(3, analysis.total_files)
            self.assertEqual(2, analysis.total_pdf_files)
            self.assertEqual(1, analysis.total_non_pdf_files)
            self.assertEqual(
                [".txt", ".pdf", ".pdf"],
                [document.extension for document in analysis.documents],
            )

    def test_relative_paths_do_not_leak_absolute_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "document.pdf"
            pdf.write_bytes(b"x")

            analysis = normalize_casefile_documents(root, (pdf,))

            self.assertEqual("document.pdf", analysis.documents[0].relative_path)
            self.assertNotIn(str(root), analysis.documents[0].relative_path)

    def test_path_with_spaces_and_accents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            folder = root / "cartella con spazi"
            folder.mkdir()
            pdf = folder / "sentenza àè.pdf"
            pdf.write_bytes(b"x")

            analysis = analyze_case_folder(root)

            self.assertEqual(
                "cartella con spazi/sentenza àè.pdf",
                analysis.documents[0].relative_path,
            )
            self.assertEqual("sentenza àè.pdf", analysis.documents[0].filename)

    def test_analyze_case_folder_rejects_missing_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"

            with self.assertRaises(FileNotFoundError):
                analyze_case_folder(missing)

    def test_analyze_case_folder_rejects_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "file.pdf"
            path.write_bytes(b"x")

            with self.assertRaises(NotADirectoryError):
                analyze_case_folder(path)

    def test_document_ids_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "001_sentenza.pdf"
            pdf.write_bytes(b"x")

            first = analyze_case_folder(root)
            second = analyze_case_folder(root)

            self.assertEqual(
                [document.id for document in first.documents],
                [document.id for document in second.documents],
            )
            self.assertEqual(1, first.documents[0].file_order)

    def test_default_document_type_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "sentenza.pdf"
            pdf.write_bytes(b"x")

            analysis = analyze_case_folder(root)
            document = analysis.documents[0]

            self.assertEqual(DocumentType.SCONOSCIUTO, document.document_type)
            self.assertEqual("low", document.type_confidence)
            self.assertEqual("none", document.type_source)
            self.assertEqual(file_sha256(pdf), document.sha256)

    def test_document_sha256_matches_manifest_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "document.pdf"
            pdf.write_bytes(b"synthetic pdf bytes")

            analysis = analyze_case_folder(root)

            self.assertEqual(file_sha256(pdf), analysis.documents[0].sha256)

    def test_document_sha256_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf = root / "document.pdf"
            pdf.write_bytes(b"same bytes")

            first = analyze_case_folder(root)
            second = analyze_case_folder(root)

            self.assertEqual(
                [document.sha256 for document in first.documents],
                [document.sha256 for document in second.documents],
            )

    def test_duplicate_files_with_same_content_are_warned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "001_original.pdf").write_bytes(b"same content")
            (root / "002_copy.pdf").write_bytes(b"same content")

            analysis = analyze_case_folder(root)

            duplicate_warnings = [
                warning
                for warning in analysis.warnings
                if warning.code == "duplicate_file"
            ]
            self.assertEqual(1, len(duplicate_warnings))
            self.assertEqual("002_copy.pdf", duplicate_warnings[0].path)
            self.assertIn(
                duplicate_warnings[0],
                analysis.documents[1].warnings,
            )

    def test_different_files_are_not_warned_as_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "001_first.pdf").write_bytes(b"first content")
            (root / "002_second.pdf").write_bytes(b"second content")

            analysis = analyze_case_folder(root)

            self.assertEqual(
                [],
                [
                    warning
                    for warning in analysis.warnings
                    if warning.code == "duplicate_file"
                ],
            )

    def test_non_pdf_documents_have_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            text = root / "notes.txt"
            text.write_bytes(b"plain text content")

            analysis = analyze_case_folder(root)

            document = analysis.documents[0]
            self.assertEqual(".txt", document.extension)
            self.assertEqual(file_sha256(text), document.sha256)

    def test_duplicate_warning_paths_are_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "sub"
            nested.mkdir()
            (root / "001_original.pdf").write_bytes(b"same content")
            (nested / "002_copy.pdf").write_bytes(b"same content")

            analysis = analyze_case_folder(root)

            duplicate_warnings = [
                warning
                for warning in analysis.warnings
                if warning.code == "duplicate_file"
            ]
            self.assertEqual(1, len(duplicate_warnings))
            self.assertEqual("sub/002_copy.pdf", duplicate_warnings[0].path)
            self.assertNotIn(str(root), duplicate_warnings[0].path or "")


if __name__ == "__main__":
    unittest.main()
