"""Checks for the lightweight Debian package and its per-user bootstrap."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DebianPackagingTest(unittest.TestCase):
    def test_built_debian_package_payload(self) -> None:
        packages = list((PROJECT_ROOT / "dist").glob("*.deb"))
        if not packages:
            self.skipTest("no Debian package found in dist/")

        package = max(packages, key=lambda candidate: candidate.stat().st_mtime)
        result = subprocess.run(
            ["dpkg-deb", "--contents", str(package)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"could not inspect {package.name}: {result.stderr}",
        )

        payload = {
            fields[5].split(" -> ", 1)[0].removeprefix(".")
            for line in result.stdout.splitlines()
            if len(fields := line.split(maxsplit=5)) == 6
        }
        for required in (
            "/usr/bin/gdlex-ocr",
            "/usr/lib/gdlex-ocr/app.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/gui.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/manifest.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/splash.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/tray.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/icons.py",
            "/usr/lib/gdlex-ocr/gdlex_ocr/version.py",
            "/usr/share/applications/gdlex-ocr.desktop",
            "/usr/share/man/man1/gdlex-ocr.1.gz",
            "/usr/share/icons/hicolor/64x64/apps/gdlex-ocr.png",
            "/usr/share/icons/hicolor/128x128/apps/gdlex-ocr.png",
        ):
            with self.subTest(required=required, package=package.name):
                self.assertIn(required, payload)

        forbidden = (
            ".venv",
            "__pycache__",
            ".git",
            ".pdf",
            "run.log",
            "manifest.json",
            "Fascicolo",
            "Downloads",
            "Documenti",
        )
        unexpected = sorted(
            path
            for path in payload
            if any(
                marker in path.lower()
                if marker == ".pdf"
                else marker in path
                for marker in forbidden
            )
        )
        self.assertFalse(
            unexpected,
            f"{package.name} contains forbidden payload entries: {unexpected}",
        )

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

    def test_wrapper_bootstraps_the_per_user_environment(self) -> None:
        wrapper = (
            PROJECT_ROOT / "packaging" / "gdlex-ocr"
        ).read_text(encoding="utf-8")

        self.assertIn('${HOME}/.local/share/gdlex-ocr', wrapper)
        self.assertIn('${HOME}/.local/state/gdlex-ocr', wrapper)
        self.assertIn('python3 -m venv', wrapper)
        self.assertIn('-m pip install --upgrade pip', wrapper)
        self.assertIn('-r "${REQUIREMENTS}"', wrapper)
        self.assertIn("setup.log", wrapper)
        self.assertIn("setup.lock", wrapper)
        self.assertIn("--setup-venv", wrapper)
        self.assertIn("--doctor", wrapper)
        self.assertNotIn("Preparare una venv utente", wrapper)
        self.assertNotIn("sudo", wrapper)
        self.assertIn('APP_DIR="/usr/lib/gdlex-ocr"', wrapper)
        self.assertIn(
            'exec "${VENV_PYTHON}" "${APP_DIR}/app.py" "$@"',
            wrapper,
        )
        self.assertNotIn("/usr/lib/gdlex-ocr/.venv", wrapper)

    def test_setup_command_creates_user_venv_without_real_downloads(self) -> None:
        wrapper = PROJECT_ROOT / "packaging" / "gdlex-ocr"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            fake_bin = root / "bin"
            calls = root / "python-calls.log"
            home.mkdir()
            fake_bin.mkdir()
            fake_python = fake_bin / "python3"
            fake_python.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "${FAKE_PYTHON_CALLS}"
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then
    target="${@: -1}"
    mkdir -p "${target}/bin"
    cp "$0" "${target}/bin/python"
fi
""",
                encoding="utf-8",
            )
            fake_python.chmod(
                fake_python.stat().st_mode | stat.S_IXUSR,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "PATH": f"{fake_bin}:{environment['PATH']}",
                    "FAKE_PYTHON_CALLS": str(calls),
                }
            )

            result = subprocess.run(
                ["bash", str(wrapper), "--setup-venv"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(
                (home / ".local/share/gdlex-ocr/venv/bin/python").is_file()
            )
            self.assertTrue(
                (home / ".local/state/gdlex-ocr/setup.log").is_file()
            )
            recorded_calls = calls.read_text(encoding="utf-8")
            self.assertIn("-m venv", recorded_calls)
            self.assertIn("-m pip install --upgrade pip", recorded_calls)
            self.assertIn("-m pip install --upgrade -r", recorded_calls)

    def test_doctor_does_not_start_or_bootstrap_the_application(self) -> None:
        wrapper = PROJECT_ROOT / "packaging" / "gdlex-ocr"
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            environment = os.environ.copy()
            environment["HOME"] = str(home)

            result = subprocess.run(
                ["bash", str(wrapper), "--doctor"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("diagnostica runtime", result.stdout)
            self.assertIn("Venv utente", result.stdout)
            self.assertFalse((home / ".local/share/gdlex-ocr").exists())

    def test_manual_page_documents_bootstrap_and_diagnostics(self) -> None:
        manual = (
            PROJECT_ROOT / "packaging" / "gdlex-ocr.1"
        ).read_text(encoding="utf-8")

        self.assertIn("\\-\\-setup\\-venv", manual)
        self.assertIn("\\-\\-doctor", manual)
        self.assertIn("setup.log", manual)
        self.assertIn("requirements.txt", manual)


if __name__ == "__main__":
    unittest.main()
