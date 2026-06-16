"""Offline tests for the GUI screenshot helper bootstrap."""

from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "capture-gui-screenshots.py"


def _load_helper_module():
    spec = importlib.util.spec_from_file_location(
        "capture_gui_screenshots",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CaptureGuiScreenshotsBootstrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helper = _load_helper_module()

    def test_find_project_root_from_script_path(self) -> None:
        self.assertEqual(PROJECT_ROOT, self.helper.find_project_root(SCRIPT_PATH))

    def test_bootstrap_reexecs_with_project_venv_and_preserves_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "scripts" / "capture-gui-screenshots.py"
            venv_python = root / ".venv" / "bin" / "python"
            script.parent.mkdir()
            venv_python.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            venv_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            calls: list[tuple[str, list[str]]] = []

            def fake_execv(path: str, args) -> None:
                calls.append((path, list(args)))

            exit_code = self.helper.bootstrap_project_venv(
                script_path=script,
                executable="/usr/bin/python3",
                argv=[str(script), "--theme", "Matrix"],
                environ={},
                execv=fake_execv,
            )

            self.assertEqual(127, exit_code)
            self.assertEqual(
                [
                    (
                        str(venv_python),
                        [str(venv_python), str(script), "--theme", "Matrix"],
                    )
                ],
                calls,
            )

    def test_bootstrap_reports_missing_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "scripts" / "capture-gui-screenshots.py"
            script.parent.mkdir()
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = self.helper.bootstrap_project_venv(
                    script_path=script,
                    executable="/usr/bin/python3",
                    argv=[str(script)],
                    environ={},
                    execv=lambda _path, _args: None,
                )

            self.assertEqual(1, exit_code)
            self.assertIn(self.helper.VENV_HINT, stderr.getvalue())

    def test_bootstrap_skips_when_already_using_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "scripts" / "capture-gui-screenshots.py"
            venv_python = root / ".venv" / "bin" / "python3"
            script.parent.mkdir()
            venv_python.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            exit_code = self.helper.bootstrap_project_venv(
                script_path=script,
                executable=str(venv_python),
                argv=[str(script)],
                environ={},
                execv=lambda _path, _args: self.fail("unexpected execv"),
            )

            self.assertIsNone(exit_code)

    def test_bootstrap_guard_exits_without_looping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            script = root / "scripts" / "capture-gui-screenshots.py"
            venv_python = root / ".venv" / "bin" / "python"
            script.parent.mkdir()
            venv_python.parent.mkdir(parents=True)
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            venv_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = self.helper.bootstrap_project_venv(
                    script_path=script,
                    executable="/usr/bin/python3",
                    argv=[str(script)],
                    environ={self.helper.REEXEC_ENV_VAR: "1"},
                    execv=lambda _path, _args: self.fail("unexpected execv"),
                )

            self.assertEqual(1, exit_code)
            self.assertIn("Rilancio nella venv non riuscito", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
