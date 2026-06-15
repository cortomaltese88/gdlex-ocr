#!/usr/bin/env python3
"""Capture diagnostic GUI screenshots without starting OCR."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("GDLEX_OCR_DISABLE_TRAY", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from gdlex_ocr.gui import MainWindow
from gdlex_ocr.theme import apply_theme


def main() -> int:
    output_dir = Path(
        os.environ.get(
            "GDLEX_OCR_GUI_SCREENSHOT_DIR",
            "/tmp/gdlex-ocr-gui-screenshots",
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    apply_theme(app, os.environ.get("GDLEX_OCR_GUI_THEME", "Matrix"))

    window = MainWindow()
    window.resize(1020, 780)
    window.show()
    app.processEvents()

    captures = (
        ("base.png", window.pdf_output_base_tab),
        ("backend_ocr.png", window.pdf_output_backend_tab),
    )
    for filename, tab in captures:
        window.pdf_output_tabs.setCurrentWidget(tab)
        app.processEvents()
        path = output_dir / filename
        if not window.grab().save(str(path)):
            raise RuntimeError(f"Impossibile salvare lo screenshot: {path}")
        print(path)

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
