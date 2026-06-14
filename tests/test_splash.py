"""Offline checks for startup splash configuration and bootstrap usage."""

from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from gdlex_ocr.icons import splash_icon_path
from gdlex_ocr.splash import SPLASH_DISABLE_ENV, splash_disabled


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SplashConfigurationTest(unittest.TestCase):
    def test_splash_icon_is_existing_raster_png(self) -> None:
        path = splash_icon_path()

        self.assertEqual("icon-128.png", path.name)
        self.assertEqual(".png", path.suffix)
        self.assertTrue(path.is_file())

    def test_splash_source_uses_raster_icon_helper(self) -> None:
        source = (PROJECT_ROOT / "gdlex_ocr" / "splash.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("splash_icon_path()", source)
        self.assertNotIn("icon.svg", source)

    def test_splash_is_enabled_when_environment_variable_is_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(splash_disabled())

    def test_truthy_environment_values_disable_splash(self) -> None:
        for value in ("1", "true", "TRUE", "yes", "Yes", "on", " ON "):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {SPLASH_DISABLE_ENV: value},
                    clear=True,
                ):
                    self.assertTrue(splash_disabled())

    def test_other_environment_values_do_not_disable_splash(self) -> None:
        for value in ("", "0", "false", "no", "off", "enabled", "2"):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {SPLASH_DISABLE_ENV: value},
                    clear=True,
                ):
                    self.assertFalse(splash_disabled())

    def test_app_checks_disable_flag_before_creating_splash(self) -> None:
        source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        main = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        disable_branch = next(
            node
            for node in ast.walk(main)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Call)
            and isinstance(node.test.func, ast.Name)
            and node.test.func.id == "splash_disabled"
        )
        create_calls = [
            node
            for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "create_splash"
        ]

        self.assertEqual(1, len(create_calls))
        self.assertLess(disable_branch.lineno, create_calls[0].lineno)
        self.assertIn(create_calls[0], list(ast.walk(disable_branch.orelse[0])))


if __name__ == "__main__":
    unittest.main()
