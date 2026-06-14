#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="/home/marco/progetti/gdlex-tools/gdlex-ocr"
ICON_ROOT="${HOME}/.local/share/icons/hicolor"
APPLICATIONS_DIR="${HOME}/.local/share/applications"
BIN_DIR="${HOME}/.local/bin"

install -d "${ICON_ROOT}/scalable/apps" "${APPLICATIONS_DIR}" "${BIN_DIR}"
install -m 0644 \
    "${PROJECT_DIR}/assets/icon.svg" \
    "${ICON_ROOT}/scalable/apps/gdlex-ocr.svg"

for size in 256 128 64 48 32; do
    source_icon="${PROJECT_DIR}/assets/icon-${size}.png"
    if [[ -f "${source_icon}" ]]; then
        install -d "${ICON_ROOT}/${size}x${size}/apps"
        install -m 0644 \
            "${source_icon}" \
            "${ICON_ROOT}/${size}x${size}/apps/gdlex-ocr.png"
    fi
done

install -m 0644 \
    "${PROJECT_DIR}/packaging/gdlex-ocr.desktop" \
    "${APPLICATIONS_DIR}/gdlex-ocr.desktop"

cat > "${BIN_DIR}/gdlex-ocr" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /home/marco/progetti/gdlex-tools/gdlex-ocr
exec /home/marco/progetti/gdlex-tools/gdlex-ocr/.venv/bin/python app.py
EOF
chmod 0755 "${BIN_DIR}/gdlex-ocr"

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 >/dev/null 2>&1 || true
fi

printf 'Launcher GD LEX OCR installato per l'\''utente %s.\n' "${USER:-corrente}"
printf 'Verificare che %s sia incluso in PATH.\n' "${BIN_DIR}"
