"""Headless tests for GUI settings persistence."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow


class GuiSettingsPersistenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _settings(self, path: Path) -> QSettings:
        return QSettings(str(path), QSettings.Format.IniFormat)

    def _close_window(self, window: MainWindow) -> None:
        window.close()
        window.deleteLater()
        self.app.processEvents()

    def test_restores_saved_gui_options_without_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            output_dir = Path(tmpdir) / "gdlex-output"
            sensitive_pdf = Path(tmpdir) / "sensitive" / "fascicolo.pdf"
            settings = self._settings(settings_path)
            settings.setValue("paths/outputDirectory", str(output_dir))
            settings.setValue("processing/profile", "Accurato testo")
            settings.setValue("processing/blockSize", 42)
            settings.setValue("pdf/createSearchable", True)
            settings.setValue("pdf/useSearchableAsSource", True)
            settings.setValue("output/structuredJobDirectory", True)
            settings.setValue("ocr/language", "eng")
            settings.setValue("ocr/backend", "external")
            settings.setValue(
                "ocr/externalCommand",
                "local-ocr {input} {output} --lang {language}",
            )
            settings.setValue("paths/inputPdf", str(sensitive_pdf))
            settings.sync()

            window = MainWindow(settings=self._settings(settings_path))

            self.assertEqual("", window.pdf_edit.text())
            self.assertEqual(str(output_dir), window.output_edit.text())
            self.assertEqual("Accurato testo", window.profile_combo.currentText())
            self.assertEqual(42, window.block_size_spin.value())
            self.assertTrue(window.searchable_checkbox.isChecked())
            self.assertTrue(window.use_searchable_as_source_checkbox.isChecked())
            self.assertTrue(window.structured_output_checkbox.isChecked())
            self.assertEqual("eng", window.ocr_language_combo.currentData())
            self.assertEqual("external", window.ocr_backend_combo.currentData())
            self.assertTrue(window.external_ocr_command_edit.isEnabled())
            self.assertEqual(
                "local-ocr {input} {output} --lang {language}",
                window.external_ocr_command_edit.text(),
            )

            self._close_window(window)

    def test_saves_relevant_options_and_never_saves_pdf_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            output_dir = Path(tmpdir) / "gdlex-output"
            sensitive_pdf = Path(tmpdir) / "sensitive" / "fascicolo.pdf"
            settings = self._settings(settings_path)
            window = MainWindow(settings=settings)

            window.pdf_edit.setText(str(sensitive_pdf))
            window.output_edit.setText(str(output_dir))
            window.output_edit.textEdited.emit(str(output_dir))
            window.profile_combo.setCurrentText("PDF già ricercabile")
            window.block_size_spin.setValue(33)
            window.searchable_checkbox.setChecked(True)
            window.use_searchable_as_source_checkbox.setChecked(True)
            window.structured_output_checkbox.setChecked(True)
            window.ocr_language_combo.setCurrentIndex(
                window.ocr_language_combo.findData("fra")
            )
            window.ocr_backend_combo.setCurrentIndex(
                window.ocr_backend_combo.findData("ocrmypdf")
            )
            window.external_ocr_command_edit.setText("")
            window.close()
            settings.sync()

            saved = self._settings(settings_path)
            self.assertEqual(
                str(output_dir),
                saved.value("paths/outputDirectory"),
            )
            self.assertEqual("PDF già ricercabile", saved.value("processing/profile"))
            self.assertEqual(33, int(saved.value("processing/blockSize")))
            self.assertTrue(saved.value("pdf/createSearchable", type=bool))
            self.assertTrue(saved.value("pdf/useSearchableAsSource", type=bool))
            self.assertTrue(saved.value("output/structuredJobDirectory", type=bool))
            self.assertEqual("fra", saved.value("ocr/language"))
            self.assertEqual("ocrmypdf", saved.value("ocr/backend"))
            self.assertFalse(saved.contains("paths/inputPdf"))
            self.assertNotIn(
                "fascicolo.pdf",
                settings_path.read_text(encoding="utf-8"),
            )

            window.deleteLater()
            self.app.processEvents()

    def test_does_not_save_auto_derived_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            sensitive_parent = Path(tmpdir) / "sensitive"
            settings = self._settings(settings_path)
            window = MainWindow(settings=settings)

            window.pdf_edit.setText(str(sensitive_parent / "fascicolo.pdf"))
            window.output_edit.setText(str(sensitive_parent))
            window._output_path_customized = False
            window.close()
            settings.sync()

            saved = self._settings(settings_path)
            self.assertFalse(saved.contains("paths/outputDirectory"))
            self.assertNotIn(
                "sensitive",
                settings_path.read_text(encoding="utf-8"),
            )

            window.deleteLater()
            self.app.processEvents()

    def test_ignores_missing_or_unavailable_saved_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.ini"
            settings = self._settings(settings_path)
            settings.setValue("processing/profile", "Accurato testo")
            settings.setValue("processing/blockSize", "not-an-integer")
            settings.setValue("pdf/createSearchable", "not-a-bool")
            settings.setValue("ocr/language", "zzz")
            settings.setValue("ocr/backend", "removed-backend")
            settings.sync()

            window = MainWindow(settings=self._settings(settings_path))

            self.assertEqual("Accurato testo", window.profile_combo.currentText())
            self.assertEqual(10, window.block_size_spin.value())
            self.assertTrue(window.searchable_checkbox.isChecked())
            self.assertEqual("ita", window.ocr_language_combo.currentData())
            self.assertEqual("auto", window.ocr_backend_combo.currentData())

            self._close_window(window)


if __name__ == "__main__":
    unittest.main()
