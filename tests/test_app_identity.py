"""Offline consistency checks for application identity and version metadata."""

from __future__ import annotations

import configparser
import re
import unittest
from pathlib import Path

from gdlex_ocr import version


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_APP_NAME = "GD LEX OCR"


class ApplicationIdentityTest(unittest.TestCase):
    def test_application_name_is_consistent_with_desktop_file(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(
            PROJECT_ROOT / "packaging" / "gdlex-ocr.desktop",
            encoding="utf-8",
        )

        self.assertEqual(EXPECTED_APP_NAME, version.APP_NAME)
        self.assertEqual(
            EXPECTED_APP_NAME,
            parser["Desktop Entry"]["Name"],
        )

    def test_application_version_matches_current_debian_version(self) -> None:
        debian_changelog = (
            PROJECT_ROOT / "packaging" / "changelog"
        ).read_text(encoding="utf-8")
        header = next(
            line for line in debian_changelog.splitlines() if line.strip()
        )
        match = re.match(r"^[^\s]+\s+\(([^)]+)\)", header)

        self.assertIsNotNone(match, "Invalid Debian changelog header")
        self.assertEqual(match.group(1), version.APP_VERSION)

    def test_application_version_is_documented_in_project_changelog(
        self,
    ) -> None:
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )
        version_heading = re.compile(
            rf"^#{{1,6}}\s+\[?v?{re.escape(version.APP_VERSION)}\]?"
            r"(?:\s|$)",
            re.MULTILINE,
        )

        self.assertIn(version.APP_VERSION, changelog)
        self.assertRegex(changelog, version_heading)

    def test_version_label_matches_application_version_when_present(
        self,
    ) -> None:
        if hasattr(version, "APP_VERSION_LABEL"):
            self.assertEqual(
                f"v{version.APP_VERSION}",
                version.APP_VERSION_LABEL,
            )


if __name__ == "__main__":
    unittest.main()
