#!/usr/bin/env bash

set -euo pipefail

ICON_ROOT="${HOME}/.local/share/icons/hicolor"

rm -f "${HOME}/.local/share/applications/gdlex-ocr.desktop"
rm -f "${HOME}/.local/bin/gdlex-ocr"
rm -f "${ICON_ROOT}/scalable/apps/gdlex-ocr.svg"

for size in 256 128 64 48 32; do
    rm -f "${ICON_ROOT}/${size}x${size}/apps/gdlex-ocr.png"
done

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 >/dev/null 2>&1 || true
fi

echo "Launcher GD LEX OCR rimosso per l'utente corrente."
