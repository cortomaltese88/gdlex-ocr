"""Offline stress tests for run_process_with_incremental_output and related helpers.

No real OCR is executed; no user PDFs are read.
All subprocesses use sys.executable (the test Python interpreter).
"""

from __future__ import annotations

import inspect
import subprocess
import sys
import time
import unittest

from gdlex_ocr.searchable_pdf import (
    build_ocrmypdf_command,
    run_process_with_incremental_output,
)


class SubprocessEncodingTest(unittest.TestCase):
    """M1: Popen must declare explicit utf-8 encoding."""

    def test_popen_declares_explicit_utf8_encoding(self) -> None:
        source = inspect.getsource(run_process_with_incremental_output)
        self.assertIn('encoding="utf-8"', source)
        self.assertIn('errors="replace"', source)

    def test_unicode_non_ascii_output_is_captured(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('àèìòù — café\\n'); sys.stdout.flush()",
        ]
        received: list[str] = []
        returncode, output = run_process_with_incremental_output(
            command,
            timeout_seconds=10,
            line_callback=received.append,
        )
        self.assertEqual(0, returncode)
        self.assertTrue(
            any("café" in line for line in received),
            f"Unicode not found in received lines: {received}",
        )

    def test_unicode_in_full_output_string(self) -> None:
        command = [
            sys.executable,
            "-c",
            "print('straße'); print('日本語')",
        ]
        returncode, output = run_process_with_incremental_output(
            command, timeout_seconds=10
        )
        self.assertEqual(0, returncode)
        self.assertIn("straße", output)
        self.assertIn("日本語", output)


class SubprocessCallbackExceptionTest(unittest.TestCase):
    """M2: callback exception must terminate the process and re-raise the exception."""

    def test_callback_exception_is_reraised(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys, time; print('go', flush=True); time.sleep(60)",
        ]

        class BoomError(RuntimeError):
            pass

        def bad_callback(line: str) -> None:
            raise BoomError("callback failed")

        with self.assertRaises(BoomError):
            run_process_with_incremental_output(
                command,
                timeout_seconds=10,
                line_callback=bad_callback,
            )

    def test_callback_exception_terminates_process_quickly(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys, time; print('start', flush=True); time.sleep(60)",
        ]

        class BoomError(RuntimeError):
            pass

        def exploding_callback(line: str) -> None:
            raise BoomError("boom")

        start = time.monotonic()
        with self.assertRaises(BoomError):
            run_process_with_incremental_output(
                command,
                timeout_seconds=10,
                line_callback=exploding_callback,
            )
        elapsed = time.monotonic() - start
        # Must complete well before the 60-second sleep finishes
        self.assertLess(elapsed, 8.0, f"Process not terminated promptly ({elapsed:.1f}s)")

    def test_finally_block_contains_terminate_and_kill(self) -> None:
        source = inspect.getsource(run_process_with_incremental_output)
        self.assertIn("process.terminate()", source)
        self.assertIn("process.kill()", source)


class BuildOcrmypdfDashDashTest(unittest.TestCase):
    """L1: build_ocrmypdf_command must insert -- before the two path arguments."""

    def test_double_dash_present_in_command(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertIn("--", command)

    def test_double_dash_immediately_precedes_input_path(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        dd_idx = command.index("--")
        self.assertEqual("in.pdf", command[dd_idx + 1])
        self.assertEqual("out.pdf", command[dd_idx + 2])

    def test_paths_remain_last_two_elements(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        self.assertEqual("in.pdf", command[-2])
        self.assertEqual("out.pdf", command[-1])

    def test_path_starting_with_dashes_input_is_protected(self) -> None:
        command = build_ocrmypdf_command("--strano.pdf", "out.pdf")
        dd_idx = command.index("--")
        self.assertEqual("--strano.pdf", command[dd_idx + 1])

    def test_path_starting_with_dashes_output_is_protected(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "--weird-output.pdf")
        dd_idx = command.index("--")
        self.assertEqual("--weird-output.pdf", command[dd_idx + 2])

    def test_double_dash_is_at_third_from_last(self) -> None:
        command = build_ocrmypdf_command("in.pdf", "out.pdf")
        dd_idx = command.index("--")
        self.assertEqual(len(command) - 3, dd_idx)


class SubprocessStressTest(unittest.TestCase):
    """L3: stress and edge-case tests for run_process_with_incremental_output."""

    def test_1000_rapid_lines_all_received(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys\nfor i in range(1000):\n    print(i, flush=True)",
        ]
        received: list[str] = []
        returncode, output = run_process_with_incremental_output(
            command,
            timeout_seconds=30,
            line_callback=received.append,
        )
        self.assertEqual(0, returncode)
        self.assertEqual(1000, len(received))
        self.assertEqual("0", received[0].strip())
        self.assertEqual("999", received[-1].strip())

    def test_partial_line_without_trailing_newline_appears_in_output(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('no newline at end'); sys.stdout.flush()",
        ]
        returncode, output = run_process_with_incremental_output(
            command, timeout_seconds=10
        )
        self.assertEqual(0, returncode)
        self.assertIn("no newline at end", output)

    def test_timeout_raises_timeout_expired(self) -> None:
        command = [sys.executable, "-c", "import time; time.sleep(60)"]
        with self.assertRaises(subprocess.TimeoutExpired):
            run_process_with_incremental_output(command, timeout_seconds=1)

    def test_exit_code_7_is_returned_not_raised(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys; print('output line'); sys.stderr.write('err msg'); sys.exit(7)",
        ]
        received: list[str] = []
        returncode, output = run_process_with_incremental_output(
            command,
            timeout_seconds=10,
            line_callback=received.append,
        )
        self.assertEqual(7, returncode)
        self.assertIn("output line", output)
        # stderr merged into stdout via STDOUT redirect
        self.assertIn("err msg", output)

    def test_callback_receives_output_before_process_ends(self) -> None:
        command = [
            sys.executable,
            "-c",
            (
                "import time, sys; "
                "print('early', flush=True); "
                "time.sleep(0.3); "
                "print('late', flush=True)"
            ),
        ]
        timestamps: list[tuple[float, str]] = []

        def timed_callback(line: str) -> None:
            timestamps.append((time.monotonic(), line))

        returncode, _ = run_process_with_incremental_output(
            command, timeout_seconds=10, line_callback=timed_callback
        )
        end_time = time.monotonic()
        self.assertEqual(0, returncode)
        self.assertEqual(2, len(timestamps))
        early_time = timestamps[0][0]
        # 'early' must arrive materially before the process ends
        self.assertGreaterEqual(end_time - early_time, 0.25)

    def test_no_shell_equals_true_in_source(self) -> None:
        source = inspect.getsource(run_process_with_incremental_output)
        self.assertNotIn("shell=True", source)

    def test_returncode_zero_on_clean_exit(self) -> None:
        command = [sys.executable, "-c", "pass"]
        returncode, output = run_process_with_incremental_output(
            command, timeout_seconds=10
        )
        self.assertEqual(0, returncode)
        self.assertEqual("", output)


if __name__ == "__main__":
    unittest.main()
