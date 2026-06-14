#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if command -v python >/dev/null 2>&1; then
    PYTHON=python
elif [[ -x .venv/bin/python ]]; then
    PYTHON=.venv/bin/python
else
    echo "Errore: attivare l'ambiente Python del progetto." >&2
    exit 1
fi

"$PYTHON" -m py_compile app.py gdlex_ocr/*.py
"$PYTHON" -m unittest discover -s tests -v
bash -n scripts/install-desktop.sh
bash -n scripts/uninstall-desktop.sh
bash -n scripts/check-ocr-deps.sh
bash -n scripts/build-deb.sh
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate packaging/gdlex-ocr.desktop
fi
git diff --check
