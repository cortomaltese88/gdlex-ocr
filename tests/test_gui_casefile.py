"""Headless tests for the GUI casefile analysis section."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QScrollArea, QTabWidget

from gdlex_ocr.gui import CasefileGuiResult, MainWindow, run_casefile_analysis
from gdlex_ocr.theme import apply_theme


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

    def test_casefile_output_buttons_exist(self) -> None:
        self.assertIsNotNone(self.window.casefile_open_folder_button)
        self.assertIsNotNone(self.window.casefile_open_report_button)
        self.assertFalse(self.window.casefile_open_folder_button.isEnabled())
        self.assertFalse(self.window.casefile_open_report_button.isEnabled())
        self.assertEqual(
            "casefileOpenFolderButton",
            self.window.casefile_open_folder_button.objectName(),
        )
        self.assertEqual(
            "casefileOpenReportButton",
            self.window.casefile_open_report_button.objectName(),
        )

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

    # ------------------------------------------------------------------
    # Tab-based layout tests
    # ------------------------------------------------------------------

    def test_main_gui_has_separate_casefile_tab(self) -> None:
        tabs = self.window.main_tabs
        self.assertIsInstance(tabs, QTabWidget)
        tab_labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("OCR documento", tab_labels)
        self.assertIn("Fascicolo", tab_labels)
        self.assertEqual(2, tabs.count())

    def test_ocr_controls_remain_in_ocr_tab(self) -> None:
        ocr_tab = self.window.ocr_tab
        self.assertIsNotNone(ocr_tab)
        for widget in (
            self.window.pdf_edit,
            self.window.output_edit,
            self.window.profile_combo,
            self.window.block_size_spin,
            self.window.searchable_checkbox,
            self.window.judgment_analysis_checkbox,
            self.window.start_button,
            self.window.cancel_button,
            self.window.progress_bar,
            self.window.log_view,
        ):
            ancestor = widget.parent()
            while ancestor is not None and ancestor is not ocr_tab:
                ancestor = ancestor.parent()
            self.assertIs(
                ancestor,
                ocr_tab,
                f"{widget.objectName() or type(widget).__name__} "
                f"is not inside ocr_tab",
            )

    def test_casefile_controls_are_in_casefile_tab(self) -> None:
        casefile_tab = self.window.casefile_tab
        self.assertIsNotNone(casefile_tab)
        for widget in (
            self.window.casefile_input_edit,
            self.window.casefile_output_edit,
            self.window.casefile_start_button,
            self.window.casefile_log_view,
        ):
            ancestor = widget.parent()
            while ancestor is not None and ancestor is not casefile_tab:
                ancestor = ancestor.parent()
            self.assertIs(
                ancestor,
                casefile_tab,
                f"{widget.objectName() or type(widget).__name__} "
                f"is not inside casefile_tab",
            )

    def test_casefile_gui_does_not_overlap_by_layout_structure(self) -> None:
        ocr_tab = self.window.ocr_tab
        casefile_tab = self.window.casefile_tab
        self.assertIsNot(ocr_tab, casefile_tab)

        casefile_ancestor = self.window.casefile_input_edit.parent()
        while casefile_ancestor is not None and casefile_ancestor is not ocr_tab:
            casefile_ancestor = casefile_ancestor.parent()
        self.assertIsNone(
            casefile_ancestor if casefile_ancestor is not ocr_tab else None,
            "Casefile controls must not share layout with OCR tab",
        )

    def test_judgment_checkbox_still_exists(self) -> None:
        cb = self.window.judgment_analysis_checkbox
        self.assertIsNotNone(cb)
        self.assertEqual("Analisi sentenza per impugnazione", cb.text())
        self.assertFalse(cb.isChecked())

    def test_no_casefile_input_path_saved_in_qsettings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
            window = MainWindow(settings=settings)

            window.casefile_input_edit.setText("/secret/fascicolo")
            window.casefile_output_edit.setText("/secret/output")
            window._save_gui_settings()
            settings.sync()

            if settings_path.exists():
                saved_text = settings_path.read_text(encoding="utf-8")
                self.assertNotIn("/secret/fascicolo", saved_text)
                self.assertNotIn("/secret/output", saved_text)

            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_casefile_tab_has_dedicated_log(self) -> None:
        self.assertIsNotNone(self.window.casefile_log_view)
        self.assertTrue(self.window.casefile_log_view.isReadOnly())
        self.assertIsNot(self.window.casefile_log_view, self.window.log_view)

    def test_casefile_log_receives_analysis_messages(self) -> None:
        self.window._append_casefile_log("test message")
        text = self.window.casefile_log_view.toPlainText()
        self.assertIn("test message", text)
        ocr_text = self.window.log_view.toPlainText()
        self.assertNotIn("test message", ocr_text)

    def test_stable_object_names(self) -> None:
        self.assertEqual("mainTabs", self.window.main_tabs.objectName())
        self.assertEqual("ocrTab", self.window.ocr_tab.objectName())
        self.assertEqual("casefileTab", self.window.casefile_tab.objectName())
        self.assertEqual(
            "casefileInputEdit",
            self.window.casefile_input_edit.objectName(),
        )
        self.assertEqual(
            "casefileOutputEdit",
            self.window.casefile_output_edit.objectName(),
        )
        self.assertEqual(
            "casefileAnalyzeButton",
            self.window.casefile_start_button.objectName(),
        )
        self.assertEqual(
            "judgmentAnalysisCheckbox",
            self.window.judgment_analysis_checkbox.objectName(),
        )

    def test_tabs_use_scroll_areas(self) -> None:
        tabs = self.window.main_tabs
        for i in range(tabs.count()):
            widget = tabs.widget(i)
            self.assertIsInstance(
                widget,
                QScrollArea,
                f"Tab {i} ({tabs.tabText(i)}) is not wrapped in QScrollArea",
            )

    # ------------------------------------------------------------------
    # Tab styling tests
    # ------------------------------------------------------------------

    def test_main_tabs_object_name(self) -> None:
        self.assertEqual("mainTabs", self.window.main_tabs.objectName())

    def test_main_tab_labels(self) -> None:
        tabs = self.window.main_tabs
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertEqual(["OCR documento", "Fascicolo"], labels)

    def test_stylesheet_contains_tab_rules(self) -> None:
        apply_theme(self.app)
        sheet = self.app.styleSheet()
        self.assertIn("QTabBar::tab", sheet)
        self.assertIn("QTabBar::tab:selected", sheet)
        self.assertIn("QTabWidget::pane", sheet)

    def test_sub_tabs_exist(self) -> None:
        tabs = self.window.pdf_output_tabs
        labels = [tabs.tabText(i) for i in range(tabs.count())]
        self.assertIn("Base", labels)
        self.assertIn("Backend OCR", labels)

    def test_key_widgets_still_exist(self) -> None:
        self.assertIsNotNone(self.window.casefile_tab)
        self.assertIsNotNone(self.window.ocr_tab)
        self.assertIsNotNone(self.window.judgment_analysis_checkbox)
        self.assertIsNotNone(self.window.casefile_start_button)
        self.assertEqual(
            "casefileAnalyzeButton",
            self.window.casefile_start_button.objectName(),
        )
        self.assertEqual(
            "judgmentAnalysisCheckbox",
            self.window.judgment_analysis_checkbox.objectName(),
        )


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
            self.assertIsInstance(result.total_index_matches, int)
            self.assertIsInstance(result.total_units, int)
            self.assertIsInstance(result.total_warnings, int)
            self.assertTrue(result.json_path.is_file())
            self.assertTrue(result.markdown_path.is_file())
            self.assertTrue(result.csv_path.is_file())
            self.assertTrue(result.units_csv_path.is_file())
            self.assertEqual("fascicolo_index.json", result.json_path.name)
            self.assertEqual("fascicolo_index.md", result.markdown_path.name)
            self.assertEqual("fascicolo_index.csv", result.csv_path.name)
            self.assertEqual("fascicolo_unita.csv", result.units_csv_path.name)

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
