"""Offline checks for desktop integration assets."""

from __future__ import annotations

import configparser
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ApplicationIconTest(unittest.TestCase):
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


class DesktopFileTest(unittest.TestCase):
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
        self.assertEqual("Office;Utility;", entry["Categories"])
        self.assertEqual("true", entry["StartupNotify"])


if __name__ == "__main__":
    unittest.main()
