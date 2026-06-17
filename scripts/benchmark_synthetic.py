#!/usr/bin/env python3
"""Generate local synthetic PDFs and benchmark repeatable GD LEX OCR steps."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gdlex_ocr.pdf_splitter import count_pdf_pages, split_pdf
from gdlex_ocr.profiles import PROFILES
from gdlex_ocr.searchable_pdf import (
    DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
    INSTALL_HINT,
    is_ocrmypdf_available,
    run_ocrmypdf,
    validate_ocrmypdf_jobs,
    validate_ocrmypdf_timeout_seconds,
)
from gdlex_ocr.version import APP_VERSION


DEFAULT_OUTPUT_DIR = Path("tmp") / "benchmark-synthetic"
DEFAULT_CASES = ("searchable", "image")
SUPPORTED_CASES = frozenset(DEFAULT_CASES)


class BenchmarkError(RuntimeError):
    """Raised when the synthetic benchmark cannot run."""


class OptionalDependencyError(BenchmarkError):
    """Raised when an optional fixture dependency is missing."""


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("deve essere maggiore di 0")
    return parsed


def parse_cases(value: str) -> tuple[str, ...]:
    cases = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    if not cases:
        raise argparse.ArgumentTypeError("specificare almeno un caso")
    unknown = sorted(set(cases) - SUPPORTED_CASES)
    if unknown:
        raise argparse.ArgumentTypeError(
            "casi non supportati: " + ", ".join(unknown)
        )
    return cases


def create_searchable_pdf(path: Path, pages: int) -> None:
    """Create a deterministic text-layer PDF using only pypdf."""
    writer = PdfWriter()
    font_ref = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )

    for page_number in range(1, pages + 1):
        page = writer.add_blank_page(width=595, height=842)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_ref}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(_page_text_stream(page_number).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    writer.add_metadata(
        {
            "/Title": "GD LEX OCR synthetic searchable benchmark",
            "/Creator": "scripts/benchmark_synthetic.py",
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        writer.write(output)


def create_image_like_pdf(path: Path, pages: int) -> None:
    """Create a deterministic raster PDF; requires optional Pillow."""
    image_module, draw_module = _require_pillow()
    images = []
    width, height = 1240, 1754

    for page_number in range(1, pages + 1):
        image = image_module.new("RGB", (width, height), "white")
        draw = draw_module.Draw(image)
        draw.rectangle((90, 80, width - 90, height - 80), outline=(0, 0, 0), width=3)
        draw.text((130, 130), f"GD LEX OCR synthetic raster page {page_number}", fill=(0, 0, 0))
        for row in range(8):
            y = 230 + row * 120
            draw.rectangle((130, y, width - 130, y + 50), fill=(230, 230, 230))
            draw.text(
                (150, y + 14),
                f"Simulated scanned line {row + 1} on page {page_number}",
                fill=(0, 0, 0),
            )
        images.append(image)

    path.parent.mkdir(parents=True, exist_ok=True)
    first, *rest = images
    first.save(path, "PDF", resolution=150.0, save_all=True, append_images=rest)


def _require_pillow() -> tuple[Any, Any]:
    try:
        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
    except ImportError as exc:
        raise OptionalDependencyError(
            "Pillow non disponibile: impossibile generare il PDF raster "
            "sintetico. Installa le dipendenze della venv del progetto oppure "
            "usa --cases searchable."
        ) from exc
    return image_module, draw_module


def _page_text_stream(page_number: int) -> str:
    lines = [
        f"GD LEX OCR synthetic searchable page {page_number}",
        "This PDF contains deterministic text and no real document content.",
        "CAPITOLO SINTETICO",
        f"Article {page_number}. Repeatable local benchmark fixture.",
        "The quick profile can read this without OCR.",
    ]
    escaped_lines = [_pdf_literal(line) for line in lines]
    operations = ["BT", "/F1 14 Tf", "72 760 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            operations.append("0 -24 Td")
        operations.append(f"{line} Tj")
    operations.append("ET")
    return "\n".join(operations)


def _pdf_literal(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )
    return f"({escaped})"


def generate_fixtures(output_dir: Path, pages: int, cases: tuple[str, ...]) -> dict[str, Path]:
    fixtures_dir = output_dir / "fixtures"
    fixture_paths: dict[str, Path] = {}
    if "searchable" in cases:
        path = fixtures_dir / "synthetic_searchable.pdf"
        create_searchable_pdf(path, pages)
        fixture_paths["searchable"] = path
    if "image" in cases:
        path = fixtures_dir / "synthetic_image.pdf"
        create_image_like_pdf(path, pages)
        fixture_paths["image"] = path
    return fixture_paths


def inspect_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(path)
    page_count = len(reader.pages)
    extracted_chars = 0
    pages_with_text = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        stripped = text.strip()
        extracted_chars += len(stripped)
        if stripped:
            pages_with_text += 1
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "pages": page_count,
        "pages_with_text": pages_with_text,
        "extracted_chars": extracted_chars,
    }


def run_case(
    case_name: str,
    pdf_path: Path,
    output_dir: Path,
    *,
    runs: int,
    block_size: int,
    run_ocr: bool,
    ocr_language: str,
    ocr_timeout: int,
    ocr_jobs: int | None,
) -> dict[str, Any]:
    case_runs = []
    for run_index in range(1, runs + 1):
        run_dir = output_dir / "runs" / case_name / f"run_{run_index:02d}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True)

        started = time.perf_counter()
        page_count = count_pdf_pages(pdf_path)
        blocks = split_pdf(pdf_path, run_dir / "blocks", pages_per_block=block_size)
        inspection = inspect_pdf(pdf_path)
        elapsed = time.perf_counter() - started

        run_result: dict[str, Any] = {
            "run": run_index,
            "seconds": round(elapsed, 6),
            "pages_per_minute": _pages_per_minute(page_count, elapsed),
            "page_count": page_count,
            "block_count": len(blocks),
            "pages_with_text": inspection["pages_with_text"],
            "extracted_chars": inspection["extracted_chars"],
        }

        if run_ocr and case_name == "image":
            run_result["ocrmypdf"] = _run_synthetic_ocr(
                pdf_path,
                run_dir / "ocr" / "synthetic_image_searchable.pdf",
                language=ocr_language,
                timeout_seconds=ocr_timeout,
                jobs=ocr_jobs,
            )
        case_runs.append(run_result)

    best = min(item["seconds"] for item in case_runs)
    average = sum(item["seconds"] for item in case_runs) / len(case_runs)
    return {
        "case": case_name,
        "input": inspect_pdf(pdf_path),
        "runs": case_runs,
        "best_seconds": round(best, 6),
        "average_seconds": round(average, 6),
    }


def _run_synthetic_ocr(
    input_pdf: Path,
    output_pdf: Path,
    *,
    language: str,
    timeout_seconds: int,
    jobs: int | None,
) -> dict[str, Any]:
    if not is_ocrmypdf_available():
        raise OptionalDependencyError(
            "OCRmyPDF non disponibile: impossibile eseguire --run-ocr. "
            f"{INSTALL_HINT}"
        )
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    run_ocrmypdf(
        input_pdf,
        output_pdf,
        language=language,
        jobs=jobs,
        timeout_seconds=timeout_seconds,
    )
    elapsed = time.perf_counter() - started
    inspection = inspect_pdf(output_pdf)
    return {
        "seconds": round(elapsed, 6),
        "pages_per_minute": _pages_per_minute(inspection["pages"], elapsed),
        "output": inspection,
    }


def _pages_per_minute(pages: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return round(pages / (seconds / 60), 3)


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    profile = PROFILES[args.profile]
    block_size = args.block_size or profile.block_size
    ocr_timeout = validate_ocrmypdf_timeout_seconds(args.ocr_timeout)
    ocr_jobs = validate_ocrmypdf_jobs(args.ocr_jobs)

    fixtures = generate_fixtures(args.output_dir, args.pages, args.cases)
    results = [
        run_case(
            case_name,
            pdf_path,
            args.output_dir,
            runs=args.runs,
            block_size=block_size,
            run_ocr=args.run_ocr,
            ocr_language=args.ocr_language,
            ocr_timeout=ocr_timeout,
            ocr_jobs=ocr_jobs,
        )
        for case_name, pdf_path in fixtures.items()
    ]

    result_json = args.result_json or args.output_dir / "results" / "latest.json"
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_version": APP_VERSION,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "method": "synthetic local fixture benchmark",
        "output_dir": str(args.output_dir),
        "pages": args.pages,
        "runs": args.runs,
        "profile": asdict(profile),
        "block_size": block_size,
        "ocr": {
            "enabled": args.run_ocr,
            "language": args.ocr_language,
            "timeout_seconds": ocr_timeout,
            "jobs": ocr_jobs,
        },
        "result_json": str(result_json),
        "fixtures": {name: str(path) for name, path in fixtures.items()},
        "results": results,
    }
    result_json.parent.mkdir(parents=True, exist_ok=True)
    result_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Genera PDF sintetici locali e misura passaggi ripetibili "
            "di gdlex-ocr senza documenti reali."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"directory per fixture e risultati (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--result-json",
        type=Path,
        default=None,
        help="file JSON dei risultati runtime",
    )
    parser.add_argument(
        "--pages",
        type=positive_int,
        default=6,
        help="numero di pagine sintetiche per fixture",
    )
    parser.add_argument(
        "--runs",
        type=positive_int,
        default=3,
        help="ripetizioni per ogni caso",
    )
    parser.add_argument(
        "--cases",
        type=parse_cases,
        default=DEFAULT_CASES,
        help="casi separati da virgola: searchable,image",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="PDF già ricercabile",
        help="profilo gdlex-ocr da registrare e usare per il block size",
    )
    parser.add_argument(
        "--block-size",
        type=positive_int,
        help="override pagine per blocco; default dal profilo scelto",
    )
    parser.add_argument(
        "--run-ocr",
        action="store_true",
        help="esegue OCRmyPDF sulla fixture raster sintetica",
    )
    parser.add_argument(
        "--ocr-language",
        default="ita",
        help="lingua OCRmyPDF per --run-ocr",
    )
    parser.add_argument(
        "--ocr-timeout",
        type=positive_int,
        default=DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
        help="timeout OCRmyPDF in secondi",
    )
    parser.add_argument(
        "--ocr-jobs",
        type=positive_int,
        help="numero job OCRmyPDF per --run-ocr",
    )
    return parser


def print_summary(report: dict[str, Any]) -> None:
    print("Benchmark sintetico completato")
    print(f"Output: {report['output_dir']}")
    print(f"Risultati JSON: {report['result_json']}")
    print(f"Profilo registrato: {report['profile']['name']}")
    for result in report["results"]:
        input_info = result["input"]
        print(
            "- {case}: {pages} pagine, {runs} run, best {best:.6f}s, "
            "media {avg:.6f}s, testo estraibile {text_pages}/{pages}".format(
                case=result["case"],
                pages=input_info["pages"],
                runs=len(result["runs"]),
                best=result["best_seconds"],
                avg=result["average_seconds"],
                text_pages=input_info["pages_with_text"],
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args)
    except BenchmarkError as exc:
        print(f"Errore benchmark: {exc}", file=sys.stderr)
        return 2
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
