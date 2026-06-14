"""Static checks for the lightweight Debian source package."""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DebianPackagingTest(unittest.TestCase):
    def test_build_script_has_required_payload_and_exclusions(self) -> None:
        script = (
            PROJECT_ROOT / "scripts" / "build-deb.sh"
        ).read_text(encoding="utf-8")

        for required in (
            "app.py",
            "gdlex_ocr/*.py",
            "assets/*",
            "packaging/changelog",
            "packaging/gdlex-ocr.desktop",
            "packaging/gdlex-ocr.1",
            "README.md",
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            "CHANGELOG.md",
            "PACKAGING.md",
            "RELEASE_CHECKLIST.md",
            "requirements.txt",
        ):
            self.assertIn(required, script)

        for forbidden in (".venv", "__pycache__", "*.pdf", "*.PDF", "*.log"):
            self.assertIn(forbidden, script)
        self.assertIn("sha256sum", script)

    def test_wrapper_uses_external_python_environment(self) -> None:
        wrapper = (
            PROJECT_ROOT / "packaging" / "gdlex-ocr"
        ).read_text(encoding="utf-8")

        self.assertIn("GDLEX_OCR_PYTHON", wrapper)
        self.assertIn(".local/share/gdlex-ocr/venv", wrapper)
        self.assertIn('APP_DIR="/usr/lib/gdlex-ocr"', wrapper)
        self.assertIn('"${APP_DIR}/app.py"', wrapper)
        self.assertNotIn("/usr/lib/gdlex-ocr/.venv", wrapper)

    def test_manual_page_documents_external_dependencies(self) -> None:
        manual = (
            PROJECT_ROOT / "packaging" / "gdlex-ocr.1"
        ).read_text(encoding="utf-8")

        self.assertIn("GDLEX_OCR_PYTHON", manual)
        self.assertIn("requirements.txt", manual)


if __name__ == "__main__":
    unittest.main()
