"""Offline checks for desktop integration assets."""

from __future__ import annotations

import configparser
import os
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gdlex_ocr.icons import application_icon_paths, tray_icon, tray_icon_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ApplicationIconTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_svg_has_expected_viewbox_and_vector_content(self) -> None:
        icon_path = PROJECT_ROOT / "assets" / "icon.svg"
        root = ET.parse(icon_path).getroot()

        self.assertEqual("0 0 512 512", root.attrib.get("viewBox"))
        self.assertTrue(root.tag.endswith("svg"))
        self.assertNotIn("data:image", icon_path.read_text(encoding="utf-8"))

    def test_svg_contains_ocr_monogram(self) -> None:
        text = (PROJECT_ROOT / "assets" / "icon.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="OCR-monogram"', text)

    def test_application_icon_uses_known_raster_sizes(self) -> None:
        paths = application_icon_paths()

        self.assertEqual(
            tuple(
                PROJECT_ROOT / "assets" / f"icon-{size}.png"
                for size in (32, 48, 64, 128, 256)
            ),
            paths,
        )
        self.assertTrue(all(path.is_file() for path in paths))

    def test_tray_icon_is_fixed_size_png(self) -> None:
        path = tray_icon_path()

        self.assertEqual(PROJECT_ROOT / "assets" / "icon-64.png", path)
        self.assertTrue(path.is_file())

    def test_tray_icon_helper_loads_valid_raster_icon(self) -> None:
        icon = tray_icon()

        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())


class DesktopFileTest(unittest.TestCase):
    def test_development_installer_is_portable_and_preserves_arguments(self) -> None:
        installer = (PROJECT_ROOT / "scripts/install-desktop.sh").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("/home/", installer)
        self.assertIn('${BASH_SOURCE[0]}', installer)
        self.assertIn('app.py "$@"', installer)

    def test_application_uses_launcher_desktop_file_name(self) -> None:
        entry_point = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('app.setDesktopFileName("gdlex-ocr")', entry_point)

    def test_launcher_has_required_values(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(
            PROJECT_ROOT / "packaging" / "gdlex-ocr.desktop",
            encoding="utf-8",
        )
        entry = parser["Desktop Entry"]

        self.assertEqual("GD LEX OCR", entry["Name"])
        self.assertEqual("Local OCR", entry["GenericName"])
        self.assertEqual("gdlex-ocr", entry["Exec"])
        self.assertEqual("gdlex-ocr", entry["Icon"])
        self.assertEqual("false", entry["Terminal"])
        self.assertEqual("Application", entry["Type"])
        self.assertEqual("Office;", entry["Categories"])
        self.assertEqual("true", entry["StartupNotify"])


if __name__ == "__main__":
    unittest.main()
