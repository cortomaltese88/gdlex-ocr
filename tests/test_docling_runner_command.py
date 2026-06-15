"""Offline tests for Docling command construction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gdlex_ocr.docling_runner import (
    DoclingRunner,
    build_docling_command,
)
from gdlex_ocr.profiles import PROFILES


class _SuccessfulProcess:
    pid = 12345
    stdout: list[str] = []

    def wait(self, timeout: int | None = None) -> int:
        return 0

    def poll(self) -> int | None:
        return None


class DoclingCommandTest(unittest.TestCase):
    def test_command_contains_balanced_options(self) -> None:
        command = build_docling_command(
            "/opt/bin/docling",
            "input.pdf",
            "output",
            table_mode="fast",
            num_threads=10,
            page_batch_size=6,
            enable_ocr=True,
            enrich_picture=False,
            enrich_chart=False,
        )

        self.assertIsInstance(command, list)
        self.assertEqual("/opt/bin/docling", command[0])
        self.assertOptionValue(command, "--image-export-mode", "placeholder")
        self.assertIn("--ocr", command)
        self.assertNotIn("--no-ocr", command)
        self.assertOptionValue(command, "--num-threads", "10")
        self.assertOptionValue(command, "--page-batch-size", "6")
        self.assertOptionValue(command, "--table-mode", "fast")
        self.assertIn("--no-enrich-picture-classes", command)
        self.assertIn("--no-enrich-picture-description", command)
        self.assertIn("--no-enrich-chart-extraction", command)

    def test_command_supports_no_ocr_and_accurate_tables(self) -> None:
        command = build_docling_command(
            "docling",
            "input.pdf",
            "output",
            table_mode="accurate",
            enable_ocr=False,
        )

        self.assertIn("--no-ocr", command)
        self.assertNotIn("--ocr", command)
        self.assertOptionValue(command, "--table-mode", "accurate")

    def test_accurate_text_profile_uses_placeholder_without_enrichment(self) -> None:
        profile = PROFILES["Accurato testo"]
        command = build_docling_command(
            "docling",
            "input.pdf",
            "output",
            table_mode=profile.table_mode,
            num_threads=profile.num_threads,
            page_batch_size=profile.page_batch_size,
            enable_ocr=profile.enable_ocr,
            enrich_picture=profile.enrich_picture,
            enrich_chart=profile.enrich_chart,
        )

        self.assertOptionValue(command, "--image-export-mode", "placeholder")
        self.assertNotIn("embedded", command)
        self.assertIn("--no-enrich-picture-classes", command)
        self.assertIn("--no-enrich-picture-description", command)
        self.assertIn("--no-enrich-chart-extraction", command)

    def test_runner_uses_argument_list_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "synthetic.pdf"
            output = root / "output"
            output.mkdir()
            expected_markdown = output / "synthetic.md"
            expected_markdown.write_text("test", encoding="utf-8")

            with (
                patch.object(
                    DoclingRunner,
                    "find_executable",
                    return_value="/opt/bin/docling",
                ),
                patch(
                    "gdlex_ocr.docling_runner.subprocess.Popen",
                    return_value=_SuccessfulProcess(),
                ) as popen,
            ):
                result = DoclingRunner().run(source, output)

        self.assertEqual(expected_markdown, result)
        command = popen.call_args.args[0]
        kwargs = popen.call_args.kwargs
        self.assertIsInstance(command, list)
        self.assertIsNot(kwargs.get("shell"), True)

    def assertOptionValue(
        self,
        command: list[str],
        option: str,
        expected: str,
    ) -> None:
        index = command.index(option)
        self.assertEqual(expected, command[index + 1])


if __name__ == "__main__":
    unittest.main()
