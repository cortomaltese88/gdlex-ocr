"""System tray helper for the GD LEX OCR Qt GUI."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from gdlex_ocr.version import APP_NAME


class GdlexOcrTray:
    """Small QSystemTrayIcon wrapper that stays inert when unsupported."""

    def __init__(
        self,
        parent: QWidget,
        *,
        icon: QIcon,
        toggle_window: Callable[[], None],
        show_window: Callable[[], None],
        open_output_folder: Callable[[], None],
        quit_app: Callable[[], None],
    ) -> None:
        self.tray_icon: QSystemTrayIcon | None = None
        self.menu: QMenu | None = None
        self.toggle_action: QAction | None = None
        self.open_output_action: QAction | None = None
        self.exit_action: QAction | None = None
        self._show_window = show_window
        self._icon = QIcon(icon)

        if self._icon.isNull() or not self.is_system_tray_available():
            return

        self.tray_icon = QSystemTrayIcon(self._icon, parent)
        self.tray_icon.setIcon(self._icon)
        self.tray_icon.setToolTip(APP_NAME)
        self.tray_icon.activated.connect(self._on_activated)

        self.menu = QMenu(parent)
        self.toggle_action = QAction("Mostra/Nascondi", parent)
        self.open_output_action = QAction("Apri cartella output", parent)
        self.exit_action = QAction("Esci", parent)

        self.toggle_action.triggered.connect(toggle_window)
        self.open_output_action.triggered.connect(open_output_folder)
        self.exit_action.triggered.connect(quit_app)

        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()
        self.menu.addAction(self.open_output_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    @staticmethod
    def is_system_tray_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def is_available(self) -> bool:
        return self.tray_icon is not None

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.showMessage(title, message, icon, 3500)
        except Exception:
            pass

    def cleanup(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.hide()
                self.tray_icon.setContextMenu(None)
            except Exception:
                pass
            self.tray_icon.deleteLater()
            self.tray_icon = None
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()
