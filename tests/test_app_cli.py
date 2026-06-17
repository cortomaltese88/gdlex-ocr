"""Command-line behavior for the application entry point."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import app
from gdlex_ocr.searchable_pdf import DEFAULT_OCRMYPDF_TIMEOUT_SECONDS
from gdlex_ocr.version import APP_VERSION


class AppCliTest(unittest.TestCase):
    def test_version_prints_version_without_starting_gui(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), patch(
            "app.QApplication",
            side_effect=AssertionError("GUI should not start for --version"),
        ):
            status = app.main(["--version"])

        self.assertEqual(0, status)
        self.assertEqual(f"{APP_VERSION}\n", output.getvalue())

    def test_doctor_prints_redirect_without_starting_gui(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), patch(
            "app.QApplication",
            side_effect=AssertionError("GUI should not start for --doctor"),
        ):
            status = app.main(["--doctor"])

        self.assertEqual(0, status)
        self.assertIn("gdlex-ocr --doctor", output.getvalue())
        self.assertIn("launcher", output.getvalue())

    def test_no_arguments_still_starts_gui(self) -> None:
        with patch("app.QApplication") as qapplication, patch(
            "app.application_icon"
        ), patch("app.apply_theme"), patch("app.load_theme_name"), patch(
            "app.MainWindow"
        ) as main_window, patch("app.splash_disabled", return_value=True):
            qapplication.return_value.exec.return_value = 0

            status = app.main([])

        self.assertEqual(0, status)
        qapplication.assert_called_once()
        main_window.return_value.show.assert_called_once()

    def test_help_documents_ocr_options_without_starting_gui(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), patch(
            "app.QApplication",
            side_effect=AssertionError("GUI should not start for --help"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                app.main(["--help"])

        self.assertEqual(0, ctx.exception.code)
        self.assertIn("--ocr-timeout SECONDS", output.getvalue())
        self.assertIn("--ocr-jobs N", output.getvalue())

    def test_ocr_cli_options_are_passed_to_main_window(self) -> None:
        with patch("app.QApplication") as qapplication, patch(
            "app.application_icon"
        ), patch("app.apply_theme"), patch("app.load_theme_name"), patch(
            "app.MainWindow"
        ) as main_window, patch("app.splash_disabled", return_value=True):
            qapplication.return_value.exec.return_value = 0

            status = app.main(["--ocr-timeout", "42", "--ocr-jobs", "3"])

        self.assertEqual(0, status)
        main_window.assert_called_once_with(
            ocr_timeout_seconds=42,
            ocr_jobs=3,
        )

    def test_default_ocr_timeout_is_preserved(self) -> None:
        args = app.parse_args([])

        self.assertEqual(DEFAULT_OCRMYPDF_TIMEOUT_SECONDS, args.ocr_timeout)
        self.assertIsNone(args.ocr_jobs)

    def test_rejects_non_positive_ocr_timeout(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.parse_args(["--ocr-timeout", "0"])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("--ocr-timeout", error.getvalue())
        self.assertIn("maggiore di 0", error.getvalue())

    def test_rejects_non_positive_ocr_jobs(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.parse_args(["--ocr-jobs", "-1"])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("--ocr-jobs", error.getvalue())
        self.assertIn("maggiore di 0", error.getvalue())


if __name__ == "__main__":
    unittest.main()
