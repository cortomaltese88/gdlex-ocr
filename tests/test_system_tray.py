"""Headless checks for GD LEX OCR system tray integration."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from gdlex_ocr.gui import MainWindow
from gdlex_ocr.tray import GdlexOcrTray


class FakeCloseEvent:
    def __init__(self) -> None:
        self.accepted = False
        self.ignored = False

    def accept(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True


class SystemTrayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        self.app.setQuitOnLastWindowClosed(True)
        self.app.processEvents()

    def test_tray_menu_contains_required_actions(self) -> None:
        with (
            patch.object(
                GdlexOcrTray,
                "is_system_tray_available",
                return_value=True,
            ),
            patch("gdlex_ocr.tray.QSystemTrayIcon") as tray_icon_class,
        ):
            parent = QWidget()
            tray = GdlexOcrTray(
                parent,
                icon=QIcon(),
                toggle_window=lambda: None,
                show_window=lambda: None,
                open_output_folder=lambda: None,
                quit_app=lambda: None,
            )

        self.assertTrue(tray.is_available())
        tray_icon_class.return_value.setToolTip.assert_called_once_with(
            "GD LEX OCR"
        )
        self.assertEqual("Mostra/Nascondi", tray.toggle_action.text())
        self.assertEqual("Apri cartella output", tray.open_output_action.text())
        self.assertEqual("Esci", tray.exit_action.text())
        tray.cleanup()
        parent.deleteLater()

    def test_main_window_initializes_available_tray_without_crashing(self) -> None:
        fake_tray = MagicMock()
        fake_tray.is_available.return_value = True

        with (
            patch("gdlex_ocr.gui._tray_enabled", return_value=True),
            patch("gdlex_ocr.gui.GdlexOcrTray", return_value=fake_tray) as tray_cls,
        ):
            window = MainWindow()

        tray_cls.assert_called_once()
        tray_icon = tray_cls.call_args.kwargs["icon"]
        self.assertFalse(tray_icon.isNull())
        self.assertIn(QSize(64, 64), tray_icon.availableSizes())
        self.assertIs(fake_tray, window.tray)
        self.assertFalse(self.app.quitOnLastWindowClosed())
        window.tray = None
        window.deleteLater()

    def test_close_during_processing_hides_to_available_tray(self) -> None:
        window = MainWindow()
        worker = MagicMock()
        worker.isRunning.return_value = True
        window._worker = worker
        window.tray = MagicMock()
        window.tray.is_available.return_value = True
        window.show()

        event = FakeCloseEvent()
        window.closeEvent(event)

        self.assertTrue(event.ignored)
        self.assertFalse(event.accepted)
        self.assertFalse(window.isVisible())
        worker.request_cancel.assert_not_called()
        window.tray.show_message.assert_called_once()
        window._worker = None
        window.tray = None
        window.deleteLater()

    def test_close_without_tray_keeps_normal_idle_behavior(self) -> None:
        window = MainWindow()
        self.assertIsNone(window.tray)

        event = FakeCloseEvent()
        window.closeEvent(event)

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)
        window.deleteLater()

    def test_close_during_processing_without_tray_keeps_cancel_prompt(self) -> None:
        window = MainWindow()
        worker = MagicMock()
        worker.isRunning.return_value = True
        window._worker = worker
        event = FakeCloseEvent()

        with patch(
            "gdlex_ocr.gui.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ) as question:
            window.closeEvent(event)

        question.assert_called_once()
        self.assertTrue(event.ignored)
        self.assertFalse(event.accepted)
        worker.request_cancel.assert_not_called()
        window._worker = None
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
