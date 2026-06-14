"""GD LEX OCR application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow
from gdlex_ocr.splash import create_splash
from gdlex_ocr.theme import apply_theme
from gdlex_ocr.version import APP_NAME, APP_VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GD LEX")
    apply_theme(app)

    window = MainWindow()
    splash = create_splash()
    splash.show()

    def show_main_window() -> None:
        window.show()
        splash.finish(window)

    QTimer.singleShot(1200, show_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
