"""GD LEX OCR application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("GD LEX OCR")
    app.setOrganizationName("GD LEX")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
