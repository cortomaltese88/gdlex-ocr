"""Application icon helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_APPLICATION_ICON_SIZES = (32, 48, 64, 128, 256)
_SPLASH_ICON_SIZE = 128
_TRAY_ICON_SIZE = 64


def application_icon_paths() -> tuple[Path, ...]:
    """Return the raster files used for the window icon."""
    return tuple(
        _ASSETS_DIR / f"icon-{size}.png"
        for size in _APPLICATION_ICON_SIZES
    )


def application_icon() -> QIcon:
    """Build the window icon from bounded raster sizes."""
    icon = QIcon()
    for size, path in zip(_APPLICATION_ICON_SIZES, application_icon_paths()):
        if path.is_file():
            icon.addFile(str(path), QSize(size, size))
    return icon


def splash_icon_path() -> Path:
    """Return the raster icon used by the startup splash."""
    return _ASSETS_DIR / f"icon-{_SPLASH_ICON_SIZE}.png"


def tray_icon_path() -> Path:
    """Return the raster icon used by the system tray."""
    return _ASSETS_DIR / f"icon-{_TRAY_ICON_SIZE}.png"


def tray_icon() -> QIcon:
    """Load a fixed-size raster icon for the system tray."""
    path = tray_icon_path()
    if not path.is_file():
        return QIcon()
    return QIcon(QPixmap(str(path)))
