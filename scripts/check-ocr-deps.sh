#!/usr/bin/env bash

set -euo pipefail

missing=0

echo "OCRmyPDF:"
if command -v ocrmypdf >/dev/null 2>&1; then
    printf '  percorso: %s\n' "$(command -v ocrmypdf)"
    printf '  versione: %s\n' "$(ocrmypdf --version 2>&1 | sed -n '1p')"
else
    echo "  non trovato"
    missing=1
fi

echo
echo "Tesseract:"
if command -v tesseract >/dev/null 2>&1; then
    printf '  percorso: %s\n' "$(command -v tesseract)"
    printf '  versione: %s\n' "$(tesseract --version 2>&1 | sed -n '1p')"
    echo "  lingue disponibili:"
    languages="$(tesseract --list-langs 2>&1)"
    printf '%s\n' "${languages}" | sed 's/^/    /'
    if ! printf '%s\n' "${languages}" | grep -qx "ita"; then
        echo "  lingua italiana (ita) non trovata"
        missing=1
    fi
else
    echo "  non trovato"
    missing=1
fi

if (( missing )); then
    echo
    echo "Per installare i prerequisiti:"
    echo "sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-ita"
    exit 1
fi

echo
echo "Prerequisiti OCRmyPDF/Tesseract disponibili."
