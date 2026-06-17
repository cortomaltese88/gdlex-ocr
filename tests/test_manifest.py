"""Offline tests for gdlex_ocr/manifest.py — no OCR, no network."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class FileSha256Test(unittest.TestCase):
    def test_known_digest(self) -> None:
        from gdlex_ocr.manifest import file_sha256

        with self.subTest("import"):
            self.assertTrue(callable(file_sha256))

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "sample.bin"
            data = b"hello world"
            f.write_bytes(data)
            expected = hashlib.sha256(data).hexdigest()
            self.assertEqual(expected, file_sha256(f))

    def test_empty_file(self) -> None:
        from gdlex_ocr.manifest import file_sha256

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "empty.bin"
            f.write_bytes(b"")
            self.assertEqual(hashlib.sha256(b"").hexdigest(), file_sha256(f))

    def test_multi_chunk_file(self) -> None:
        from gdlex_ocr.manifest import file_sha256

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "big.bin"
            data = b"x" * (65536 * 3 + 7)
            f.write_bytes(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), file_sha256(f))


def _fake_profile() -> MagicMock:
    p = MagicMock()
    p.name = "Bilanciato"
    p.block_size = 15
    p.num_threads = 10
    p.page_batch_size = 6
    p.enable_ocr = True
    p.table_mode = "fast"
    p.enrich_picture = False
    p.enrich_chart = False
    p.structure_markdown = True
    return p


class BuildInitialManifestTest(unittest.TestCase):
    def _build(self, tmpdir: Path) -> dict:
        from gdlex_ocr.manifest import build_initial_manifest

        pdf = tmpdir / "fascicolo.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        return build_initial_manifest(
            pdf_path=pdf,
            output_dir=tmpdir / "output",
            profile=_fake_profile(),
            pages_per_block=15,
            create_searchable=True,
            ocr_language="ita",
            app_version="0.1.2",
        )

    def test_top_level_keys_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        for key in ("schema_version", "app", "job", "input", "profile",
                    "processing", "outputs", "warnings", "errors"):
            with self.subTest(key=key):
                self.assertIn(key, m)

    def test_schema_version_is_integer(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertIsInstance(m["schema_version"], int)

    def test_app_name_and_version(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertEqual("GD LEX OCR", m["app"]["name"])
        self.assertEqual("0.1.2", m["app"]["version"])

    def test_initial_status_is_running(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertEqual("running", m["job"]["status"])

    def test_input_fields(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertEqual("fascicolo.pdf", m["input"]["filename"])
        self.assertIsInstance(m["input"]["sha256"], str)
        self.assertEqual(64, len(m["input"]["sha256"]))
        self.assertIsNone(m["input"]["page_count"])

    def test_profile_options_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        opts = m["profile"]["options"]
        self.assertEqual(15, opts["block_size"])
        self.assertEqual("fast", opts["table_mode"])

    def test_legal_dossier_profile_is_recorded_in_manifest(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest
        from gdlex_ocr.profiles import PROFILES

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "fascicolo.pdf"
            pdf.write_bytes(b"%PDF")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=root / "output",
                profile=PROFILES["Fascicolo legale"],
                pages_per_block=25,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.7",
            )

        self.assertEqual("Fascicolo legale", m["profile"]["name"])
        self.assertEqual(25, m["profile"]["options"]["block_size"])
        self.assertFalse(m["profile"]["options"]["enable_ocr"])
        self.assertEqual("accurate", m["profile"]["options"]["table_mode"])

    def test_processing_flags(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        proc = m["processing"]
        self.assertTrue(proc["ocr_searchable_pdf_requested"])
        self.assertEqual("ita", proc["ocr_language"])
        self.assertEqual(0, proc["blocks_completed"])

    def test_outputs_contain_run_log_and_manifest(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertIn("run_log", m["outputs"])
        self.assertIn("manifest", m["outputs"])
        self.assertIn("run.log", m["outputs"]["run_log"])
        self.assertIn("manifest.json", m["outputs"]["manifest"])

    def test_legacy_output_layout_metadata_is_additive(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))

        self.assertEqual(
            {
                "structured": False,
                "job_output_dir": m["outputs"]["output_dir"],
            },
            m["output_layout"],
        )

    def test_structured_output_paths_are_coherent(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "fascicolo.pdf"
            pdf.write_bytes(b"%PDF")
            job_dir = root / "output" / "fascicolo_ocr_job"
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=job_dir,
                profile=_fake_profile(),
                pages_per_block=15,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.3",
                structured_output=True,
            )

            self.assertEqual(1, m["schema_version"])
            self.assertTrue(m["output_layout"]["structured"])
            self.assertEqual(str(job_dir), m["outputs"]["output_dir"])
            self.assertEqual(
                str(job_dir),
                m["output_layout"]["job_output_dir"],
            )
            self.assertEqual(
                str(job_dir / "run.log"),
                m["outputs"]["run_log"],
            )
            self.assertEqual(
                str(job_dir / "manifest.json"),
                m["outputs"]["manifest"],
            )

    def test_no_document_content(self) -> None:
        """Manifest must not contain OCR text or extracted document content."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        serialised = json.dumps(m)
        self.assertNotIn("%PDF-1.4 fake", serialised)

    def test_warnings_and_errors_are_empty_lists(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        self.assertEqual([], m["warnings"])
        self.assertEqual([], m["errors"])

    def test_output_sha256_initial_values_are_none(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        sha = m["output_sha256"]
        self.assertIsNone(sha["markdown"])
        self.assertIsNone(sha["searchable_pdf"])
        self.assertIsNone(sha["index_markdown"])

    def test_bookmark_metadata_is_additive(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))

        self.assertEqual(
            {
                "strategy": None,
                "count": 0,
                "fallback": False,
                "warnings": [],
                "reason": None,
            },
            m["bookmarks"],
        )

    def test_bookmarks_reason_is_none_when_searchable_requested(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "doc.pdf"
            pdf.write_bytes(b"%PDF")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=root / "out",
                profile=_fake_profile(),
                pages_per_block=10,
                create_searchable=True,
                ocr_language="ita",
                app_version="0.1.4",
            )

        self.assertIsNone(m["bookmarks"]["reason"])

    def test_bookmarks_reason_when_searchable_not_requested(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "doc.pdf"
            pdf.write_bytes(b"%PDF")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=root / "out",
                profile=_fake_profile(),
                pages_per_block=10,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.4",
            )

        self.assertEqual("searchable_pdf_not_requested", m["bookmarks"]["reason"])

    def test_markdown_structure_metadata_is_additive(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))

        self.assertEqual(
            {
                "enabled": True,
                "post_processed": False,
                "headings_added": 0,
                "strategy": "conservative_heading_detection",
                "warnings": [],
            },
            m["markdown_structure"],
        )
        self.assertTrue(m["profile"]["options"]["structure_markdown"])

    def test_ocr_backend_metadata_is_additive(self) -> None:
        from gdlex_ocr.searchable_pdf import DEFAULT_OCRMYPDF_TIMEOUT_SECONDS

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))

        self.assertEqual(
            {
                "requested": "auto",
                "name": None,
                "command": None,
                "available": False,
                "used": False,
                "use_as_source": False,
                "ocrmypdf_timeout_seconds": DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
                "ocrmypdf_jobs": None,
                "warnings": [],
            },
            m["ocr_backend"],
        )

    def test_ocrmypdf_runtime_options_are_auditable(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "doc.pdf"
            pdf.write_bytes(b"%PDF")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=root / "out",
                profile=_fake_profile(),
                pages_per_block=10,
                create_searchable=True,
                ocr_language="ita",
                app_version="0.1.4",
                ocrmypdf_timeout_seconds=42,
                ocrmypdf_jobs=3,
            )

        self.assertEqual(42, m["ocr_backend"]["ocrmypdf_timeout_seconds"])
        self.assertEqual(3, m["ocr_backend"]["ocrmypdf_jobs"])

    def test_job_id_is_uuid_string(self) -> None:
        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as td:
            m = self._build(Path(td))
        job_id = m["job"]["id"]
        self.assertIsInstance(job_id, str)
        uuid.UUID(job_id)

    def test_two_jobs_have_different_ids(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m1 = self._build(Path(td))
            m2 = self._build(Path(td))
        self.assertNotEqual(m1["job"]["id"], m2["job"]["id"])


class WriteReadManifestTest(unittest.TestCase):
    def test_write_produces_valid_utf8_json(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, write_manifest

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "output"
            out.mkdir()
            pdf = Path(td) / "doc.pdf"
            pdf.write_bytes(b"%PDF")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=10,
                create_searchable=False,
                ocr_language="eng",
                app_version="0.1.2",
            )
            path = write_manifest(m, out)
            self.assertTrue(path.is_file())
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        self.assertEqual(m["job"]["id"], parsed["job"]["id"])

    def test_write_manifest_is_indented(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, write_manifest

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            pdf = Path(td) / "x.pdf"
            pdf.write_bytes(b"")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=5,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.2",
            )
            path = write_manifest(m, out)
            raw = path.read_text(encoding="utf-8")
        self.assertIn("\n", raw)
        self.assertIn("  ", raw)

    def test_status_can_be_updated_to_success(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, write_manifest

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            pdf = Path(td) / "x.pdf"
            pdf.write_bytes(b"")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=5,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.2",
            )
            m["job"]["status"] = "success"
            m["job"]["duration_seconds"] = 42.0
            write_manifest(m, out)
            parsed = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("success", parsed["job"]["status"])
        self.assertEqual(42.0, parsed["job"]["duration_seconds"])

    def test_status_can_be_updated_to_failed(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, write_manifest

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            pdf = Path(td) / "x.pdf"
            pdf.write_bytes(b"")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=5,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.2",
            )
            m["job"]["status"] = "failed"
            m["errors"].append("Errore sintetico")
            write_manifest(m, out)
            parsed = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("failed", parsed["job"]["status"])
        self.assertIn("Errore sintetico", parsed["errors"])


class SafeWriteManifestTest(unittest.TestCase):
    def test_returns_true_on_success(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, safe_write_manifest

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            pdf = Path(td) / "x.pdf"
            pdf.write_bytes(b"")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=5,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.2",
            )
            result = safe_write_manifest(m, out)
        self.assertTrue(result)

    def test_returns_false_on_permission_error(self) -> None:
        from gdlex_ocr.manifest import build_initial_manifest, safe_write_manifest
        from unittest.mock import patch

        import tempfile

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            pdf = Path(td) / "x.pdf"
            pdf.write_bytes(b"")
            m = build_initial_manifest(
                pdf_path=pdf,
                output_dir=out,
                profile=_fake_profile(),
                pages_per_block=5,
                create_searchable=False,
                ocr_language="ita",
                app_version="0.1.2",
            )
            with patch("gdlex_ocr.manifest.write_manifest",
                       side_effect=OSError("permission denied")):
                result = safe_write_manifest(m, out)
        self.assertFalse(result)


class ManifestModulePresenceTest(unittest.TestCase):
    def test_manifest_module_is_importable(self) -> None:
        import gdlex_ocr.manifest as mod

        self.assertTrue(hasattr(mod, "file_sha256"))
        self.assertTrue(hasattr(mod, "utc_now_iso"))
        self.assertTrue(hasattr(mod, "build_initial_manifest"))
        self.assertTrue(hasattr(mod, "write_manifest"))
        self.assertTrue(hasattr(mod, "safe_write_manifest"))
        self.assertTrue(hasattr(mod, "load_manifest"))
        self.assertTrue(hasattr(mod, "verify_manifest_outputs"))
        self.assertTrue(hasattr(mod, "format_manifest_verification"))
        self.assertTrue(hasattr(mod, "MANIFEST_FILENAME"))
        self.assertEqual("manifest.json", mod.MANIFEST_FILENAME)


class ManifestVerificationTest(unittest.TestCase):
    def _manifest(
        self,
        root: Path,
        *,
        status: str = "success",
        searchable_requested: bool = False,
    ) -> dict:
        return {
            "schema_version": 1,
            "job": {"status": status},
            "processing": {
                "ocr_searchable_pdf_requested": searchable_requested,
            },
            "outputs": {
                "markdown": str(root / "sample_ocr.md"),
                "index_markdown": None,
                "searchable_pdf": None,
                "run_log": str(root / "run.log"),
                "manifest": str(root / "manifest.json"),
            },
        }

    def test_load_manifest(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text('{"schema_version": 1}', encoding="utf-8")
            loaded = load_manifest(path)

        self.assertEqual(1, loaded["schema_version"])

    def test_load_legacy_manifest_without_bookmarks(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text(
                '{"schema_version": 1, "outputs": {}}',
                encoding="utf-8",
            )
            loaded = load_manifest(path)

        self.assertNotIn("bookmarks", loaded)

    def test_load_manifest_rejects_invalid_json(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text("{invalid", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_manifest(path)

    def test_verifies_outputs_in_structured_job_directory(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            job_dir = Path(td) / "sample_ocr_job"
            job_dir.mkdir()
            manifest = self._manifest(job_dir)
            manifest["output_layout"] = {
                "structured": True,
                "job_output_dir": str(job_dir),
            }
            for name in ("sample_ocr.md", "run.log", "manifest.json"):
                (job_dir / name).touch()

            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertEqual([], report["missing"])

    def test_success_with_required_files_present(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root)
            for name in ("sample_ocr.md", "run.log", "manifest.json"):
                (root / name).touch()
            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertEqual([], report["missing"])
        self.assertEqual(3, sum(item["required"] for item in report["checked"]))

    def test_success_with_missing_markdown_fails(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root)
            (root / "run.log").touch()
            (root / "manifest.json").touch()
            report = verify_manifest_outputs(manifest)

        self.assertFalse(report["ok"])
        self.assertEqual(["markdown"], report["missing"])

    def test_failed_job_does_not_require_markdown(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root, status="failed")
            (root / "run.log").touch()
            (root / "manifest.json").touch()
            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertNotIn("markdown", report["missing"])

    def test_missing_requested_searchable_pdf_is_warning(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root, searchable_requested=True)
            for name in ("sample_ocr.md", "run.log", "manifest.json"):
                (root / name).touch()
            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertIn(
            "PDF ricercabile richiesto ma non presente",
            report["warnings"],
        )

    def test_searchable_pdf_present_is_reported(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root, searchable_requested=True)
            searchable = root / "sample_searchable.pdf"
            index = root / "sample_ocr_index.md"
            manifest["outputs"]["searchable_pdf"] = str(searchable)
            manifest["outputs"]["index_markdown"] = str(index)
            for path in (
                root / "sample_ocr.md",
                root / "run.log",
                root / "manifest.json",
                searchable,
                index,
            ):
                path.touch()
            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertEqual([], report["warnings"])
        searchable_item = next(
            item
            for item in report["checked"]
            if item["key"] == "searchable_pdf"
        )
        self.assertTrue(searchable_item["exists"])

    def test_verification_does_not_open_declared_outputs(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest(root)
            for name in ("sample_ocr.md", "run.log", "manifest.json"):
                (root / name).write_text("contenuto riservato", encoding="utf-8")
            with patch.object(
                Path,
                "open",
                side_effect=AssertionError("output content was read"),
            ):
                report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])

    def test_format_verification_summary(self) -> None:
        from gdlex_ocr.manifest import format_manifest_verification

        report = {
            "ok": False,
            "checked": [
                {"required": True, "exists": True},
                {"required": True, "exists": False},
            ],
            "missing": ["markdown"],
            "warnings": ["PDF ricercabile richiesto ma non presente"],
        }

        summary = format_manifest_verification(report)

        self.assertIn("Output verificati: 1/2", summary)
        self.assertIn("Manca: markdown", summary)
        self.assertIn("Warning: PDF ricercabile", summary)


class LoadManifestEdgeCaseTest(unittest.TestCase):
    def test_rejects_json_array_root(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_rejects_json_string_root(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text('"ciao"', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_rejects_json_null_root(self) -> None:
        from gdlex_ocr.manifest import load_manifest

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text("null", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)


class VerifyManifestEdgeCaseTest(unittest.TestCase):
    def test_empty_manifest_does_not_crash(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        report = verify_manifest_outputs({})

        self.assertTrue(report["ok"])
        self.assertEqual([], report["missing"])
        self.assertEqual([], report["warnings"])

    def test_manifest_without_job_key_does_not_crash(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        report = verify_manifest_outputs({"outputs": {}, "processing": {}})

        self.assertTrue(report["ok"])
        self.assertNotIn("markdown", report["missing"])

    def test_directory_path_not_counted_as_existing_file(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dir_path = root / "is_a_dir"
            dir_path.mkdir()
            manifest = {
                "job": {"status": "success"},
                "processing": {"ocr_searchable_pdf_requested": False},
                "outputs": {
                    "markdown": str(dir_path),
                    "run_log": str(root / "run.log"),
                    "manifest": str(root / "manifest.json"),
                },
            }
            (root / "run.log").touch()
            (root / "manifest.json").touch()
            report = verify_manifest_outputs(manifest)

        self.assertFalse(report["ok"])
        self.assertIn("markdown", report["missing"])
        markdown_item = next(
            item for item in report["checked"] if item["key"] == "markdown"
        )
        self.assertFalse(markdown_item["exists"])

    def test_unknown_status_does_not_require_markdown(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "run.log").touch()
            (root / "manifest.json").touch()
            manifest = {
                "job": {"status": "cancelled"},
                "processing": {"ocr_searchable_pdf_requested": False},
                "outputs": {
                    "markdown": None,
                    "run_log": str(root / "run.log"),
                    "manifest": str(root / "manifest.json"),
                },
            }
            report = verify_manifest_outputs(manifest)

        self.assertTrue(report["ok"])
        self.assertNotIn("markdown", report["missing"])

    def test_success_without_declared_run_log_reports_missing(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sample_ocr.md").touch()
            (root / "manifest.json").touch()
            manifest = {
                "job": {"status": "success"},
                "processing": {"ocr_searchable_pdf_requested": False},
                "outputs": {
                    "markdown": str(root / "sample_ocr.md"),
                    "run_log": None,
                    "manifest": str(root / "manifest.json"),
                },
            }
            report = verify_manifest_outputs(manifest)

        self.assertFalse(report["ok"])
        self.assertIn("run_log", report["missing"])

    def test_non_string_path_treated_as_not_declared(self) -> None:
        from gdlex_ocr.manifest import verify_manifest_outputs

        manifest = {
            "job": {"status": "failed"},
            "processing": {"ocr_searchable_pdf_requested": False},
            "outputs": {
                "markdown": 42,
                "run_log": ["lista"],
                "manifest": None,
            },
        }
        report = verify_manifest_outputs(manifest)

        for item in report["checked"]:
            if item["key"] in {"markdown", "run_log", "manifest"}:
                self.assertFalse(item["exists"])


class FormatManifestVerificationEdgeCaseTest(unittest.TestCase):
    def test_multiple_warnings_all_appear_in_summary(self) -> None:
        from gdlex_ocr.manifest import format_manifest_verification

        report = {
            "ok": False,
            "checked": [
                {"required": True, "exists": True},
                {"required": True, "exists": False},
                {"required": True, "exists": False},
            ],
            "missing": ["markdown", "run_log"],
            "warnings": [
                "PDF ricercabile richiesto ma non presente",
                "Indice Markdown del PDF ricercabile non presente",
            ],
        }

        summary = format_manifest_verification(report)

        self.assertIn("Output verificati: 1/3", summary)
        self.assertIn("PDF ricercabile richiesto", summary)
        self.assertIn("Indice Markdown", summary)

    def test_empty_report_does_not_crash(self) -> None:
        from gdlex_ocr.manifest import format_manifest_verification

        summary = format_manifest_verification({})

        self.assertIn("Output verificati: 0/0", summary)


class ManifestOutputLayoutConsistencyTest(unittest.TestCase):
    def test_manifest_filename_constant_consistent_with_output_layout(self) -> None:
        from gdlex_ocr.manifest import MANIFEST_FILENAME as mf_name
        from gdlex_ocr.output_layout import MANIFEST_FILENAME as ol_name

        self.assertEqual(mf_name, ol_name)

    def test_log_filename_constant_consistent_with_output_layout(self) -> None:
        from gdlex_ocr.output_layout import LOG_FILENAME, build_output_layout

        layout = build_output_layout(Path("/tmp/doc.pdf"), Path("/tmp/out"))
        self.assertEqual(Path("/tmp/out") / LOG_FILENAME, layout["run_log"])


if __name__ == "__main__":
    unittest.main()
