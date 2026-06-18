"""GD LEX OCR application entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_export import (
    default_casefile_json_path,
    default_casefile_markdown_path,
    write_casefile_analysis_json,
    write_casefile_analysis_markdown,
)
from gdlex_ocr.gui import MainWindow
from gdlex_ocr.icons import application_icon
from gdlex_ocr.judgments import (
    JUDGMENT_ANALYSIS_FILENAME,
    extract_judgment_metadata,
    format_judgment_summary,
    prepend_judgment_summary,
    write_judgment_analysis_for_markdown,
)
from gdlex_ocr.profiles import DEFAULT_PROFILE, PROFILES
from gdlex_ocr.searchable_pdf import DEFAULT_OCRMYPDF_TIMEOUT_SECONDS
from gdlex_ocr.splash import (
    SPLASH_DURATION_MS,
    create_splash,
    splash_disabled,
)
from gdlex_ocr.theme import apply_theme, load_theme_name
from gdlex_ocr.version import APP_NAME, APP_VERSION
from gdlex_ocr.worker import OcrWorker


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("deve essere un intero") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("deve essere maggiore di 0")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gdlex-ocr")
    parser.add_argument(
        "--version",
        action="store_true",
        help="stampa la versione ed esce",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="rimanda alla diagnostica del launcher installato ed esce",
    )
    parser.add_argument(
        "--analyze-judgment",
        metavar="INPUT.md",
        help="analizza offline una sentenza da Markdown gia' esistente",
    )
    parser.add_argument(
        "--analyze-casefile",
        metavar="CARTELLA",
        help="analizza una cartella fascicolo e genera indice JSON e Markdown",
    )
    parser.add_argument(
        "--output",
        metavar="OUTPUT",
        help=(
            "file Markdown di output per --analyze-judgment, directory output "
            "per --analyze-casefile oppure per la conversione PDF"
        ),
    )
    parser.add_argument(
        "--prepend",
        action="store_true",
        help="antepone la scheda sentenza al Markdown originale nell'output",
    )
    parser.add_argument(
        "--ocr-timeout",
        metavar="SECONDS",
        type=positive_int,
        default=DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
        help=(
            "timeout OCRmyPDF in secondi "
            f"(default: {DEFAULT_OCRMYPDF_TIMEOUT_SECONDS})"
        ),
    )
    parser.add_argument(
        "--ocr-jobs",
        metavar="N",
        type=positive_int,
        default=None,
        help="numero di job OCRmyPDF (--jobs); default automatico",
    )
    parser.add_argument(
        "--analyze-judgment-after-conversion",
        action="store_true",
        help=(
            "dopo la conversione PDF crea sentenza_analysis.md accanto al "
            "Markdown principale"
        ),
    )
    parser.add_argument(
        "input_pdf",
        nargs="?",
        help="PDF da convertire in Markdown senza aprire la GUI",
    )
    args = parser.parse_args(argv)
    skip = args.version or args.doctor
    if args.analyze_casefile and not skip:
        if not args.output:
            parser.error("--output e' obbligatorio con --analyze-casefile")
        if args.input_pdf:
            parser.error(
                "--analyze-casefile non puo' essere usato insieme a input_pdf"
            )
        if args.analyze_judgment:
            parser.error(
                "--analyze-casefile non puo' essere usato insieme a "
                "--analyze-judgment"
            )
        if args.analyze_judgment_after_conversion:
            parser.error(
                "--analyze-casefile non puo' essere usato insieme a "
                "--analyze-judgment-after-conversion"
            )
        if args.prepend:
            parser.error(
                "--analyze-casefile non puo' essere usato insieme a --prepend"
            )
    if args.analyze_judgment and not skip and not args.output:
        parser.error("--output e' obbligatorio con --analyze-judgment")
    if args.analyze_judgment and args.input_pdf and not skip:
        parser.error("--analyze-judgment non puo' essere usato insieme a input_pdf")
    if args.input_pdf and not skip and not args.output:
        parser.error("--output e' obbligatorio con input_pdf")
    return args


def analyze_judgment_markdown(input_name: str, output_name: str, prepend: bool) -> int:
    input_path = Path(input_name).expanduser()
    output_path = Path(output_name).expanduser()

    if not input_path.exists():
        print(f"Errore: input Markdown non trovato: {input_path}", file=sys.stderr)
        return 1
    if not input_path.is_file():
        print(f"Errore: input Markdown non e' un file: {input_path}", file=sys.stderr)
        return 1
    if input_path.resolve() == output_path.resolve(strict=False):
        print(
            "Errore: l'output non puo' coincidere con il file Markdown di input.",
            file=sys.stderr,
        )
        return 1

    try:
        markdown = input_path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        print(
            f"Errore: impossibile leggere l'input Markdown come UTF-8: {exc}",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"Errore: impossibile leggere l'input Markdown: {exc}", file=sys.stderr)
        return 1

    analysis = extract_judgment_metadata(markdown)
    output_markdown = (
        prepend_judgment_summary(markdown, analysis)
        if prepend
        else format_judgment_summary(analysis)
    )

    try:
        output_path.write_text(output_markdown, encoding="utf-8")
    except OSError as exc:
        print(f"Errore: impossibile scrivere l'output Markdown: {exc}", file=sys.stderr)
        return 1

    return 0


def analyze_casefile_cli(input_name: str, output_name: str) -> int:
    input_dir = Path(input_name).expanduser()
    output_dir = Path(output_name).expanduser()

    if not input_dir.exists():
        print(f"Errore: cartella non trovata: {input_dir}", file=sys.stderr)
        return 1
    if not input_dir.is_dir():
        print(f"Errore: il percorso non e' una cartella: {input_dir}", file=sys.stderr)
        return 1
    if output_dir.exists() and not output_dir.is_dir():
        print(
            f"Errore: il percorso di output esiste ed e' un file: {output_dir}",
            file=sys.stderr,
        )
        return 1

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Errore: impossibile creare la cartella di output: {exc}", file=sys.stderr)
        return 1

    analysis = analyze_case_folder(input_dir)

    json_path = default_casefile_json_path(output_dir)
    md_path = default_casefile_markdown_path(output_dir)

    try:
        write_casefile_analysis_json(analysis, json_path)
    except OSError as exc:
        print(f"Errore: impossibile scrivere il JSON: {exc}", file=sys.stderr)
        return 1

    try:
        write_casefile_analysis_markdown(analysis, md_path)
    except OSError as exc:
        print(f"Errore: impossibile scrivere il Markdown: {exc}", file=sys.stderr)
        return 1

    print(json_path)
    print(md_path)
    return 0


def convert_pdf_to_markdown_cli(
    input_pdf: str,
    output_dir: str,
    *,
    analyze_judgment_after_conversion: bool = False,
    ocr_timeout_seconds: int = DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
    ocr_jobs: int | None = None,
) -> int:
    """Run the normal PDF-to-Markdown worker without opening the GUI."""
    pdf_path = Path(input_pdf).expanduser()
    destination = Path(output_dir).expanduser()

    if not pdf_path.exists():
        print(f"Errore: input PDF non trovato: {pdf_path}", file=sys.stderr)
        return 1
    if not pdf_path.is_file():
        print(f"Errore: input PDF non e' un file: {pdf_path}", file=sys.stderr)
        return 1

    profile = PROFILES[DEFAULT_PROFILE]
    completed: dict[str, str] = {}
    failed: list[str] = []
    cancelled: list[str] = []

    def remember_completed(
        final_path: str,
        work_dir: str,
        duration: str,
        speed: str,
    ) -> None:
        completed.update({
            "final_path": final_path,
            "work_dir": work_dir,
            "duration": duration,
            "speed": speed,
        })

    worker = OcrWorker(
        str(pdf_path),
        str(destination),
        profile.block_size,
        profile,
        create_searchable=profile.create_searchable_pdf,
        use_searchable_as_source=profile.use_searchable_as_source,
        ocr_timeout_seconds=ocr_timeout_seconds,
        ocr_jobs=ocr_jobs,
    )
    worker.log_message.connect(print)
    worker.progress_changed.connect(
        lambda percent, eta: print(f"Avanzamento {percent}% - ETA {eta}")
    )
    worker.completed.connect(remember_completed)
    worker.failed.connect(failed.append)
    worker.cancelled.connect(cancelled.append)

    worker.run()

    if cancelled:
        print(f"Elaborazione annullata: {cancelled[-1]}", file=sys.stderr)
        return 1
    if failed or "final_path" not in completed:
        detail = failed[-1] if failed else "conversione non completata"
        print(f"Errore: {detail}", file=sys.stderr)
        return 1

    final_path = Path(completed["final_path"])
    print(f"Markdown creato: {final_path}")

    if analyze_judgment_after_conversion:
        try:
            write_judgment_analysis_for_markdown(
                final_path,
                final_path.parent,
                log_callback=print,
                update_manifest=True,
            )
        except (OSError, UnicodeError) as exc:
            print(f"Errore: analisi sentenza non completata: {exc}", file=sys.stderr)
            return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    cli_args = sys.argv[1:] if argv is None else argv
    args = parse_args(cli_args)

    if args.version:
        print(APP_VERSION)
        return 0

    if args.doctor:
        print(
            "La diagnostica completa è disponibile dal launcher installato:\n"
            "  gdlex-ocr --doctor"
        )
        return 0

    if args.analyze_casefile:
        return analyze_casefile_cli(args.analyze_casefile, args.output)

    if args.analyze_judgment:
        return analyze_judgment_markdown(
            args.analyze_judgment,
            args.output,
            args.prepend,
        )

    if args.input_pdf:
        return convert_pdf_to_markdown_cli(
            args.input_pdf,
            args.output,
            analyze_judgment_after_conversion=(
                args.analyze_judgment_after_conversion
            ),
            ocr_timeout_seconds=args.ocr_timeout,
            ocr_jobs=args.ocr_jobs,
        )

    app = QApplication([sys.argv[0], *cli_args])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GD LEX")
    app.setDesktopFileName("gdlex-ocr")
    icon = application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    apply_theme(app, load_theme_name())

    window = MainWindow(
        ocr_timeout_seconds=args.ocr_timeout,
        ocr_jobs=args.ocr_jobs,
    )
    if splash_disabled():
        window.show()
    else:
        splash = create_splash()
        splash.show()

        def show_main_window() -> None:
            splash.close()
            window.show()

        QTimer.singleShot(SPLASH_DURATION_MS, show_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
