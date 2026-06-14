"""Generated startup splash screen for GD LEX OCR."""

from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSplashScreen

from gdlex_ocr.theme import (
    BACKGROUND,
    BORDER,
    GREEN,
    GREEN_BRIGHT,
    GREEN_DARK,
    TEXT_MUTED,
)
from gdlex_ocr.version import APP_NAME, APP_SUBTITLE, APP_VERSION_LABEL


def create_splash() -> QSplashScreen:
    """Build a self-contained splash without external image assets."""
    width, height = 620, 330
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(BACKGROUND))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    background = QLinearGradient(0, 0, width, height)
    background.setColorAt(0.0, QColor("#050806"))
    background.setColorAt(0.55, QColor("#0a120d"))
    background.setColorAt(1.0, QColor("#071a0e"))
    painter.fillRect(pixmap.rect(), background)

    randomizer = random.Random(3101984)
    painter.setFont(QFont("DejaVu Sans Mono", 8))
    for column in range(18, width, 24):
        alpha = randomizer.randint(20, 58)
        painter.setPen(QColor(50, 232, 117, alpha))
        glyphs = "".join(randomizer.choice("01GDLX") for _ in range(8))
        painter.drawText(column, randomizer.randint(20, 115), glyphs)

    painter.fillRect(0, 0, 7, height, QColor(GREEN))
    painter.setPen(QPen(QColor(BORDER), 1))
    painter.drawRoundedRect(15, 15, width - 30, height - 30, 10, 10)

    painter.setPen(QColor(GREEN_BRIGHT))
    painter.setFont(QFont("DejaVu Sans", 29, QFont.Weight.Bold))
    painter.drawText(
        54,
        136,
        width - 108,
        58,
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        APP_NAME,
    )

    painter.setPen(QColor(TEXT_MUTED))
    painter.setFont(QFont("DejaVu Sans", 11))
    painter.drawText(
        57,
        192,
        width - 114,
        32,
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        APP_SUBTITLE,
    )

    painter.setPen(QPen(QColor(GREEN_DARK), 1))
    painter.drawLine(57, 238, width - 57, 238)

    painter.setPen(QColor(GREEN))
    painter.setFont(QFont("DejaVu Sans Mono", 10, QFont.Weight.DemiBold))
    painter.drawText(
        57,
        255,
        width - 114,
        28,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        APP_VERSION_LABEL,
    )
    painter.end()

    splash = QSplashScreen(
        pixmap,
        Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint,
    )
    splash.setObjectName("startupSplash")
    return splash
