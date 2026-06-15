"""Offline tests for OCRmyPDF command construction and helpers.

No real OCR is executed; no user PDFs are read.
"""

from __future__ import annotations

import io
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.profiles import PROFILES
from gdlex_ocr.ocr_backends import OcrBackend, OcrBackendRun
from gdlex_ocr.searchable_pdf import (
    INSTALL_HINT,
    SearchablePdfError,
    build_ocrmypdf_command,
    is_ocrmypdf_available,
    make_progressive_output_path,
    run_ocrmypdf,
)
from gdlex_ocr.worker import OcrWorker


def _synthetic_pdf(num_pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class StructuredOutputWorkerTest(unittest.TestCase):
    def test_structured_output_defaults_to_false(self) -> None:
        parameter = inspect.signature(OcrWorker.__init__).parameters[
            "structured_output"
        ]
        self.assertIs(False, parameter.default)

    def test_prepare_output_dir_reserves_progressive_job_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_pdf = root / "fascicolo.pdf"
            source_pdf.write_bytes(b"%PDF")
            output_root = root / "output"
            (output_root / "fascicolo_ocr_job").mkdir(parents=True)
            worker = OcrWorker(
                str(source_pdf),
                str(output_root),
                pages_per_block=3,
                profile=PROFILES["Bilanciato"],
                structured_output=True,
            )

            worker._prepare_output_dir()

            expected = output_root / "fascicolo_ocr_job_2"
            self.assertEqual(expected, worker.output_dir)
            self.assertTrue(expected.is_dir())
            self.assertEqual(expected / "run.log", worker._log_path)
            self.assertEqual(
                expected / "fascicolo_ocr.md",
                worker._output_layout["markdown"],
            )

    def test_markdown_post_processing_updates_file_manifest_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_pdf = root / "fascicolo.pdf"
            markdown = root / "fascicolo_ocr.md"
            source_pdf.write_bytes(b"%PDF")
            markdown.write_text(
                "Testo.\n\nCAPITOLO PRIMO\n\nContenuto.\n",
                encoding="utf-8",
            )
            worker = OcrWorker(
                str(source_pdf),
                str(root),
                pages_per_block=3,
                profile=PROFILES["Accurato testo"],
            )
            worker._manifest = {"markdown_structure": {}}
            log_messages: list[str] = []
            worker._write_log = log_messages.append

            worker._post_process_markdown(markdown)

            self.assertIn(
                "## CAPITOLO PRIMO",
                markdown.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                {
                    "enabled": True,
                    "post_processed": True,
                    "headings_added": 1,
                    "strategy": "conservative_heading_detection",
                    "warnings": [],
                },
                worker._manifest["markdown_structure"],
            )
            self.assertTrue(
                any("aggiunti 1 heading strutturali" in item
                    for item in log_messages)
            )

    def test_unavailable_source_backend_falls_back_to_original_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_pdf = root / "fascicolo.pdf"
            source_pdf.write_bytes(_synthetic_pdf(1))
            worker = OcrWorker(
                str(source_pdf),
                str(root),
                pages_per_block=3,
                profile=PROFILES["Accurato testo"],
                create_searchable=True,
                use_searchable_as_source=True,
            )
            worker._ocr_backend = OcrBackend(
                "auto",
                False,
                None,
                None,
                False,
                ("Nessun backend disponibile.",),
            )
            worker._manifest = {
                "warnings": [],
                "ocr_backend": {
                    "warnings": [],
                },
            }
            log_messages: list[str] = []
            worker._write_log = log_messages.append

            with patch(
                "gdlex_ocr.ocr_backends.subprocess.Popen",
            ) as popen:
                result = worker._prepare_searchable_source()

            self.assertEqual(source_pdf, result)
            self.assertTrue(worker._source_backend_failed)
            self.assertTrue(worker._manifest["warnings"])
            self.assertTrue(
                any("uso il PDF originale" in item for item in log_messages)
            )
            popen.assert_not_called()


class BuildOcrmypdfCommandTest(unittest.TestCase):
    def test_returns_argument_list(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertIsInstance(command, list)
        self.assertGreater(len(command), 0)

    def test_first_element_is_executable(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertEqual("ocrmypdf", command[0])

    def test_default_language_is_ita(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self._assert_option_value(command, "--language", "ita")

    def test_custom_language_is_used(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf", language="ita+eng")
        self._assert_option_value(command, "--language", "ita+eng")

    def test_input_and_output_are_last_two_positional_args(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertEqual("in.pdf", command[-2])
        self.assertEqual("out.pdf", command[-1])

    def test_jobs_added_when_provided(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf", jobs=4)
        self._assert_option_value(command, "--jobs", "4")

    def test_jobs_absent_when_not_provided(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertNotIn("--jobs", command)

    def test_safety_flags_present(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertIn("--deskew", command)
        self.assertIn("--rotate-pages", command)
        self.assertIn("--skip-text", command)

    def test_shell_string_not_returned(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertNotIsInstance(command, str)

    def _assert_option_value(
        self, command: list[str], option: str, expected: str
    ) -> None:
        idx = command.index(option)
        self.assertEqual(expected, command[idx + 1])


class IsOcrmypdfAvailableTest(unittest.TestCase):
    def test_returns_true_when_found_in_path(self) -> None:
        with patch(
            "gdlex_ocr.searchable_pdf.shutil.which",
            return_value="/usr/bin/ocrmypdf",
        ):
            self.assertTrue(is_ocrmypdf_available())

    def test_returns_false_when_not_in_path(self) -> None:
        with patch(
            "gdlex_ocr.searchable_pdf.shutil.which",
            return_value=None,
        ):
            self.assertFalse(is_ocrmypdf_available())

    def test_return_type_is_bool(self) -> None:
        with patch("gdlex_ocr.searchable_pdf.shutil.which", return_value=None):
            result = is_ocrmypdf_available()
        self.assertIsInstance(result, bool)


class RunOcrmypdfTest(unittest.TestCase):
    def test_missing_ocrmypdf_raises_error_with_install_hint(self) -> None:
        with patch(
            "gdlex_ocr.searchable_pdf.is_ocrmypdf_available",
            return_value=False,
        ):
            with self.assertRaisesRegex(
                SearchablePdfError,
                INSTALL_HINT,
            ):
                run_ocrmypdf("in.pdf", "out.pdf")


class MakeProgressiveOutputPathTest(unittest.TestCase):
    def test_returns_base_path_when_not_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = make_progressive_output_path(tmpdir, "mydoc")
            self.assertEqual(Path(tmpdir) / "mydoc_searchable.pdf", result)

    def test_increments_suffix_when_base_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "mydoc_searchable.pdf").write_bytes(b"x")
            result = make_progressive_output_path(tmpdir, "mydoc")
            self.assertEqual(Path(tmpdir) / "mydoc_searchable_2.pdf", result)

    def test_increments_further_when_multiple_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "mydoc_searchable.pdf").write_bytes(b"x")
            (Path(tmpdir) / "mydoc_searchable_2.pdf").write_bytes(b"x")
            result = make_progressive_output_path(tmpdir, "mydoc")
            self.assertEqual(Path(tmpdir) / "mydoc_searchable_3.pdf", result)

    def test_custom_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = make_progressive_output_path(tmpdir, "mydoc", suffix="_ocr")
            self.assertEqual(Path(tmpdir) / "mydoc_ocr.pdf", result)

    def test_result_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = make_progressive_output_path(tmpdir, "mydoc")
            self.assertFalse(result.exists())


class SearchablePdfPipelineTest(unittest.TestCase):
    def test_uses_markdown_headings_for_pdf_and_index(self) -> None:
        markdown = """\
## Blocco 1 - Pagine 1-3

## Annotazione di P.G.
## Verbale di sommarie informazioni

## Blocco 2 - Pagine 4-6

## Richiesta di archiviazione
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_pdf = root / "fascicolo.pdf"
            markdown_path = root / "fascicolo_ocr.md"
            source_pdf.write_bytes(_synthetic_pdf(6))
            markdown_path.write_text(markdown, encoding="utf-8")
            worker = OcrWorker(
                str(source_pdf),
                str(root),
                pages_per_block=3,
                profile=PROFILES["Bilanciato"],
                create_searchable=True,
            )
            worker._manifest = {
                "outputs": {
                    "searchable_pdf": None,
                    "index_markdown": None,
                },
                "bookmarks": {},
                "ocr_backend": {},
            }
            log_messages: list[str] = []
            worker._write_log = log_messages.append

            def fake_ocr(input_path, output_path, **_kwargs) -> None:
                Path(output_path).write_bytes(Path(input_path).read_bytes())

            backend = OcrBackend(
                "ocrmypdf",
                True,
                "/usr/bin/ocrmypdf",
                None,
                True,
            )

            def fake_backend(
                _backend,
                input_path,
                output_path,
                **_kwargs,
            ) -> OcrBackendRun:
                fake_ocr(input_path, output_path)
                return OcrBackendRun(
                    "ocrmypdf",
                    ("ocrmypdf", str(input_path), str(output_path)),
                )

            with (
                patch(
                    "gdlex_ocr.worker.detect_ocr_backend",
                    return_value=backend,
                ),
                patch(
                    "gdlex_ocr.worker.run_ocr_backend",
                    side_effect=fake_backend,
                ),
            ):
                worker._build_searchable_pdf(6, markdown_path)

            searchable_path = root / "fascicolo_searchable.pdf"
            reader = PdfReader(searchable_path)
            outline = reader.outline
            titles = [item.title for item in outline]
            destinations = [
                reader.get_destination_page_number(item) for item in outline
            ]

            self.assertEqual(
                [
                    "Annotazione di P.G",
                    "Verbale di sommarie informazioni",
                    "Richiesta di archiviazione",
                ],
                titles,
            )
            self.assertEqual([0, 0, 3], destinations)

            index_path = root / "fascicolo_ocr_index.md"
            self.assertTrue(index_path.is_file())
            index = index_path.read_text(encoding="utf-8")
            self.assertIn("`markdown_headings`", index)
            self.assertIn("| Annotazione di P.G | 1 |", index)
            self.assertIn(
                "| Verbale di sommarie informazioni | 1 |",
                index,
            )
            self.assertIn("| Richiesta di archiviazione | 4 |", index)
            self.assertEqual(
                {
                    "strategy": "markdown_headings",
                    "count": 3,
                    "fallback": False,
                    "warnings": [],
                    "reason": None,
                },
                worker._manifest["bookmarks"],
            )
            self.assertTrue(worker._manifest["ocr_backend"]["used"])
            self.assertEqual(
                "ocrmypdf",
                worker._manifest["ocr_backend"]["name"],
            )
            self.assertTrue(
                any(
                    "strategia markdown_headings, 3 voci" in message
                    for message in log_messages
                )
            )


if __name__ == "__main__":
    unittest.main()
