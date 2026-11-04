import contextlib
import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ateval.cli import main
from ateval.config import load_config
from ateval.registry import DETECTORS, detector_by_name
from ateval.schema import DatasetRecord


class FoundationTests(unittest.TestCase):
    def test_default_config_is_local_first(self):
        self.assertTrue(load_config().offline)

    def test_config_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[app]\nseed=9\noffline=true\noutput_dir="out"\n')
            cfg = load_config(path)
            self.assertEqual(cfg.seed, 9)
            self.assertEqual(cfg.output_dir, "out")

    def test_dataset_record_valid_and_metadata_preserved(self):
        row = DatasetRecord.from_mapping({"sample_id":"s1", "text":"Body", "label":"human", "source_id":"src", "dataset":"demo", "domain":"cs", "metadata":{"split":"test"}})
        self.assertEqual(row.domain, "cs")
        self.assertEqual(row.metadata["split"], "test")

    def test_dataset_record_rejects_missing_and_invalid_labels(self):
        with self.assertRaisesRegex(ValueError, "missing required"):
            DatasetRecord.from_mapping({"sample_id":"s"})
        with self.assertRaisesRegex(ValueError, "label must"):
            DatasetRecord.from_mapping({"sample_id":"s", "text":"x", "label":"maybe", "source_id":"src", "dataset":"d"})

    def test_registry_does_not_claim_unimplemented_methods(self):
        self.assertEqual(len(DETECTORS), 10)
        self.assertEqual(detector_by_name("detectgpt").status, "planned")
        with self.assertRaises(KeyError):
            detector_by_name("made-up")

    def test_cli_detector_list_and_doctor(self):
        self.assertEqual(main(["detector", "list"]), 0)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["doctor"]), 0)
        report = json.loads(output.getvalue().split("\nINFO ")[0])
        self.assertIn("packages", report)
        self.assertIn("backend", report)
        self.assertIn("frontend", report)
        self.assertIn("ollama", report)
        self.assertIn("latex", report)
        self.assertIn("storage", report)

    def test_bug02_dependency_lockfile_and_dockerfile_consistency(self):
        import tomllib

        root = Path(__file__).resolve().parent.parent
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        uv_lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

        ateval_pkg = next(pkg for pkg in uv_lock["package"] if pkg["name"] == "ateval")
        self.assertEqual(ateval_pkg["version"], pyproject["project"]["version"])
        self.assertEqual(
            sorted(ateval_pkg["metadata"]["provides-extras"]),
            sorted(pyproject["project"]["optional-dependencies"].keys()),
        )
        self.assertIn("uv.lock", dockerfile)
        self.assertIn("uv export --locked", dockerfile)
        self.assertIn("--require-hashes", dockerfile)
        self.assertIn("ateval/static", dockerfile)
        self.assertTrue((root / "ateval" / "static" / "index.html").is_file())

    def test_bug05_dynamic_port_validation_host_binding_and_container_healthcheck(self):
        import argparse
        import os
        from unittest.mock import patch
        from ateval.cli import validate_port

        # 1. Valid default and custom ports
        self.assertEqual(validate_port("8000"), 8000)
        self.assertEqual(validate_port(9123), 9123)
        self.assertEqual(validate_port("1"), 1)
        self.assertEqual(validate_port("65535"), 65535)

        # 2. Invalid ports rejected
        for invalid in ("0", "-5", "65536", "70000", "abc", "", True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(argparse.ArgumentTypeError):
                    validate_port(invalid)

        # 3. CLI api subcommand respects PORT env var, --port override, and rejects invalid PORT or --port
        with patch("uvicorn.run") as mock_run:
            with patch.dict(os.environ, {"PORT": "9090"}):
                self.assertEqual(main(["api"]), 0)
                mock_run.assert_called_with("ateval.api:app", host="127.0.0.1", port=9090, log_level="info")

            with patch.dict(os.environ, {"PORT": "9090"}):
                self.assertEqual(main(["api", "--host", "0.0.0.0", "--port", "8123"]), 0)
                mock_run.assert_called_with("ateval.api:app", host="0.0.0.0", port=8123, log_level="info")

            # Invalid PORT env var fails cleanly with SystemExit(2) when running `api`, but does not break `version`
            with patch.dict(os.environ, {"PORT": "not-a-port"}):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["version"]), 0)
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        main(["api"])
                    self.assertEqual(ctx.exception.code, 2)

            # Invalid --port CLI argument fails with SystemExit(2)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx2:
                    main(["api", "--port", "70000"])
                self.assertEqual(ctx2.exception.code, 2)

        # 4. Dockerfile and compose.yaml healthchecks inspect dynamic PORT rather than hardcoded 8000
        root = Path(__file__).resolve().parent.parent
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        compose = (root / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("os.environ.get('PORT', '8000')", dockerfile)
        self.assertIn("os.environ.get('PORT', '8000')", compose)


if __name__ == "__main__":
    unittest.main()
