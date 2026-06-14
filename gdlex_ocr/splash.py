"""Animated Matrix-style startup splash for GD LEX OCR."""

from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSplashScreen

from gdlex_ocr.icons import splash_icon_path
from gdlex_ocr.version import APP_NAME, APP_SUBTITLE, APP_VERSION_LABEL


SPLASH_DISABLE_ENV = "GDLEX_OCR_DISABLE_SPLASH"
SPLASH_DURATION_MS = 2800
SPLASH_FRAME_INTERVAL_MS = 50
_DIGITAL_RAIN_GLYPHS = "01GDLX<>/{}[]"


def splash_disabled() -> bool:
    """Return whether the startup splash is disabled by the environment."""
    value = os.environ.get(SPLASH_DISABLE_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def digital_rain_columns(width: int, column_width: int = 24) -> tuple[int, ...]:
    """Return stable x coordinates for the animated rain columns."""
    if width <= 0 or column_width <= 0:
        return ()
    return tuple(range(column_width // 2, width, column_width))


def digital_rain_cell(column: int, row: int, frame: int) -> tuple[str, int]:
    """Return a deterministic glyph and opacity for one rain cell."""
    seed = column * 17 + row * 31 + frame
    glyph = _DIGITAL_RAIN_GLYPHS[seed % len(_DIGITAL_RAIN_GLYPHS)]
    trail = (row - (frame // 2 + column * 3)) % 18
    if trail == 0:
        alpha = 210
    elif trail < 6:
        alpha = 125 - trail * 17
    else:
        alpha = 16
    return glyph, alpha


class MatrixSplashScreen(QSplashScreen):
    """Lightweight Matrix splash using the raster application icon."""

    _WIDTH = 680
    _HEIGHT = 380
    _ICON_SIZE = 88

    def __init__(self) -> None:
        pixmap = QPixmap(self._WIDTH, self._HEIGHT)
        pixmap.fill(QColor("#030704"))
        super().__init__(
            pixmap,
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("startupSplash")
        self._frame = 0
        self._progress = 0.0
        self._brand_icon = QPixmap(str(splash_icon_path()))
        self._timer = QTimer(self)
        self._timer.setInterval(SPLASH_FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._render()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._frame += 1
        self._progress = min(
            1.0,
            self._progress + SPLASH_FRAME_INTERVAL_MS / SPLASH_DURATION_MS,
        )
        self._render()

    def _render(self) -> None:
        pixmap = QPixmap(self._WIDTH, self._HEIGHT)
        pixmap.fill(QColor("#030704"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rain_font = QFont("DejaVu Sans Mono", 10)
        painter.setFont(rain_font)
        row_height = 20
        row_count = self._HEIGHT // row_height + 2
        for column, x in enumerate(digital_rain_columns(self._WIDTH)):
            phase = (self._frame + column * 5) % row_count
            for row in range(-1, row_count):
                glyph, alpha = digital_rain_cell(column, row, self._frame)
                y = ((row + phase) % row_count) * row_height - 4
                painter.setPen(QColor(0, 255, 65, alpha))
                painter.drawText(x, y, glyph)

        panel = QRectF(54.0, 42.0, self._WIDTH - 108.0, 254.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(3, 12, 6, 226)))
        painter.drawRoundedRect(panel, 12.0, 12.0)

        outer = QRectF(1.0, 1.0, self._WIDTH - 2.0, self._HEIGHT - 2.0)
        inner = QRectF(5.0, 5.0, self._WIDTH - 10.0, self._HEIGHT - 10.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#00b83a"), 2))
        painter.drawRect(outer)
        painter.setPen(QPen(QColor("#123d1d"), 1))
        painter.drawRect(inner)

        if not self._brand_icon.isNull():
            icon = self._brand_icon.scaled(
                self._ICON_SIZE,
                self._ICON_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_x = 105.0 + (self._ICON_SIZE - icon.width()) / 2
            icon_y = 79.0 + (self._ICON_SIZE - icon.height()) / 2
            painter.drawPixmap(int(icon_x), int(icon_y), icon)

        painter.setFont(QFont("DejaVu Sans Mono", 34, QFont.Weight.Bold))
        painter.setPen(QColor("#e0ffe7"))
        painter.drawText(
            QRectF(205.0, 76.0, 370.0, 58.0),
            Qt.AlignmentFlag.AlignCenter,
            APP_NAME,
        )

        painter.setFont(QFont("DejaVu Sans", 12))
        painter.setPen(QColor("#7bf59a"))
        painter.drawText(
            QRectF(205.0, 137.0, 370.0, 30.0),
            Qt.AlignmentFlag.AlignCenter,
            APP_SUBTITLE,
        )

        painter.setPen(QPen(QColor("#1a5c2d"), 1))
        painter.drawLine(116, 184, self._WIDTH - 116, 184)

        painter.setFont(QFont("DejaVu Sans Mono", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#39ff70"))
        painter.drawText(
            QRectF(72.0, 198.0, self._WIDTH - 144.0, 26.0),
            Qt.AlignmentFlag.AlignCenter,
            APP_VERSION_LABEL,
        )

        painter.setFont(QFont("DejaVu Sans Mono", 9))
        painter.setPen(QColor("#68bd7c"))
        painter.drawText(
            QRectF(72.0, 237.0, self._WIDTH - 144.0, 24.0),
            Qt.AlignmentFlag.AlignCenter,
            "LOCAL OCR / NO CLOUD UPLOAD",
        )

        bar_x, bar_y = 74.0, self._HEIGHT - 48.0
        bar_width, bar_height = self._WIDTH - 148.0, 8.0
        painter.setBrush(QBrush(QColor("#07140a")))
        painter.setPen(QPen(QColor("#1a5c2d"), 1))
        painter.drawRoundedRect(
            QRectF(bar_x, bar_y, bar_width, bar_height),
            3.0,
            3.0,
        )
        fill_width = bar_width * self._progress
        if fill_width > 0:
            painter.setBrush(QBrush(QColor("#00d943")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                QRectF(bar_x, bar_y, fill_width, bar_height),
                3.0,
                3.0,
            )

        painter.end()
        self.setPixmap(pixmap)


def create_splash() -> MatrixSplashScreen:
    """Build the animated startup splash."""
    return MatrixSplashScreen()
