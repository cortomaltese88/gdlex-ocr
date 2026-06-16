#!/usr/bin/env python3
"""Capture diagnostic GUI screenshots without starting OCR."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, MutableMapping, Sequence


REEXEC_ENV_VAR = "GDLEX_OCR_SCREENSHOT_HELPER_REEXEC"
VENV_HINT = (
    "Eseguire con .venv/bin/python scripts/capture-gui-screenshots.py "
    "oppure creare la venv."
)


def find_project_root(script_path: Path | str = __file__) -> Path:
    """Return the repository root for this helper script."""
    return Path(script_path).resolve().parents[1]


def project_venv_python(project_root: Path) -> Path:
    return project_root / ".venv" / "bin" / "python"


def is_project_venv_python(executable: str, project_root: Path) -> bool:
    executable_path = Path(executable).expanduser()
    if not executable_path.is_absolute():
        executable_path = Path.cwd() / executable_path

    venv_bin = project_root / ".venv" / "bin"
    try:
        executable_path.absolute().relative_to(venv_bin.absolute())
    except ValueError:
        return False
    return executable_path.name.startswith("python")


def bootstrap_project_venv(
    *,
    script_path: Path | str = __file__,
    executable: str | None = None,
    argv: Sequence[str] | None = None,
    environ: MutableMapping[str, str] | None = None,
    execv: Callable[[str, Sequence[str]], object] | None = None,
) -> int | None:
    """Re-exec this script inside the project venv when launched directly."""
    project_root = find_project_root(script_path)
    executable = executable or sys.executable
    argv = argv or sys.argv
    environ = environ if environ is not None else os.environ
    execv = execv or os.execv

    if is_project_venv_python(executable, project_root):
        return None

    venv_python = project_venv_python(project_root)
    if environ.get(REEXEC_ENV_VAR) == "1":
        print(f"Rilancio nella venv non riuscito. {VENV_HINT}", file=sys.stderr)
        return 1

    if venv_python.is_file():
        environ[REEXEC_ENV_VAR] = "1"
        execv(
            str(venv_python),
            [str(venv_python), str(Path(script_path).resolve()), *argv[1:]],
        )
        return 127

    print(VENV_HINT, file=sys.stderr)
    return 1


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("GDLEX_OCR_DISABLE_TRAY", "1")

    project_root = find_project_root()
    sys.path.insert(0, str(project_root))

    from PySide6.QtWidgets import QApplication

    from gdlex_ocr.gui import MainWindow
    from gdlex_ocr.theme import apply_theme

    output_dir = Path(
        os.environ.get(
            "GDLEX_OCR_GUI_SCREENSHOT_DIR",
            "/tmp/gdlex-ocr-gui-screenshots",
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    apply_theme(app, os.environ.get("GDLEX_OCR_GUI_THEME", "Matrix"))

    window = MainWindow()
    window.resize(1020, 780)
    window.show()
    app.processEvents()

    captures = (
        ("base.png", window.pdf_output_base_tab),
        ("backend_ocr.png", window.pdf_output_backend_tab),
    )
    for filename, tab in captures:
        window.pdf_output_tabs.setCurrentWidget(tab)
        app.processEvents()
        path = output_dir / filename
        if not window.grab().save(str(path)):
            raise RuntimeError(f"Impossibile salvare lo screenshot: {path}")
        print(path)

    window.close()
    return 0


if __name__ == "__main__":
    bootstrap_exit = bootstrap_project_venv()
    if bootstrap_exit is not None:
        raise SystemExit(bootstrap_exit)
    raise SystemExit(main())
