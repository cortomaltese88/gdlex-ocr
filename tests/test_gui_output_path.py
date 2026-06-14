"""Headless tests for the GUI source and output path fields."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow, resolve_output_path, resolve_pdf_path


class OutputPathGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_output_field_is_editable_with_clear_placeholder(self) -> None:
        self.assertFalse(self.window.output_edit.isReadOnly())
        self.assertIn("incolla", self.window.output_edit.placeholderText())

    def test_manual_output_path_survives_pdf_selection(self) -> None:
        manual_path = "/tmp/output-personalizzato"
        self.window.output_edit.setText(manual_path)
        self.window.output_edit.textEdited.emit(manual_path)

        with (
            patch(
                "gdlex_ocr.gui.QFileDialog.getOpenFileName",
                return_value=("/tmp/documenti/fascicolo.pdf", ""),
            ),
            patch("gdlex_ocr.gui.count_pdf_pages", return_value=12),
        ):
            self.window._select_pdf()

        self.assertEqual(manual_path, self.window.output_edit.text())

    def test_pdf_selection_updates_only_an_unmodified_suggestion(self) -> None:
        selections = [
            ("/tmp/primo/fascicolo.pdf", ""),
            ("/tmp/secondo/fascicolo.pdf", ""),
        ]
        with (
            patch(
                "gdlex_ocr.gui.QFileDialog.getOpenFileName",
                side_effect=selections,
            ),
            patch("gdlex_ocr.gui.count_pdf_pages", return_value=12),
        ):
            self.window._select_pdf()
            self.assertEqual("/tmp/primo", self.window.output_edit.text())
            self.window._select_pdf()

        self.assertEqual("/tmp/secondo", self.window.output_edit.text())

    def test_browse_updates_output_field(self) -> None:
        with patch(
            "gdlex_ocr.gui.QFileDialog.getExistingDirectory",
            return_value="/tmp/output-da-browse",
        ):
            self.window._select_output()

        self.assertEqual("/tmp/output-da-browse", self.window.output_edit.text())
        self.assertTrue(self.window._output_path_customized)

    def test_resolve_output_path_expands_user_and_environment(self) -> None:
        with patch.dict(os.environ, {"GDLEX_OUTPUT": "risultati"}):
            result = resolve_output_path("~/$GDLEX_OUTPUT")

        self.assertEqual(Path.home() / "risultati", result)

    def test_start_creates_and_passes_expanded_output_path_to_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "fascicolo.pdf"
            pdf_path.touch()
            expected_output = Path(tmpdir) / "risultati"
            self.window.pdf_edit.setText(str(pdf_path))
            self.window.output_edit.setText("$GDLEX_TEST_ROOT/risultati")
            worker = MagicMock()
            worker.isRunning.return_value = False

            with (
                patch.dict(os.environ, {"GDLEX_TEST_ROOT": tmpdir}),
                patch("gdlex_ocr.gui.count_pdf_pages", return_value=3),
                patch("gdlex_ocr.gui.OcrWorker", return_value=worker) as worker_cls,
            ):
                self.window._start()

            self.assertTrue(expected_output.is_dir())
            self.assertEqual(str(expected_output), worker_cls.call_args.args[1])
            worker.start.assert_called_once_with()


class PdfPathGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_pdf_field_is_editable_and_accepts_keyboard_paste(self) -> None:
        pdf_path = "/tmp/fascicolo-incollato.pdf"
        self.assertFalse(self.window.pdf_edit.isReadOnly())
        self.assertIn("incolla", self.window.pdf_edit.placeholderText())

        QApplication.clipboard().setText(pdf_path)
        self.window.pdf_edit.setFocus()
        QTest.keyClick(
            self.window.pdf_edit,
            Qt.Key.Key_V,
            Qt.KeyboardModifier.ControlModifier,
        )

        self.assertEqual(pdf_path, self.window.pdf_edit.text())

    def test_manual_pdf_path_is_expanded_and_passed_to_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "fascicolo.pdf"
            pdf_path.touch()
            output_path = Path(tmpdir) / "output"
            self.window.pdf_edit.setText("$GDLEX_PDF_ROOT/fascicolo.pdf")
            self.window.output_edit.setText(str(output_path))
            worker = MagicMock()
            worker.isRunning.return_value = False

            with (
                patch.dict(os.environ, {"GDLEX_PDF_ROOT": tmpdir}),
                patch("gdlex_ocr.gui.count_pdf_pages", return_value=7),
                patch("gdlex_ocr.gui.OcrWorker", return_value=worker) as worker_cls,
            ):
                self.window._start()

            self.assertEqual(str(pdf_path), worker_cls.call_args.args[0])
            self.assertEqual("$GDLEX_PDF_ROOT/fascicolo.pdf", self.window.pdf_edit.text())
            self.assertEqual("7 pagine", self.window.page_count_label.text())
            worker.start.assert_called_once_with()

    def test_browse_updates_pdf_field(self) -> None:
        selected_path = "/tmp/documenti/fascicolo.pdf"
        with (
            patch(
                "gdlex_ocr.gui.QFileDialog.getOpenFileName",
                return_value=(selected_path, ""),
            ),
            patch("gdlex_ocr.gui.count_pdf_pages", return_value=12),
            patch.object(Path, "is_file", return_value=True),
        ):
            self.window._select_pdf()

        self.assertEqual(selected_path, self.window.pdf_edit.text())
        self.assertEqual("12 pagine", self.window.page_count_label.text())

    def test_resolve_pdf_path_expands_user_and_environment(self) -> None:
        with patch.dict(os.environ, {"GDLEX_PDF": "documenti/fascicolo.pdf"}):
            result = resolve_pdf_path("~/$GDLEX_PDF")

        self.assertEqual(Path.home() / "documenti/fascicolo.pdf", result)

    def test_start_rejects_missing_pdf(self) -> None:
        self.window.pdf_edit.setText("/tmp/pdf-inesistente.pdf")
        self.window.output_edit.setText("/tmp/output")

        with (
            patch("gdlex_ocr.gui.QMessageBox.warning") as warning,
            patch("gdlex_ocr.gui.OcrWorker") as worker_cls,
        ):
            self.window._start()

        warning.assert_called_once()
        self.assertEqual("File non trovato", warning.call_args.args[1])
        worker_cls.assert_not_called()

    def test_start_rejects_non_pdf_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "fascicolo.txt"
            source_path.touch()
            self.window.pdf_edit.setText(str(source_path))
            self.window.output_edit.setText(str(Path(tmpdir) / "output"))

            with (
                patch("gdlex_ocr.gui.QMessageBox.warning") as warning,
                patch("gdlex_ocr.gui.OcrWorker") as worker_cls,
            ):
                self.window._start()

        warning.assert_called_once()
        self.assertEqual("Formato non valido", warning.call_args.args[1])
        worker_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
