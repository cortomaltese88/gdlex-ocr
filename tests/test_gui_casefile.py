"""Headless tests for the GUI casefile analysis section."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import CasefileGuiResult, MainWindow, run_casefile_analysis


class CasefileGuiControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_casefile_gui_controls_exist(self) -> None:
        self.assertIsNotNone(self.window.casefile_input_edit)
        self.assertIsNotNone(self.window.casefile_output_edit)
        self.assertIsNotNone(self.window.casefile_input_button)
        self.assertIsNotNone(self.window.casefile_output_button)
        self.assertIsNotNone(self.window.casefile_start_button)
        self.assertEqual(
            "Analizza fascicolo",
            self.window.casefile_start_button.text(),
        )
        self.assertFalse(self.window.casefile_input_edit.isReadOnly())
        self.assertFalse(self.window.casefile_output_edit.isReadOnly())

    def test_casefile_gui_does_not_store_sensitive_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            sensitive_dir = Path(tmpdir) / "sensitive-client-data"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
            window = MainWindow(settings=settings)

            window.casefile_input_edit.setText(str(sensitive_dir))
            window.casefile_output_edit.setText(str(Path(tmpdir) / "output"))
            window.close()
            settings.sync()

            if settings_path.exists():
                saved_text = settings_path.read_text(encoding="utf-8")
                self.assertNotIn("sensitive-client-data", saved_text)

            window.deleteLater()
            self.app.processEvents()

    def test_casefile_gui_invokes_worker_or_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            output_dir = Path(tmpdir) / "output"
            self.window.casefile_input_edit.setText(str(input_dir))
            self.window.casefile_output_edit.setText(str(output_dir))

            worker = MagicMock()

            with patch(
                "gdlex_ocr.gui.CasefileWorker",
                return_value=worker,
            ) as worker_cls:
                self.window._start_casefile_analysis()

            worker_cls.assert_called_once()
            call_args = worker_cls.call_args
            self.assertEqual(input_dir, call_args.args[0])
            self.assertEqual(output_dir, call_args.args[1])
            worker.start.assert_called_once()

    def test_casefile_gui_rejects_missing_input(self) -> None:
        self.window.casefile_input_edit.setText("")
        self.window.casefile_output_edit.setText("/tmp/output")
        with (
            patch("gdlex_ocr.gui.QMessageBox.warning") as warning,
            patch("gdlex_ocr.gui.CasefileWorker") as worker_cls,
        ):
            self.window._start_casefile_analysis()
        warning.assert_called_once()
        self.assertEqual("Dati mancanti", warning.call_args.args[1])
        worker_cls.assert_not_called()

    def test_casefile_gui_rejects_nonexistent_input_dir(self) -> None:
        self.window.casefile_input_edit.setText("/tmp/nonexistent-dir-12345")
        self.window.casefile_output_edit.setText("/tmp/output")
        with (
            patch("gdlex_ocr.gui.QMessageBox.warning") as warning,
            patch("gdlex_ocr.gui.CasefileWorker") as worker_cls,
        ):
            self.window._start_casefile_analysis()
        warning.assert_called_once()
        self.assertEqual("Cartella non trovata", warning.call_args.args[1])
        worker_cls.assert_not_called()

    def test_casefile_gui_rejects_missing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            self.window.casefile_input_edit.setText(str(input_dir))
            self.window.casefile_output_edit.setText("")
            with (
                patch("gdlex_ocr.gui.QMessageBox.warning") as warning,
                patch("gdlex_ocr.gui.CasefileWorker") as worker_cls,
            ):
                self.window._start_casefile_analysis()
        warning.assert_called_once()
        self.assertEqual("Dati mancanti", warning.call_args.args[1])
        worker_cls.assert_not_called()

    def test_casefile_gui_disables_controls_during_analysis(self) -> None:
        self.assertTrue(self.window.casefile_start_button.isEnabled())
        self.assertTrue(self.window.casefile_input_edit.isEnabled())
        self.assertTrue(self.window.casefile_output_edit.isEnabled())

        self.window._set_casefile_running(True)
        self.assertFalse(self.window.casefile_start_button.isEnabled())
        self.assertFalse(self.window.casefile_input_edit.isEnabled())
        self.assertFalse(self.window.casefile_input_button.isEnabled())
        self.assertFalse(self.window.casefile_output_edit.isEnabled())
        self.assertFalse(self.window.casefile_output_button.isEnabled())

        self.window._set_casefile_running(False)
        self.assertTrue(self.window.casefile_start_button.isEnabled())
        self.assertTrue(self.window.casefile_input_edit.isEnabled())

    def test_casefile_gui_does_not_interfere_with_ocr_controls(self) -> None:
        self.window._set_casefile_running(True)
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertTrue(self.window.pdf_edit.isEnabled())
        self.assertTrue(self.window.output_edit.isEnabled())


class CasefileAnalysisHelperTest(unittest.TestCase):
    def test_casefile_gui_success_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            (input_dir / "sentenza.pdf").write_bytes(b"%PDF-fake")
            (input_dir / "memoria.pdf").write_bytes(b"%PDF-fake-2")
            (input_dir / "readme.txt").write_bytes(b"notes")
            output_dir = Path(tmpdir) / "output"

            result = run_casefile_analysis(input_dir, output_dir)

            self.assertIsInstance(result, CasefileGuiResult)
            self.assertEqual(3, result.total_files)
            self.assertEqual(2, result.total_pdf_files)
            self.assertIsInstance(result.total_indexes, int)
            self.assertIsInstance(result.total_warnings, int)
            self.assertTrue(result.json_path.is_file())
            self.assertTrue(result.markdown_path.is_file())
            self.assertEqual("fascicolo_index.json", result.json_path.name)
            self.assertEqual("fascicolo_index.md", result.markdown_path.name)

    def test_casefile_gui_success_creates_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()
            (input_dir / "doc.pdf").write_bytes(b"%PDF-1")
            output_dir = Path(tmpdir) / "nested" / "output"

            result = run_casefile_analysis(input_dir, output_dir)

            self.assertTrue(output_dir.is_dir())
            self.assertTrue(result.json_path.is_file())

    def test_casefile_gui_raises_on_missing_input_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "does-not-exist"
            output_dir = Path(tmpdir) / "output"

            with self.assertRaises(FileNotFoundError):
                run_casefile_analysis(missing, output_dir)


if __name__ == "__main__":
    unittest.main()
