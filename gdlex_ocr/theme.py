"""Matrix-inspired visual theme for the GD LEX desktop interface."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


BACKGROUND = "#070b09"
PANEL = "#0b120e"
PANEL_RAISED = "#101a14"
INPUT_BACKGROUND = "#050806"
GREEN = "#32e875"
GREEN_BRIGHT = "#7dffa8"
GREEN_MUTED = "#78a989"
GREEN_DARK = "#173d25"
BORDER = "#245535"
TEXT = "#d8f3df"
TEXT_MUTED = "#8aaa93"
WARNING = "#f0b45a"


STYLE_SHEET = f"""
QWidget {{
    color: {TEXT};
    background-color: {BACKGROUND};
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: {BACKGROUND};
}}

QLabel {{
    background: transparent;
}}

QLabel#appTitle {{
    color: {GREEN_BRIGHT};
    font-size: 24pt;
    font-weight: 700;
    letter-spacing: 2px;
}}

QLabel#appSubtitle {{
    color: {TEXT_MUTED};
    font-size: 10.5pt;
}}

QLabel#versionBadge {{
    color: {GREEN};
    background-color: {GREEN_DARK};
    border: 1px solid {BORDER};
    border-radius: 11px;
    padding: 4px 10px;
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}}

QLabel#sectionHint {{
    color: {TEXT_MUTED};
}}

QLabel#statusLabel {{
    color: {GREEN_BRIGHT};
    font-weight: 600;
}}

QLabel#etaLabel {{
    color: {GREEN_MUTED};
    font-family: "DejaVu Sans Mono", monospace;
}}

QFrame#headerFrame {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-left: 4px solid {GREEN};
    border-radius: 7px;
}}

QGroupBox {{
    color: {GREEN_BRIGHT};
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 7px;
    font-weight: 600;
    margin-top: 12px;
    padding-top: 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: {PANEL};
}}

QLineEdit, QSpinBox, QTextEdit {{
    color: {TEXT};
    background-color: {INPUT_BACKGROUND};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 9px;
    selection-color: {BACKGROUND};
    selection-background-color: {GREEN};
}}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border-color: {GREEN};
}}

QLineEdit:disabled, QSpinBox:disabled {{
    color: {TEXT_MUTED};
    background-color: {PANEL};
}}

QLineEdit[readOnly="true"] {{
    color: {TEXT};
}}

QSpinBox {{
    padding-right: 24px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    background-color: {PANEL_RAISED};
    border-left: 1px solid {BORDER};
}}

QPushButton {{
    color: {GREEN_BRIGHT};
    background-color: {PANEL_RAISED};
    border: 1px solid {BORDER};
    border-radius: 5px;
    min-height: 20px;
    padding: 7px 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    color: #ffffff;
    background-color: {GREEN_DARK};
    border-color: {GREEN};
}}

QPushButton:pressed {{
    background-color: #102c1a;
}}

QPushButton:disabled {{
    color: #526459;
    background-color: #0b100d;
    border-color: #1b2b21;
}}

QPushButton#primaryButton {{
    color: {BACKGROUND};
    background-color: {GREEN};
    border-color: {GREEN_BRIGHT};
    min-width: 100px;
}}

QPushButton#primaryButton:hover {{
    background-color: {GREEN_BRIGHT};
}}

QPushButton#cancelButton {{
    min-width: 100px;
}}

QProgressBar {{
    color: {TEXT};
    background-color: {INPUT_BACKGROUND};
    border: 1px solid {BORDER};
    border-radius: 6px;
    min-height: 22px;
    text-align: center;
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}}

QProgressBar::chunk {{
    background-color: {GREEN};
    border-radius: 5px;
}}

QTextEdit#logView {{
    color: #a7e8b9;
    background-color: #030604;
    border-color: {BORDER};
    font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
    font-size: 9.5pt;
}}

QScrollBar:vertical {{
    background: {INPUT_BACKGROUND};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {GREEN_DARK};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QToolTip {{
    color: {TEXT};
    background-color: {PANEL_RAISED};
    border: 1px solid {GREEN};
    padding: 4px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the application palette and shared widget stylesheet."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(INPUT_BACKGROUND))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL_RAISED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(PANEL_RAISED))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(GREEN_BRIGHT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(GREEN))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(BACKGROUND))
    app.setPalette(palette)
    app.setStyleSheet(STYLE_SHEET)
