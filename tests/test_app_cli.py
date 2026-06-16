"""Command-line behavior for the application entry point."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import app
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


if __name__ == "__main__":
    unittest.main()
