"""Application themes for the GD LEX desktop interface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


AVAILABLE_THEMES = ("Matrix", "Chiaro")
DEFAULT_THEME = "Matrix"

BACKGROUND = "#070b09"
PANEL = "#0b120e"
PANEL_RAISED = "#101a14"
INPUT_BACKGROUND = "#050806"
INPUT_SURFACE = "#101a14"
INPUT_SURFACE_HOVER = "#132219"
INPUT_BORDER = "#3d8152"
INPUT_BORDER_HOVER = "#62c982"
INPUT_DISABLED = "#0b110d"
GREEN = "#32e875"
GREEN_BRIGHT = "#7dffa8"
GREEN_MUTED = "#78a989"
GREEN_DARK = "#173d25"
BORDER = "#245535"
TEXT = "#d8f3df"
TEXT_MUTED = "#8aaa93"
WARNING = "#f0b45a"

_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
_ARROW_DOWN = (_ASSET_DIR / "matrix-arrow-down.svg").as_posix()
_ARROW_UP = (_ASSET_DIR / "matrix-arrow-up.svg").as_posix()


MATRIX_STYLE_SHEET = f"""
QWidget {{
    color: {TEXT};
    background-color: {BACKGROUND};
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: {BACKGROUND};
}}

QWidget#mainCanvas {{
    background-color: #030604;
}}

QFrame#appShell {{
    background-color: #080e0a;
    border: 2px solid #286a40;
    border-radius: 12px;
}}

QLabel {{
    background: transparent;
}}

QLabel#headerEyebrow {{
    color: {GREEN};
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 8pt;
    font-weight: 600;
    letter-spacing: 1px;
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

QLabel#headerMeta {{
    color: {GREEN_MUTED};
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 7.5pt;
    font-weight: 600;
    letter-spacing: 1px;
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
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #102016, stop: 0.55 {PANEL}, stop: 1 #0a100c
    );
    border: 1px solid #34754b;
    border-left: 5px solid {GREEN};
    border-radius: 8px;
}}

QFrame#headerDivider {{
    color: {BORDER};
    background-color: {BORDER};
    border: none;
    min-width: 1px;
    max-width: 1px;
    min-height: 42px;
}}

QGroupBox {{
    color: {GREEN_BRIGHT};
    background-color: {PANEL};
    border: 1px solid #2a5e3b;
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

QLineEdit, QComboBox, QAbstractSpinBox {{
    color: {TEXT};
    background-color: {INPUT_SURFACE};
    border: 1px solid {INPUT_BORDER};
    border-radius: 6px;
    min-height: 22px;
    padding: 7px 10px;
    selection-color: {BACKGROUND};
    selection-background-color: {GREEN};
}}

QLineEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {{
    background-color: {INPUT_SURFACE_HOVER};
    border-color: {INPUT_BORDER_HOVER};
}}

QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{
    background-color: #15271c;
    border: 2px solid {GREEN_BRIGHT};
    padding: 6px 9px;
}}

QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled {{
    color: #73857a;
    background-color: {INPUT_DISABLED};
    border-color: #25382b;
}}

QLineEdit[readOnly="true"] {{
    color: {TEXT};
}}

QAbstractSpinBox {{
    padding-right: 31px;
}}

QAbstractSpinBox:focus {{
    padding-right: 30px;
}}

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    width: 25px;
    background-color: #18291e;
    border-left: 1px solid {INPUT_BORDER};
}}

QAbstractSpinBox::up-button {{
    border-top-right-radius: 5px;
    border-bottom: 1px solid #294f36;
}}

QAbstractSpinBox::down-button {{
    border-bottom-right-radius: 5px;
}}

QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
    background-color: {GREEN_DARK};
    border-left-color: {GREEN};
}}

QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {{
    width: 9px;
    height: 9px;
}}

QAbstractSpinBox::up-arrow {{
    image: url({_ARROW_UP});
}}

QAbstractSpinBox::down-arrow {{
    image: url({_ARROW_DOWN});
}}

