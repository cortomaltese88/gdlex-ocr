"""GD LEX OCR application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow
from gdlex_ocr.splash import SPLASH_DURATION_MS, create_splash
from gdlex_ocr.theme import apply_theme, load_theme_name
from gdlex_ocr.version import APP_NAME, APP_VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GD LEX")
    apply_theme(app, load_theme_name())

    window = MainWindow()
    splash = create_splash()
    splash.show()

    def show_main_window() -> None:
        splash.close()
        window.show()

    QTimer.singleShot(SPLASH_DURATION_MS, show_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
