import importlib.util
import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ateval import api as local_api


class LocalApiTests(unittest.TestCase):
    def test_ollama_health_configuration_is_loopback_only(self):
        from ateval.api import _loopback_ollama_url

        self.assertEqual(_loopback_ollama_url("http://127.0.0.1:11434/"), "http://127.0.0.1:11434")
        for value in ("https://127.0.0.1:11434", "http://remote.example:11434", "http://127.0.0.1:11434/api"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "loopback"):
                    _loopback_ollama_url(value)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        local_api.APP_HOME = root / "state"
        local_api.RAW_DATA_DIR = local_api.APP_HOME / "datasets" / "raw"
        local_api.DB_PATH = local_api.APP_HOME / "test.sqlite3"
        self.client_context = TestClient(local_api.app, base_url="http://127.0.0.1:8000")
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.temp.cleanup()

    def import_csv(self):
        content = (
            "sample_id,text,label,source_id,dataset,generator,domain\n"
            "h1,Human-authored sample,human,src-1,fixture,,computer-science\n"
            "m1,Generated sample,machine,src-2,fixture,model-a,computer-science\n"
        )
        return self.client.post("/api/v1/datasets/import", files={"file": ("fixture.csv", content, "text/csv")})

    def test_local_health_and_system(self):
        self.assertEqual(self.client.get("/api/v1/health").json()["status"], "ok")
        self.assertTrue(self.client.get("/api/v1/system").json()["local_only"])
        self.assertEqual(self.client.get("/api/v1/system").json()["max_upload_bytes"], 25 * 1024 * 1024)

    def test_public_demo_only_processes_fixed_synthetic_sample(self):
        from unittest.mock import patch
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "PUBLIC_DEMO_REQUESTS_PER_MINUTE", 20):
            local_api._public_rate_counts.clear()
            system = self.client.get("/api/v1/system").json()
            self.assertFalse(system["local_only"])
            self.assertTrue(system["public_demo"])
            self.assertFalse(system["uploads_enabled"])
            self.assertEqual(system["storage_root"], "ephemeral public demo")
            rejected = self.client.post("/api/v1/manuscripts/analyze", files={
                "file": ("paper.tex", "private content", "text/x-tex"),
            }, headers={"Origin": "http://127.0.0.1:5174"})
            self.assertEqual(rejected.status_code, 403)
            self.assertEqual(rejected.headers.get("access-control-allow-origin"), "http://127.0.0.1:5174")
            self.assertNotIn("private content", rejected.text)
            sample = self.client.post("/api/v1/demo/sample")
            self.assertEqual(sample.status_code, 200, sample.text)
            self.assertIn("This synthetic sample", sample.json()["prose_projection"])
            self.assertEqual(self.client.get("/api/v1/datasets").json(), [])

    def test_public_demo_rate_limit_is_applied(self):
        from unittest.mock import patch
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "PUBLIC_DEMO_REQUESTS_PER_MINUTE", 1):
            local_api._public_rate_counts.clear()
            self.assertEqual(self.client.get("/api/v1/health").status_code, 200)
            limited = self.client.get("/api/v1/health")
            self.assertEqual(limited.status_code, 429)

    def test_render_demo_rate_limit_uses_forwarded_client_address(self):
        from unittest.mock import patch
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "PUBLIC_DEMO_REQUESTS_PER_MINUTE", 1), patch.dict("os.environ", {"RENDER": "true"}):
            local_api._public_rate_counts.clear()
            first_ip = {"X-Forwarded-For": "192.0.2.10, 10.0.0.1"}
            second_ip = {"X-Forwarded-For": "192.0.2.11, 10.0.0.1"}
            self.assertEqual(self.client.get("/api/v1/health", headers=first_ip).status_code, 200)
            self.assertEqual(self.client.get("/api/v1/health", headers=first_ip).status_code, 429)
            self.assertEqual(self.client.get("/api/v1/health", headers=second_ip).status_code, 200)

    def test_streaming_api_body_limit_rejects_oversized_requests(self):
        messages = [
            {"type": "http.request", "body": b"x" * (1024 * 1024), "more_body": True},
            {"type": "http.request", "body": b"xx", "more_body": False},
        ]
        sent = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            sent.append(message)

        async def consume(scope, limited_receive, send_response):
            await limited_receive()
            await limited_receive()

        middleware = local_api.MaxRequestBodyMiddleware(consume, max_bytes=1)
        asyncio.run(middleware({"type": "http", "path": "/api/v1/test", "headers": []}, receive, send))
        self.assertEqual(sent[0]["status"], 413)

    def test_import_preserves_provenance_and_hides_raw_text_from_list(self):
        response = self.import_csv()
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["row_count"], 2)
        self.assertEqual(body["validation"]["label_distribution"], {"human": 1, "machine": 1})
        self.assertEqual(body["validation"]["domain_distribution"], {"computer-science": 2})
        listed = self.client.get("/api/v1/datasets").json()
        self.assertEqual(listed[0]["id"], body["id"])
        self.assertNotIn("Human-authored sample", str(listed))

    def test_rejects_unsupported_file_type(self):
        response = self.client.post("/api/v1/datasets/import", files={"file": ("notes.txt", "private prose", "text/plain")})
        self.assertEqual(response.status_code, 415)

    def test_draft_can_be_saved_but_execution_is_truthfully_unavailable(self):
        imported = self.import_csv().json()
        draft = self.client.post("/api/v1/experiments", json={"name": "Fixture evaluation", "dataset_id": imported["id"], "configuration": {"task": "binary-detection"}})
        self.assertEqual(draft.status_code, 200, draft.text)
        self.assertEqual(draft.json()["status"], "draft")
        run = self.client.post(f"/api/v1/experiments/{draft.json()['id']}/run")
        self.assertEqual(run.status_code, 409)
        self.assertIn("No detector", run.json()["detail"])

    def test_rejects_untrusted_browser_origins(self):
        response = self.client.get("/api/v1/health", headers={"Origin": "https://example.invalid"})
        self.assertEqual(response.status_code, 403)

    def test_cors_allows_actual_vite_origin_and_preflight(self):
        origin = "http://127.0.0.1:5174"
        preflight = self.client.options("/api/v1/manuscripts/analyze", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(preflight.status_code, 200, preflight.text)
        self.assertEqual(preflight.headers.get("access-control-allow-origin"), origin)
        self.assertIn("POST", preflight.headers.get("access-control-allow-methods", ""))
        self.assertIn("content-type", preflight.headers.get("access-control-allow-headers", "").lower())
        self.assertNotIn("PUT", preflight.headers.get("access-control-allow-methods", ""))
        self.assertNotIn("PATCH", preflight.headers.get("access-control-allow-methods", ""))
        self.assertNotIn("true", preflight.headers.get("access-control-allow-credentials", "").lower())
        auth_preflight = self.client.options("/api/v1/manuscripts/analyze", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        })
        self.assertEqual(auth_preflight.status_code, 400)

    def test_invalid_origin_is_rejected_without_allowing_null_origin(self):
        for origin in ("https://example.invalid", "null", "http://127.0.0.1:5999"):
            with self.subTest(origin=origin):
                response = self.client.get("/api/v1/health", headers={"Origin": origin})
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("access-control-allow-origin", response.headers)

    def test_tex_multipart_upload_from_vite_origin_is_analyzed(self):
        origin = "http://127.0.0.1:5174"
        source = b"\\section{Introduction}\nThe method estimates the target quantity."
        response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
            "file": ("..\\draft.tex", source, "application/x-tex"),
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertEqual(response.json()["document"]["format"], "tex")
        self.assertEqual(response.json()["document"]["name"], "draft.tex")
        self.assertIn("estimates the target", response.json()["prose_projection"])

    def test_malformed_docx_and_pdf_return_readable_errors(self):
        origin = "http://127.0.0.1:5174"
        cases = (
            ("broken.docx", b"not-a-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("broken.pdf", b"not-a-pdf", "application/pdf"),
        )
        for filename, content, media_type in cases:
            with self.subTest(filename=filename):
                response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
                    "file": (filename, content, media_type),
                })
                self.assertIn(response.status_code, (422, 503), response.text)
                self.assertEqual(response.headers.get("access-control-allow-origin"), origin)

    def test_docx_multipart_upload_is_parsed_or_reports_optional_dependency(self):
        origin = "http://localhost:5174"
        try:
            from docx import Document
        except ImportError:
            content = b"not-a-real-docx"
            expected_status = 503
        else:
            import io
            document = Document()
            document.add_paragraph("A local DOCX passage for upload testing.")
            buffer = io.BytesIO()
            document.save(buffer)
            content = buffer.getvalue()
            expected_status = 200
        response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
            "file": ("draft.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        })
        self.assertEqual(response.status_code, expected_status, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        if expected_status == 200:
            self.assertIn("local DOCX passage", response.json()["prose_projection"])

    def test_pdf_multipart_upload_is_parsed_or_reports_optional_dependency(self):
        origin = "http://127.0.0.1:5174"
        try:
            import pymupdf
        except ImportError:
            content = b"not-a-real-pdf"
            expected_status = 503
        else:
            import io
            document = pymupdf.open()
            page = document.new_page()
            page.insert_text((72, 72), "This text-layer PDF contains enough reliable prose for local upload validation. " * 2)
            content = document.tobytes()
            document.close()
            expected_status = 200
        response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
            "file": ("draft.pdf", content, "application/pdf"),
        })
        self.assertEqual(response.status_code, expected_status, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        if expected_status == 200:
            self.assertEqual(response.json()["document"]["format"], "pdf")

    def test_malformed_multipart_has_cors_headers(self):
        origin = "http://127.0.0.1:5174"
        response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, data="not multipart")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)

    def test_oversized_manuscript_is_rejected_with_cors_headers(self):
        origin = "http://127.0.0.1:5174"
        response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
            "file": ("too-large.txt", b"x" * (25 * 1024 * 1024 + 1), "text/plain"),
        })
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)

    def test_backend_upload_exception_has_cors_headers(self):
        from unittest.mock import patch
        origin = "http://127.0.0.1:5174"
        with patch.object(local_api, "import_manuscript", side_effect=RuntimeError("fixture parser failure")):
            response = self.client.post("/api/v1/manuscripts/analyze", headers={"Origin": origin}, files={
                "file": ("draft.txt", "Academic prose.", "text/plain"),
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)

    def test_packaged_frontend_and_api_share_the_local_fastapi_origin(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as build_dir:
            Path(build_dir, "index.html").write_text("<!doctype html><title>ATEval packaged test</title>", encoding="utf-8")
            Path(build_dir, "assets").mkdir()
            Path(build_dir, "assets", "app.js").write_text("window.ateval = true", encoding="utf-8")
            with patch.object(local_api, "CLIENT_BUILD_DIR", Path(build_dir)):
                page = self.client.get("/")
                asset = self.client.get("/assets/app.js")
                health = self.client.get("/api/v1/health")
        self.assertEqual(page.status_code, 200)
        self.assertIn("ATEval packaged test", page.text)
        self.assertEqual(asset.text, "window.ateval = true")
        self.assertEqual(health.json()["status"], "ok")

    def test_writing_analysis_is_available_and_keeps_text_out_of_audit(self):
        self.assertEqual(self.client.get("/api/v1/writing/status").json()["baseline"], "available")
        source = "We show that the method works in order to explain the result."
        analysis_response = self.client.post("/api/v1/writing/analyze", json={"text": source, "document_name": "paper.tex", "document_format": "tex"})
        self.assertEqual(analysis_response.status_code, 200, analysis_response.text)
        analysis = analysis_response.json()
        self.assertTrue(analysis["suggestions"])
        suggestion = analysis["suggestions"][0]
        audit_response = self.client.post("/api/v1/writing/audits", json={"text": source, "document_name": "paper.tex", "document_format": "tex", "accepted_suggestion_ids": [suggestion["id"]]})
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        audit = audit_response.json()["audit"]
        self.assertFalse(audit["source_text_stored"])
        self.assertEqual(audit["accepted_change_count"], 1)
        self.assertNotIn(source, str(audit))
        with local_api.get_db() as db:
            saved = db.execute("SELECT payload_json FROM reports WHERE kind = 'writing_audit'").fetchone()["payload_json"]
        self.assertNotIn(source, saved)

    def test_writing_upload_extracts_utf8_source_locally(self):
        response = self.client.post("/api/v1/writing/ingest", files={"file": ("draft.tex", "\\section{Intro}\nText", "text/plain")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["source_modified"])
        self.assertEqual(response.json()["format"], "tex")

    def test_scar_api_returns_no_edit_without_local_model(self):
        response = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": "The estimate is reported in Table 2. This paragraph summarizes the result.",
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["gate"]["decision"], "NO_EDIT_REQUIRED")
        self.assertEqual(body["review_decision"], "NO_CHANGE")
        self.assertIsNone(body["inference"])
        self.assertTrue(body["structural_validation"]["skipped"])

    def test_scar_api_abstains_on_missing_context_without_model(self):
        response = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported.",
            "intention": "clarity",
            "author_requested_edit": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["gate"]["decision"], "INSUFFICIENT_CONTEXT")
        self.assertEqual(body["review_decision"], "REQUIRES_EXPERT_REVIEW")
        self.assertIsNone(body["inference"])

    def test_manuscript_analysis_reports_experimental_detector_truthfully(self):
        response = self.client.post("/api/v1/manuscripts/analyze", files={
            "file": ("paper.txt", "A short academic passage.", "text/plain"),
        })
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertEqual(report["detector_summary"]["available_method_count"], 1)
        self.assertIsNone(report["detector_summary"]["overall_authorship_probability"])
        self.assertEqual(report["coverage"]["ai_signal_passages_analyzed"], 1)
        self.assertEqual(report["passages"][0]["analysis_status"], "analyzed")
        self.assertIn("false positives", report["detector_summary"]["warning"])

    def test_manuscript_analysis_rejects_unsupported_file_type(self):
        response = self.client.post("/api/v1/manuscripts/analyze", files={
            "file": ("paper.md", "text", "text/markdown"),
        })
        self.assertEqual(response.status_code, 422)

    def test_manuscript_export_applies_only_accepted_mapped_edit(self):
        source = "This is a source sentence."
        response = self.client.post("/api/v1/manuscripts/export", files={
            "file": ("paper.txt", source, "text/plain"),
        }, data={"accepted_edits": '[{"source_text":"This","replacement":"That","source_map":{"editable":true,"path":"paper.txt","start":0,"end":4}}]'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content.decode(), "That is a source sentence.")
        self.assertIn("paper-reviewed.txt", response.headers.get("content-disposition", ""))
        self.assertEqual(source, "This is a source sentence.")

    def test_manuscript_revision_fails_truthfully_when_local_model_unavailable(self):
        from unittest.mock import patch
        with patch.object(local_api, "_ollama_revision_status", return_value={"available": False, "reason": "Model is not installed."}):
            response = self.client.post("/api/v1/writing/revise", json={
                "sentence": "The method needs clarity.",
                "paragraph_context": "The method needs clarity. This context gives the research setting.",
                "intention": "clarity",
                "author_requested_edit": True,
            })
        self.assertEqual(response.status_code, 503)
        self.assertIn("not installed", response.json()["detail"])

    def test_manuscript_revision_reports_local_model_timeout(self):
        from unittest.mock import patch

        class TimedOutGenerator:
            def __init__(self, *args, **kwargs):
                pass

            def generate(self, request):
                raise TimeoutError("local inference exceeded the configured timeout")

        with patch.object(local_api, "_ollama_revision_status", return_value={"available": True, "reason": None}), patch.object(local_api, "XtraGPTOllamaGenerator", TimedOutGenerator):
            response = self.client.post("/api/v1/writing/revise", json={
                "sentence": "The method needs clarity.",
                "paragraph_context": "The method needs clarity. This context gives the research setting.",
                "intention": "clarity",
                "author_requested_edit": True,
            })
        self.assertEqual(response.status_code, 503)
        self.assertIn("timeout", response.json()["detail"])

    def test_manuscript_revision_uses_safety_aware_prompt_mode(self):
        from unittest.mock import patch

        class AvailableGenerator:
            def __init__(self, *args, **kwargs):
                self.mode = kwargs["mode"]

            def generate(self, request):
                raise RuntimeError(f"prompt mode={self.mode}")

        with patch.object(local_api, "_ollama_revision_status", return_value={"available": True, "reason": None}), patch.object(local_api, "XtraGPTOllamaGenerator", AvailableGenerator):
            response = self.client.post("/api/v1/writing/revise", json={
                "sentence": "The method needs clarity.",
                "paragraph_context": "The method needs clarity. This context gives the research setting.",
                "intention": "clarity",
                "author_requested_edit": True,
            })
        self.assertEqual(response.status_code, 503)
        self.assertIn("prompt mode=ateval", response.json()["detail"])

    @unittest.skipUnless(importlib.util.find_spec("joblib"), "optional revision-ml dependencies are not installed")
    def test_learned_revision_intent_is_advisory_and_not_persisted(self):
        if not local_api.REVISION_MODEL_PATH.is_file():
            self.skipTest("trained Milestone 3 model artifacts are not installed")
        response = self.client.post("/api/v1/writing/revision-intent", json={
            "sentence": "The results are not clear.",
            "context_after": "This sentence describes the method outcome.",
            "section_type": "abstract",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["decision"], "advisory_only")
        self.assertTrue(body["author_review_required"])
        self.assertFalse(body["automatic_edit_applied"])
        self.assertIsNone(body["modification_necessary"])
        self.assertIn("uncalibrated", body["score_kind"])
        self.assertNotIn("The results are not clear.", str(body))
        with local_api.get_db() as db:
            saved = db.execute("SELECT COUNT(*) AS count FROM reports WHERE kind = 'revision_intent'").fetchone()["count"]
        self.assertEqual(saved, 0)


if __name__ == "__main__":
    unittest.main()
