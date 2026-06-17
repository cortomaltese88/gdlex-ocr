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
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
    QPushButton,
    QTabWidget,
    QWidget,
)

from gdlex_ocr.gui import MainWindow, resolve_output_path, resolve_pdf_path
from gdlex_ocr.theme import apply_theme


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
        self.app.setStyleSheet("")

    def test_output_field_is_editable_with_clear_placeholder(self) -> None:
        self.assertFalse(self.window.output_edit.isReadOnly())
        self.assertIn("incolla", self.window.output_edit.placeholderText())

    def test_pdf_and_output_checkboxes_are_unchecked_by_default(self) -> None:
        searchable = self.window.searchable_checkbox
        structured = self.window.structured_output_checkbox

        self.assertEqual("Crea PDF ricercabile OCR", searchable.text())
        self.assertFalse(searchable.isChecked())
        self.assertEqual(
            "Crea cartella fascicolo per ogni elaborazione",
            structured.text(),
        )
        self.assertFalse(structured.isChecked())
        self.assertIn("sottocartella dedicata", structured.toolTip())

    def test_pdf_output_group_contains_base_and_backend_tabs(self) -> None:
        group = self.window.pdf_output_group
        tabs = group.findChild(QTabWidget)

        self.assertIsInstance(group, QGroupBox)
        self.assertEqual("PDF e output", group.title())
        self.assertIs(tabs, self.window.pdf_output_tabs)
        self.assertEqual(2, tabs.count())
        self.assertEqual(
            ["Base", "Backend OCR"],
            [tabs.tabText(index) for index in range(tabs.count())],
        )

    def test_pdf_output_controls_are_in_the_expected_tabs(self) -> None:
        base_tab = self.window.pdf_output_base_tab
        backend_tab = self.window.pdf_output_backend_tab

        for widget in (
            self.window.searchable_checkbox,
            self.window.ocr_language_combo,
            self.window.use_searchable_as_source_checkbox,
            self.window.structured_output_checkbox,
        ):
            self.assertIs(widget.parentWidget(), base_tab)

        for widget in (
            self.window.ocr_backend_combo,
            self.window.ocr_timeout_spin,
            self.window.ocr_jobs_edit,
            self.window.external_ocr_command_edit,
        ):
            self.assertIs(widget.parentWidget(), backend_tab)

    def test_external_command_does_not_occupy_space_in_base_tab(self) -> None:
        tabs = self.window.pdf_output_tabs
        tabs.setCurrentWidget(self.window.pdf_output_base_tab)
        self.window.show()
        self.app.processEvents()

        self.assertTrue(self.window.pdf_output_base_tab.isVisible())
        self.assertFalse(self.window.pdf_output_backend_tab.isVisible())
        self.assertFalse(self.window.external_ocr_command_edit.isVisible())

    def test_pdf_output_tabs_keep_controls_visible_without_overlap(self) -> None:
        apply_theme(self.app, "Matrix")
        tabs = self.window.pdf_output_tabs
        self.window.resize(1020, 780)
        self.window.show()

        tabs.setCurrentWidget(self.window.pdf_output_base_tab)
        self.app.processEvents()
        base_controls = (
            self.window.searchable_checkbox,
            self.window.ocr_language_label,
            self.window.ocr_language_combo,
            self.window.use_searchable_as_source_checkbox,
            self.window.structured_output_checkbox,
        )
        self._assert_widgets_fit_tab(
            self.window.pdf_output_base_tab,
            base_controls,
        )
        self._assert_rows_do_not_overlap(
            (
                (
                    self.window.searchable_checkbox,
                    self.window.ocr_language_label,
                    self.window.ocr_language_combo,
                ),
                (
                    self.window.use_searchable_as_source_checkbox,
                    self.window.structured_output_checkbox,
                ),
            )
        )

        tabs.setCurrentWidget(self.window.pdf_output_backend_tab)
        self.app.processEvents()
        backend_controls = (
            self.window.ocr_backend_label,
            self.window.ocr_backend_combo,
            self.window.ocr_timeout_label,
            self.window.ocr_timeout_spin,
            self.window.ocr_jobs_label,
            self.window.ocr_jobs_edit,
            self.window.external_ocr_command_label,
            self.window.external_ocr_command_edit,
        )
        self._assert_widgets_fit_tab(
            self.window.pdf_output_backend_tab,
            backend_controls,
        )
        self._assert_rows_do_not_overlap(
            (
                (
                    self.window.ocr_backend_label,
                    self.window.ocr_backend_combo,
                ),
                (
                    self.window.ocr_timeout_label,
                    self.window.ocr_timeout_spin,
                    self.window.ocr_jobs_label,
                    self.window.ocr_jobs_edit,
                ),
                (
                    self.window.external_ocr_command_label,
                    self.window.external_ocr_command_edit,
                ),
            )
        )
        self.assertGreaterEqual(self.window.external_ocr_command_edit.width(), 600)

    def _assert_widgets_fit_tab(
        self,
        tab: QWidget,
        widgets: tuple[QWidget, ...],
    ) -> None:
        for widget in widgets:
            widget_name = widget.objectName() or widget.__class__.__name__
            with self.subTest(widget=widget_name):
                self.assertTrue(widget.isVisible())
                self.assertGreaterEqual(
                    widget.height(),
                    widget.fontMetrics().height(),
                )
                self.assertLessEqual(
                    widget.geometry().bottom(),
                    tab.rect().bottom(),
                )

    def _assert_rows_do_not_overlap(
        self,
        rows: tuple[tuple[QWidget, ...], ...],
    ) -> None:
        for upper_row, lower_row in zip(rows, rows[1:]):
            self.assertLess(
                max(widget.geometry().bottom() for widget in upper_row),
                min(widget.geometry().top() for widget in lower_row),
            )

    def test_pdf_output_group_does_not_overlap_progress_at_minimum_size(self) -> None:
        apply_theme(self.app, "Matrix")
        self.window.resize(1020, 780)
        self.window.show()
        self.app.processEvents()

        self.assertLess(
            self.window.pdf_output_group.geometry().bottom(),
            self.window.progress_group.geometry().top(),
        )

    def test_main_window_has_reasonable_minimum_size(self) -> None:
        minimum = self.window.minimumSize()

        self.assertGreaterEqual(minimum.width(), 900)
        self.assertLessEqual(minimum.width(), 1100)
        self.assertGreaterEqual(minimum.height(), 700)
        self.assertLessEqual(minimum.height(), 900)

    def test_pdf_output_controls_keep_running_state_behavior(self) -> None:
        self.assertFalse(self.window.ocr_language_combo.isEnabled())
        self.assertFalse(self.window.ocr_backend_combo.isEnabled())

        self.window.searchable_checkbox.setChecked(True)
        self.assertTrue(self.window.ocr_language_combo.isEnabled())
        self.assertTrue(self.window.ocr_backend_combo.isEnabled())
        self.assertTrue(
            self.window.use_searchable_as_source_checkbox.isEnabled()
        )

        self.window._set_running(True)
        self.assertFalse(self.window.searchable_checkbox.isEnabled())
        self.assertFalse(self.window.structured_output_checkbox.isEnabled())
        self.assertFalse(self.window.ocr_language_combo.isEnabled())
        self.assertFalse(self.window.ocr_backend_combo.isEnabled())
        self.assertFalse(self.window.external_ocr_command_edit.isEnabled())

        self.window._set_running(False)
        self.assertTrue(self.window.searchable_checkbox.isEnabled())
        self.assertTrue(self.window.structured_output_checkbox.isEnabled())
        self.assertTrue(self.window.ocr_language_combo.isEnabled())
        self.assertTrue(self.window.ocr_backend_combo.isEnabled())

        external_index = self.window.ocr_backend_combo.findData("external")
        self.window.ocr_backend_combo.setCurrentIndex(external_index)
        self.assertTrue(self.window.external_ocr_command_edit.isEnabled())
        self.window._set_running(True)
        self.assertFalse(self.window.external_ocr_command_edit.isEnabled())

    def test_external_backend_controls_and_worker_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "fascicolo.pdf"
            pdf_path.touch()
            self.window.pdf_edit.setText(str(pdf_path))
            self.window.output_edit.setText(str(Path(tmpdir) / "output"))
            self.window.searchable_checkbox.setChecked(True)
            external_index = self.window.ocr_backend_combo.findData("external")
            self.window.ocr_backend_combo.setCurrentIndex(external_index)
            command = "local-ocr {input} {output} --lang {language}"
            self.window.external_ocr_command_edit.setText(command)
            self.window.ocr_timeout_spin.setValue(77)
            self.window.ocr_jobs_edit.setText("5")
            self.window.use_searchable_as_source_checkbox.setChecked(True)
            worker = MagicMock()
            worker.isRunning.return_value = False

            with (
                patch("gdlex_ocr.gui.count_pdf_pages", return_value=3),
                patch("gdlex_ocr.gui.detect_ocr_backend") as detect,
                patch("gdlex_ocr.gui.OcrWorker", return_value=worker) as worker_cls,
            ):
                detect.return_value.runnable = True
                detect.return_value.warnings = ()
                self.window._start()

            kwargs = worker_cls.call_args.kwargs
            self.assertEqual("external", kwargs["ocr_backend"])
            self.assertEqual(command, kwargs["external_ocr_command"])
            self.assertEqual(77, kwargs["ocr_timeout_seconds"])
            self.assertEqual(5, kwargs["ocr_jobs"])
            self.assertTrue(kwargs["use_searchable_as_source"])
            worker.start.assert_called_once_with()

    def test_action_buttons_use_separate_output_and_run_rows(self) -> None:
        output_buttons = [
            self.window.open_folder_button,
            self.window.open_markdown_button,
            self.window.open_pdf_button,
            self.window.open_manifest_button,
            self.window.open_log_button,
            self.window.verify_outputs_button,
        ]
        run_buttons = [
            self.window.start_button,
            self.window.cancel_button,
        ]

        self.window.resize(self.window.minimumSize())
        self.window.show()
        self.app.processEvents()

        self.assertTrue(
            all(isinstance(button, QPushButton) for button in output_buttons)
        )
        self.assertTrue(
            all(isinstance(button, QPushButton) for button in run_buttons)
        )
        self.assertEqual(1, len({button.geometry().top() for button in output_buttons}))
        self.assertEqual(1, len({button.geometry().top() for button in run_buttons}))
        self.assertLess(
            output_buttons[0].geometry().top(),
            run_buttons[0].geometry().top(),
        )

        for row in (output_buttons, run_buttons):
            ordered = sorted(row, key=lambda button: button.geometry().left())
            for left_button, right_button in zip(ordered, ordered[1:]):
                self.assertLess(
                    left_button.geometry().right(),
                    right_button.geometry().left(),
                )

    def test_manual_output_path_survives_pdf_selection(self) -> None:
        manual_path = "/tmp/output-personalizzato"
        self.window.output_edit.setText(manual_path)
        self.window.output_edit.textEdited.emit(manual_path)
        dialog = MagicMock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.selectedFiles.return_value = ["/tmp/documenti/fascicolo.pdf"]

        with (
            patch("gdlex_ocr.gui._themed_file_dialog", return_value=dialog),
            patch("gdlex_ocr.gui.count_pdf_pages", return_value=12),
        ):
            self.window._select_pdf()

        self.assertEqual(manual_path, self.window.output_edit.text())

    def test_pdf_selection_updates_only_an_unmodified_suggestion(self) -> None:
        dialogs = []
        for selected_file in (
            "/tmp/primo/fascicolo.pdf",
            "/tmp/secondo/fascicolo.pdf",
        ):
            dialog = MagicMock()
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            dialog.selectedFiles.return_value = [selected_file]
            dialogs.append(dialog)

        with (
            patch("gdlex_ocr.gui._themed_file_dialog", side_effect=dialogs),
            patch("gdlex_ocr.gui.count_pdf_pages", return_value=12),
        ):
            self.window._select_pdf()
            self.assertEqual("/tmp/primo", self.window.output_edit.text())
            self.window._select_pdf()

        self.assertEqual("/tmp/secondo", self.window.output_edit.text())

    def test_browse_updates_output_field(self) -> None:
        dialog = MagicMock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.selectedFiles.return_value = ["/tmp/output-da-browse"]

        with patch(
            "gdlex_ocr.gui._themed_file_dialog",
            return_value=dialog,
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
            self.assertFalse(worker_cls.call_args.kwargs["structured_output"])
            worker.start.assert_called_once_with()

    def test_accurate_text_profile_enables_searchable_checkbox(self) -> None:
        self.window.profile_combo.setCurrentText("Accurato testo")

        self.assertTrue(self.window.searchable_checkbox.isChecked())

    def test_accurate_text_profile_enables_use_searchable_as_source_checkbox(
        self,
    ) -> None:
        self.window.profile_combo.setCurrentText("Accurato testo")

        self.assertTrue(
            self.window.use_searchable_as_source_checkbox.isChecked()
        )
        self.assertTrue(
            self.window.use_searchable_as_source_checkbox.isEnabled()
        )

    def test_balanced_profile_leaves_searchable_checkbox_unchecked(self) -> None:
        self.window.profile_combo.setCurrentText("Accurato testo")
        self.window.profile_combo.setCurrentText("Bilanciato")

        self.assertFalse(self.window.searchable_checkbox.isChecked())

    def test_searchable_pdf_profile_does_not_set_use_searchable_as_source(
        self,
    ) -> None:
        self.window.profile_combo.setCurrentText("PDF già ricercabile")

        self.assertFalse(self.window.searchable_checkbox.isChecked())
        self.assertFalse(
            self.window.use_searchable_as_source_checkbox.isChecked()
        )

    def test_legal_dossier_profile_is_selectable_in_gui(self) -> None:
        self.assertNotEqual(
            -1,
            self.window.profile_combo.findText("Fascicolo legale"),
        )

        self.window.profile_combo.setCurrentText("Fascicolo legale")

        self.assertEqual(25, self.window.block_size_spin.value())
        self.assertFalse(self.window.searchable_checkbox.isChecked())
        self.assertFalse(
            self.window.use_searchable_as_source_checkbox.isChecked()
        )
        self.assertIn("accurate", self.window.profile_summary_label.text())

    def test_start_passes_structured_output_to_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "fascicolo.pdf"
            pdf_path.touch()
            self.window.pdf_edit.setText(str(pdf_path))
            self.window.output_edit.setText(str(Path(tmpdir) / "output"))
            self.window.structured_output_checkbox.setChecked(True)
            worker = MagicMock()
            worker.isRunning.return_value = False

            with (
                patch("gdlex_ocr.gui.count_pdf_pages", return_value=3),
                patch("gdlex_ocr.gui.OcrWorker", return_value=worker) as worker_cls,
            ):
                self.window._start()

            self.assertTrue(worker_cls.call_args.kwargs["structured_output"])
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
        dialog = MagicMock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.selectedFiles.return_value = [selected_path]

        with (
            patch("gdlex_ocr.gui._themed_file_dialog", return_value=dialog),
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


class OpenLocalPathsGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_gui_uses_qdesktopservices_instead_of_xdg_open(self) -> None:
        gui_source = (
            Path(__file__).resolve().parents[1] / "gdlex_ocr" / "gui.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("xdg-open", gui_source)
        self.assertIn("QDesktopServices.openUrl", gui_source)

    def test_log_and_verification_buttons_start_disabled(self) -> None:
        self.assertEqual("Apri log", self.window.open_log_button.text())
        self.assertFalse(self.window.open_log_button.isEnabled())
        self.assertEqual(
            "Verifica output",
            self.window.verify_outputs_button.text(),
        )
        self.assertFalse(self.window.verify_outputs_button.isEnabled())

    def test_existing_log_enables_button(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "run.log"
            log_path.touch()
            self.window.output_edit.setText(tmpdir)

            self.window._enable_log_button()

        self.assertTrue(self.window.open_log_button.isEnabled())
        self.assertEqual(str(log_path), self.window._log_path)

    def test_open_log_uses_shared_local_path_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "run.log"
            log_path.touch()
            self.window._log_path = str(log_path)

            with patch.object(self.window, "_open_local_path") as open_path:
                self.window._open_log()

        open_path.assert_called_once_with(
            log_path,
            "Impossibile aprire il file",
            "Errore durante l'apertura del log.",
        )

    def test_existing_manifest_enables_open_and_verify_buttons(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.touch()
            self.window.output_edit.setText(tmpdir)

            self.window._enable_manifest_button()

        self.assertTrue(self.window.open_manifest_button.isEnabled())
        self.assertTrue(self.window.verify_outputs_button.isEnabled())
        self.assertEqual(str(manifest_path), self.window._manifest_path)

    def test_structured_job_enables_its_log_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_root = Path(tmpdir)
            job_dir = output_root / "fascicolo_ocr_job"
            job_dir.mkdir()
            manifest_path = job_dir / "manifest.json"
            log_path = job_dir / "run.log"
            manifest_path.touch()
            log_path.touch()
            self.window.output_edit.setText(str(output_root))
            self.window._job_output_dir = str(job_dir)

            self.window._enable_manifest_button()
            self.window._enable_log_button()

        self.assertEqual(str(manifest_path), self.window._manifest_path)
        self.assertEqual(str(log_path), self.window._log_path)
        self.assertTrue(self.window.open_manifest_button.isEnabled())
        self.assertTrue(self.window.open_log_button.isEnabled())
        self.assertTrue(self.window.verify_outputs_button.isEnabled())

    def test_verify_outputs_shows_formatted_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.touch()
            self.window._manifest_path = str(manifest_path)

            with (
                patch(
                    "gdlex_ocr.gui.load_manifest",
                    return_value={"job": {"status": "success"}},
                ),
                patch(
                    "gdlex_ocr.gui.verify_manifest_outputs",
                    return_value={"checked": [], "missing": [], "warnings": []},
                ),
                patch(
                    "gdlex_ocr.gui.format_manifest_verification",
                    return_value="Output verificati: 3/3",
                ),
                patch("gdlex_ocr.gui.QMessageBox.information") as information,
            ):
                self.window._verify_outputs()

        information.assert_called_once_with(
            self.window,
            "Verifica output",
            "Output verificati: 3/3",
        )

    def test_open_output_folder_uses_local_file_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.window.output_edit.setText(tmpdir)

            with patch(
                "gdlex_ocr.gui.QDesktopServices.openUrl",
                return_value=True,
            ) as open_url:
                self.window._open_output_folder()

        opened_url = open_url.call_args.args[0]
        self.assertTrue(opened_url.isLocalFile())
        self.assertEqual(tmpdir, opened_url.toLocalFile())

    def test_open_output_folder_prefers_structured_job_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = Path(tmpdir) / "fascicolo_ocr_job"
            job_dir.mkdir()
            self.window.output_edit.setText(tmpdir)
            self.window._job_output_dir = str(job_dir)

            with patch(
                "gdlex_ocr.gui.QDesktopServices.openUrl",
                return_value=True,
            ) as open_url:
                self.window._open_output_folder()

        self.assertEqual(str(job_dir), open_url.call_args.args[0].toLocalFile())

    def test_open_markdown_reports_open_url_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            markdown_path = Path(tmpdir) / "risultato.md"
            markdown_path.touch()
            self.window._final_markdown_path = str(markdown_path)

            with (
                patch(
                    "gdlex_ocr.gui.QDesktopServices.openUrl",
                    return_value=False,
                ) as open_url,
                patch("gdlex_ocr.gui.QMessageBox.critical") as critical,
            ):
                self.window._open_markdown()

        opened_url = open_url.call_args.args[0]
        self.assertEqual(str(markdown_path), opened_url.toLocalFile())
        critical.assert_called_once_with(
            self.window,
            "Impossibile aprire il file",
            "Errore durante l'apertura del file Markdown.",
        )

    def test_open_searchable_pdf_uses_local_file_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "ricercabile.pdf"
            pdf_path.touch()
            self.window._searchable_pdf_path = str(pdf_path)

            with patch(
                "gdlex_ocr.gui.QDesktopServices.openUrl",
                return_value=True,
            ) as open_url:
                self.window._open_searchable_pdf()

        opened_url = open_url.call_args.args[0]
        self.assertTrue(opened_url.isLocalFile())
        self.assertEqual(str(pdf_path), opened_url.toLocalFile())


class ResolveOutputFileGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_enable_log_button_noop_when_output_path_empty(self) -> None:
        self.window.output_edit.setText("")
        self.window._enable_log_button()
        self.assertFalse(self.window.open_log_button.isEnabled())

    def test_enable_manifest_button_noop_when_file_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.window.output_edit.setText(tmpdir)
            self.window._enable_manifest_button()
        self.assertFalse(self.window.open_manifest_button.isEnabled())
        self.assertFalse(self.window.verify_outputs_button.isEnabled())

    def test_resolve_existing_output_file_returns_none_for_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir) / "run.log"
            dir_path.mkdir()
            self.window.output_edit.setText(tmpdir)
            result = self.window._resolve_existing_output_file("run.log")
        self.assertIsNone(result)

    def test_resolve_existing_output_file_returns_path_for_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "run.log"
            log_path.touch()
            self.window.output_edit.setText(tmpdir)
            result = self.window._resolve_existing_output_file("run.log")
        self.assertEqual(log_path, result)

    def test_verify_outputs_shows_warning_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text("{invalid json", encoding="utf-8")
            self.window._manifest_path = str(manifest_path)

            with patch("gdlex_ocr.gui.QMessageBox.warning") as warning:
                self.window._verify_outputs()

        warning.assert_called_once()
        self.assertEqual("Manifest non leggibile", warning.call_args.args[1])

    def test_verify_outputs_shows_warning_on_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text("[1, 2, 3]", encoding="utf-8")
            self.window._manifest_path = str(manifest_path)

            with patch("gdlex_ocr.gui.QMessageBox.warning") as warning:
                self.window._verify_outputs()

        warning.assert_called_once()
        self.assertEqual("Manifest non leggibile", warning.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
