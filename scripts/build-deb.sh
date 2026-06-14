#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

for command in dpkg-deb gzip install mktemp sha256sum tar; do
    if ! command -v "${command}" >/dev/null 2>&1; then
        printf 'Errore: comando richiesto non trovato: %s\n' "${command}" >&2
        exit 1
    fi
done

VERSION="$(
    sed -n 's/^APP_VERSION = "\([^"]*\)"/\1/p' gdlex_ocr/version.py
)"
if [[ -z "${VERSION}" ]]; then
    echo "Errore: impossibile determinare APP_VERSION." >&2
    exit 1
fi

PACKAGE="gdlex-ocr"
BUILD_ROOT="$(mktemp -d)"
PACKAGE_ROOT="${BUILD_ROOT}/${PACKAGE}_${VERSION}_all"
OUTPUT_DIR="${PROJECT_DIR}/dist"
OUTPUT_PATH="${OUTPUT_DIR}/${PACKAGE}_${VERSION}_all.deb"
trap 'rm -rf "${BUILD_ROOT}"' EXIT

install -d \
    "${PACKAGE_ROOT}/DEBIAN" \
    "${PACKAGE_ROOT}/usr/bin" \
    "${PACKAGE_ROOT}/usr/lib/gdlex-ocr/gdlex_ocr" \
    "${PACKAGE_ROOT}/usr/lib/gdlex-ocr/assets" \
    "${PACKAGE_ROOT}/usr/share/applications" \
    "${PACKAGE_ROOT}/usr/share/doc/gdlex-ocr" \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps"
install -d "${PACKAGE_ROOT}/usr/share/man/man1"

install -m 0755 packaging/gdlex-ocr "${PACKAGE_ROOT}/usr/bin/gdlex-ocr"
install -m 0644 app.py "${PACKAGE_ROOT}/usr/lib/gdlex-ocr/app.py"
install -m 0644 gdlex_ocr/*.py "${PACKAGE_ROOT}/usr/lib/gdlex-ocr/gdlex_ocr/"
install -m 0644 assets/* "${PACKAGE_ROOT}/usr/lib/gdlex-ocr/assets/"
install -m 0644 \
    packaging/gdlex-ocr.desktop \
    "${PACKAGE_ROOT}/usr/share/applications/gdlex-ocr.desktop"
install -m 0644 \
    assets/icon.svg \
    "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps/gdlex-ocr.svg"

for size in 32 48 64 128 256; do
    install -d "${PACKAGE_ROOT}/usr/share/icons/hicolor/${size}x${size}/apps"
    install -m 0644 \
        "assets/icon-${size}.png" \
        "${PACKAGE_ROOT}/usr/share/icons/hicolor/${size}x${size}/apps/gdlex-ocr.png"
done

for document in \
    README.md \
    LICENSE \
    THIRD_PARTY_NOTICES.md \
    CHANGELOG.md \
    PACKAGING.md \
    RELEASE_CHECKLIST.md \
    requirements.txt; do
    install -m 0644 \
        "${document}" \
        "${PACKAGE_ROOT}/usr/share/doc/gdlex-ocr/${document}"
done
install -m 0644 LICENSE "${PACKAGE_ROOT}/usr/share/doc/gdlex-ocr/copyright"
gzip -9n -c packaging/changelog \
    > "${PACKAGE_ROOT}/usr/share/doc/gdlex-ocr/changelog.gz"
gzip -9n -c packaging/gdlex-ocr.1 \
    > "${PACKAGE_ROOT}/usr/share/man/man1/gdlex-ocr.1.gz"
chmod 0644 \
    "${PACKAGE_ROOT}/usr/share/doc/gdlex-ocr/changelog.gz" \
    "${PACKAGE_ROOT}/usr/share/man/man1/gdlex-ocr.1.gz"

INSTALLED_SIZE="$(du -sk "${PACKAGE_ROOT}/usr" | awk '{print $1}')"
cat > "${PACKAGE_ROOT}/DEBIAN/control" <<EOF
Package: ${PACKAGE}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Studio GD LEX <cortomaltese88@users.noreply.github.com>
Depends: python3 (>= 3.12), python3-venv
Suggests: ocrmypdf, tesseract-ocr, tesseract-ocr-ita
Installed-Size: ${INSTALLED_SIZE}
Homepage: https://github.com/cortomaltese88/gdlex-ocr
Description: OCR locale da PDF a Markdown
 Applicazione desktop PySide6 per convertire localmente documenti PDF in
 Markdown tramite Docling, con PDF ricercabile OCR opzionale.
EOF

mkdir -p "${OUTPUT_DIR}"
rm -f "${OUTPUT_PATH}"
dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "${OUTPUT_PATH}"

CONTENTS="$(dpkg-deb --fsys-tarfile "${OUTPUT_PATH}" | tar -tf -)"
while IFS= read -r entry; do
    case "${entry}" in
        *".venv"*|*"__pycache__"*|*"./.git"*|*.pdf|*.PDF|*.log)
            printf 'Errore: contenuto vietato nel pacchetto: %s\n' "${entry}" >&2
            exit 1
            ;;
    esac
done <<< "${CONTENTS}"

for required in \
    "./usr/bin/gdlex-ocr" \
    "./usr/lib/gdlex-ocr/app.py" \
    "./usr/share/applications/gdlex-ocr.desktop" \
    "./usr/share/doc/gdlex-ocr/requirements.txt"; do
    if ! grep -Fxq "${required}" <<< "${CONTENTS}"; then
        printf 'Errore: file richiesto assente dal pacchetto: %s\n' \
            "${required}" >&2
        exit 1
    fi
done

(
    cd "${OUTPUT_DIR}"
    sha256sum "$(basename "${OUTPUT_PATH}")" \
        > "$(basename "${OUTPUT_PATH}").sha256"
)

printf 'Pacchetto creato e verificato: %s\n' "${OUTPUT_PATH}"
printf 'Checksum SHA-256: %s.sha256\n' "${OUTPUT_PATH}"
