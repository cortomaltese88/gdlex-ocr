"""Offline tests for optional OCR backend discovery and commands."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from gdlex_ocr.ocr_backends import (
    OcrBackend,
    OcrBackendError,
    backend_manifest,
    build_backend_command,
    detect_ocr_backend,
    run_ocr_backend,
)


class OcrBackendDetectionTest(unittest.TestCase):
    def test_auto_selects_ocrmypdf_when_present(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            side_effect=lambda name: (
                "/usr/bin/ocrmypdf" if name == "ocrmypdf" else None
            ),
        ):
            backend = detect_ocr_backend("auto")

        self.assertEqual("ocrmypdf", backend.name)
        self.assertTrue(backend.available)
        self.assertTrue(backend.runnable)

    def test_missing_ocrmypdf_has_clear_warning(self) -> None:
        with patch("gdlex_ocr.ocr_backends.shutil.which", return_value=None):
            backend = detect_ocr_backend("ocrmypdf")

        self.assertFalse(backend.available)
        self.assertIn("non disponibile", backend.warnings[0])

    def test_external_backend_requires_executable_and_placeholders(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            return_value="/opt/bin/local-ocr",
        ):
            backend = detect_ocr_backend(
                "external",
                external_command=(
                    "local-ocr --input {input} --output {output} "
                    "--language {language}"
                ),
            )

        self.assertTrue(backend.available)
        command = build_backend_command(
            backend,
            "input.pdf",
            "output.pdf",
            "ita",
        )
        self.assertEqual("/opt/bin/local-ocr", command[0])
        self.assertIn("input.pdf", command)
        self.assertIn("output.pdf", command)
        self.assertIn("ita", command)

    def test_external_backend_without_placeholders_is_unavailable(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            return_value="/opt/bin/local-ocr",
        ):
            backend = detect_ocr_backend(
                "external",
                external_command="local-ocr input.pdf output.pdf",
            )

        self.assertFalse(backend.available)
        self.assertIn("{input}", backend.warnings[0])

    def test_masterpdf_is_detected_but_never_runnable(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            side_effect=lambda name: (
                "/usr/bin/masterpdfeditor5"
                if name == "masterpdfeditor5"
                else None
            ),
        ):
            backend = detect_ocr_backend("masterpdf")

        self.assertTrue(backend.available)
        self.assertFalse(backend.runnable)
        self.assertIn("workflow manuale", backend.warnings[0])

    def test_tesseract_is_diagnostic_not_pdf_backend(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            return_value="/usr/bin/tesseract",
        ):
            backend = detect_ocr_backend("tesseract")

        self.assertTrue(backend.available)
        self.assertFalse(backend.runnable)
        self.assertIn("OCRmyPDF", backend.warnings[0])

    def test_ocrmypdf_backend_command_includes_jobs_when_configured(
        self,
    ) -> None:
        backend = OcrBackend(
            "ocrmypdf",
            True,
            "/usr/bin/ocrmypdf",
            None,
            True,
        )

        command = build_backend_command(
            backend,
            "input.pdf",
            "output.pdf",
            "ita",
            jobs=3,
        )

        self.assertEqual("/usr/bin/ocrmypdf", command[0])
        self.assertIn("--jobs", command)
        self.assertEqual("3", command[command.index("--jobs") + 1])

    def test_proprietary_backend_is_not_launched(self) -> None:
        with (
            patch(
                "gdlex_ocr.ocr_backends.shutil.which",
                side_effect=lambda name: (
                    "/usr/bin/masterpdfeditor5"
                    if name == "masterpdfeditor5"
                    else None
                ),
            ),
            patch("gdlex_ocr.ocr_backends.subprocess.Popen") as popen,
        ):
            backend = detect_ocr_backend("masterpdf")
            with self.assertRaises(OcrBackendError):
                run_ocr_backend(backend, "in.pdf", "out.pdf")

        popen.assert_not_called()

    def test_manifest_contains_backend_state_without_document_content(self) -> None:
        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            return_value="/usr/bin/ocrmypdf",
        ):
            backend = detect_ocr_backend("ocrmypdf")

        metadata = backend_manifest(backend)
        self.assertEqual("ocrmypdf", metadata["name"])
        self.assertTrue(metadata["available"])
        self.assertFalse(metadata["used"])
        self.assertNotIn("document text", str(metadata))

    def test_external_backend_run_uses_fake_subprocess_only(self) -> None:
        class SuccessfulProcess:
            returncode = 0

            @staticmethod
            def communicate(timeout=None):
                return ("", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output = root / "output.pdf"
            output.write_bytes(b"%PDF")
            with (
                patch(
                    "gdlex_ocr.ocr_backends.shutil.which",
                    return_value="/opt/bin/local-ocr",
                ),
                patch(
                    "gdlex_ocr.ocr_backends.subprocess.Popen",
                    return_value=SuccessfulProcess(),
                ) as popen,
            ):
                backend = detect_ocr_backend(
                    "external",
                    external_command="local-ocr {input} {output}",
                )
                result = run_ocr_backend(
                    backend,
                    root / "input.pdf",
                    output,
                )

        self.assertEqual("external", result.name)
        self.assertIsInstance(popen.call_args.args[0], list)
        self.assertIsNot(popen.call_args.kwargs.get("shell"), True)

    def test_ocrmypdf_run_uses_configured_timeout_and_jobs(self) -> None:
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output = root / "output.pdf"
            output.write_bytes(b"%PDF")
            backend = OcrBackend(
                "ocrmypdf",
                True,
                "/usr/bin/ocrmypdf",
                None,
                True,
            )
            process = MagicMock()
            process.returncode = 0
            process.communicate.return_value = ("", None)

            with patch(
                "gdlex_ocr.ocr_backends.subprocess.Popen",
                return_value=process,
            ) as popen:
                run_ocr_backend(
                    backend,
                    root / "input.pdf",
                    output,
                    timeout_seconds=7,
                    jobs=5,
                )

        command = popen.call_args.args[0]
        self.assertIn("--jobs", command)
        self.assertEqual("5", command[command.index("--jobs") + 1])
        process.communicate.assert_called_once_with(timeout=7)

    def test_timeout_kills_process_and_raises_ocr_backend_error(self) -> None:
        import subprocess as _subprocess
        from unittest.mock import MagicMock

        with patch(
            "gdlex_ocr.ocr_backends.shutil.which",
            return_value="/usr/bin/ocrmypdf",
        ):
            backend = detect_ocr_backend("ocrmypdf")

        with patch(
            "gdlex_ocr.ocr_backends.subprocess.Popen",
        ) as mock_popen:
            mock_proc = MagicMock()
            # First call raises TimeoutExpired; second call (drain after kill) succeeds.
            mock_proc.communicate.side_effect = [
                _subprocess.TimeoutExpired(cmd="ocrmypdf", timeout=1),
                ("", None),
            ]
            mock_popen.return_value = mock_proc

            with self.assertRaises(OcrBackendError) as ctx:
                run_ocr_backend(backend, "in.pdf", "out.pdf", timeout_seconds=1)

            self.assertIn("timeout", str(ctx.exception).lower())
            mock_proc.kill.assert_called_once()

    def test_rejects_non_positive_timeout(self) -> None:
        backend = OcrBackend(
            "ocrmypdf",
            True,
            "/usr/bin/ocrmypdf",
            None,
            True,
        )

        with self.assertRaisesRegex(ValueError, "maggiore di 0"):
            run_ocr_backend(backend, "in.pdf", "out.pdf", timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
