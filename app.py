"""GD LEX OCR application entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow
from gdlex_ocr.icons import application_icon
from gdlex_ocr.splash import (
    SPLASH_DURATION_MS,
    create_splash,
    splash_disabled,
)
from gdlex_ocr.theme import apply_theme, load_theme_name
from gdlex_ocr.version import APP_NAME, APP_VERSION


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gdlex-ocr")
    parser.add_argument(
        "--version",
        action="store_true",
        help="stampa la versione ed esce",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="rimanda alla diagnostica del launcher installato ed esce",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    cli_args = sys.argv[1:] if argv is None else argv
    args = parse_args(cli_args)

    if args.version:
        print(APP_VERSION)
        return 0

    if args.doctor:
        print(
            "La diagnostica completa è disponibile dal launcher installato:\n"
            "  gdlex-ocr --doctor"
        )
        return 0

    app = QApplication([sys.argv[0], *cli_args])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GD LEX")
    app.setDesktopFileName("gdlex-ocr")
    icon = application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    apply_theme(app, load_theme_name())

    window = MainWindow()
    if splash_disabled():
        window.show()
    else:
        splash = create_splash()
        splash.show()

        def show_main_window() -> None:
            splash.close()
            window.show()

        QTimer.singleShot(SPLASH_DURATION_MS, show_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