QAbstractSpinBox:disabled::up-button,
QAbstractSpinBox:disabled::down-button {{
    background-color: #111912;
    border-left-color: #25382b;
}}

QTextEdit {{
    color: {TEXT};
    background-color: {INPUT_BACKGROUND};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 9px;
    selection-color: {BACKGROUND};
    selection-background-color: {GREEN};
}}

QTextEdit:focus {{
    border-color: {GREEN};
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

QMenuBar {{
    color: {TEXT};
    background-color: {PANEL};
}}

QMenuBar::item:selected, QMenu::item:selected {{
    color: {GREEN_BRIGHT};
    background-color: {GREEN_DARK};
}}

QMenu {{
    color: {TEXT};
    background-color: {PANEL};
    border: 1px solid {BORDER};
}}

QComboBox {{
    padding-right: 35px;
}}

QComboBox:focus {{
    padding-right: 34px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 29px;
    background-color: #18291e;
    border-left: 1px solid {INPUT_BORDER};
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}

QComboBox::drop-down:hover {{
    background-color: {GREEN_DARK};
    border-left-color: {GREEN};
}}

QComboBox::down-arrow {{
    image: url({_ARROW_DOWN});
    width: 10px;
    height: 10px;
}}

QComboBox:disabled::drop-down {{
    background-color: #111912;
    border-left-color: #25382b;
}}

QComboBox QAbstractItemView {{
    color: {TEXT};
    background-color: {INPUT_SURFACE};
    border: 1px solid {INPUT_BORDER_HOVER};
    outline: 0;
    padding: 3px;
    selection-color: {GREEN_BRIGHT};
    selection-background-color: {GREEN_DARK};
}}

QLabel#aboutTitle {{
    color: {GREEN_BRIGHT};
    font-size: 20pt;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#aboutVersion {{
    color: {GREEN};
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}}

QLabel#aboutDetails {{
    color: {TEXT};
}}
"""


LIGHT_STYLE_SHEET = """
QWidget {
    color: #26342d;
    background-color: #eef2ef;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10pt;
}

QMainWindow, QDialog {
    background-color: #eef2ef;
}

QWidget#mainCanvas {
    background-color: #dde5df;
}

QFrame#appShell {
    background-color: #f6f8f6;
    border: 1px solid #94ab9c;
    border-radius: 12px;
}

QLabel {
    background: transparent;
}

QLabel#headerEyebrow {
    color: #287a4d;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 8pt;
    font-weight: 600;
    letter-spacing: 1px;
}

QLabel#appTitle {
    color: #174d31;
    font-size: 24pt;
    font-weight: 700;
    letter-spacing: 2px;
}

QLabel#appSubtitle, QLabel#sectionHint {
    color: #64736a;
}

QLabel#versionBadge {
    color: #155a35;
    background-color: #e1eee6;
    border: 1px solid #9db9a7;
    border-radius: 11px;
    padding: 4px 10px;
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}

QLabel#headerMeta {
    color: #64736a;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 7.5pt;
    font-weight: 600;
    letter-spacing: 1px;
}

QLabel#statusLabel {
    color: #155a35;
    font-weight: 600;
}

QLabel#etaLabel {
    color: #52665a;
    font-family: "DejaVu Sans Mono", monospace;
}

QFrame#headerFrame {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #f8fbf9, stop: 1 #ffffff
    );
    border: 1px solid #a9beb0;
    border-left: 5px solid #278653;
    border-radius: 8px;
}

QFrame#headerDivider {
    color: #c2cec6;
    background-color: #c2cec6;
    border: none;
    min-width: 1px;
    max-width: 1px;
    min-height: 42px;
}

QGroupBox {
    color: #174d31;
    background-color: #ffffff;
    border: 1px solid #b8c8be;
    border-radius: 7px;
    font-weight: 600;
    margin-top: 12px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #ffffff;
}

QLineEdit, QSpinBox, QTextEdit, QComboBox {
    color: #26342d;
    background-color: #ffffff;
    border: 1px solid #aebeb4;
    border-radius: 5px;
    padding: 7px 9px;
    selection-color: #ffffff;
    selection-background-color: #287a4d;
}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #287a4d;
}

QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    color: #89948e;
    background-color: #e7ebe8;
}

QSpinBox {
    padding-right: 24px;
}

QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    background-color: #e7eee9;
    border-left: 1px solid #aebeb4;
}

QComboBox QAbstractItemView {
    color: #26342d;
    background-color: #ffffff;
    selection-color: #ffffff;
    selection-background-color: #287a4d;
}

QPushButton {
    color: #244332;
    background-color: #f8faf8;
    border: 1px solid #9fb2a6;
    border-radius: 5px;
    min-height: 20px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    color: #123522;
    background-color: #e1eee6;
    border-color: #287a4d;
}

QPushButton:pressed {
    background-color: #cfdfd5;
}

QPushButton:disabled {
    color: #929c96;
    background-color: #e9ecea;
    border-color: #d0d7d2;
}

QPushButton#primaryButton {
    color: #ffffff;
    background-color: #287a4d;
    border-color: #185f39;
    min-width: 100px;
}

QPushButton#primaryButton:hover {
    background-color: #1f6841;
}

QPushButton#cancelButton {
    min-width: 100px;
}

QProgressBar {
    color: #26342d;
    background-color: #e1e8e3;
    border: 1px solid #9fb2a6;
    border-radius: 6px;
    min-height: 22px;
    text-align: center;
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: #338b59;
    border-radius: 5px;
}

QTextEdit#logView {
    color: #26342d;
    background-color: #fbfcfb;
    border-color: #aebeb4;
    font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
    font-size: 9.5pt;
}

QScrollBar:vertical {
    background: #edf1ee;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #a7b9ad;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #7f9988;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QMenuBar {
    color: #26342d;
    background-color: #ffffff;
}

QMenuBar::item:selected, QMenu::item:selected {
    color: #ffffff;
    background-color: #287a4d;
}

QMenu {
    color: #26342d;
    background-color: #ffffff;
    border: 1px solid #aebeb4;
}

QToolTip {
    color: #26342d;
    background-color: #ffffff;
    border: 1px solid #287a4d;
    padding: 4px;
}

QLabel#aboutTitle {
    color: #174d31;
    font-size: 20pt;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#aboutVersion {
    color: #287a4d;
    font-family: "DejaVu Sans Mono", monospace;
    font-weight: 600;
}

QLabel#aboutDetails {
    color: #26342d;
}
"""


def load_theme_name() -> str:
    """Load the saved theme, falling back to Matrix."""
    name = QSettings().value("theme", DEFAULT_THEME)
    return name if name in AVAILABLE_THEMES else DEFAULT_THEME


def save_theme_name(name: str) -> None:
    """Persist a valid theme using the application's QSettings identity."""
    if name in AVAILABLE_THEMES:
        QSettings().setValue("theme", name)


def apply_theme(app: QApplication, name: str = DEFAULT_THEME) -> None:
    """Apply a theme palette and shared widget stylesheet."""
    if name not in AVAILABLE_THEMES:
        name = DEFAULT_THEME

    is_light = name == "Chiaro"
    background = "#eef2ef" if is_light else BACKGROUND
    panel = "#ffffff" if is_light else PANEL
    panel_raised = "#f8faf8" if is_light else PANEL_RAISED
    input_background = "#ffffff" if is_light else INPUT_BACKGROUND
    text = "#26342d" if is_light else TEXT
    placeholder_text = "#718078" if is_light else "#9abca4"
    accent = "#287a4d" if is_light else GREEN
    highlighted_text = "#ffffff" if is_light else BACKGROUND

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
    palette.setColor(QPalette.ColorRole.Base, QColor(input_background))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(panel))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(panel_raised))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(text))
    palette.setColor(QPalette.ColorRole.Text, QColor(text))
    palette.setColor(QPalette.ColorRole.Button, QColor(panel_raised))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(accent))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(highlighted_text))
    app.setPalette(palette)
    app.setStyleSheet(LIGHT_STYLE_SHEET if is_light else MATRIX_STYLE_SHEET)
