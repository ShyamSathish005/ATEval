import importlib.util
import asyncio
import json
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
            first_ip = {"X-Forwarded-For": "203.0.113.99, 192.0.2.10"}
            second_ip = {"X-Forwarded-For": "203.0.113.99, 192.0.2.11"}
            self.assertEqual(self.client.get("/api/v1/health", headers=first_ip).status_code, 200)
            self.assertEqual(self.client.get("/api/v1/health", headers=first_ip).status_code, 429)
            self.assertEqual(self.client.get("/api/v1/health", headers=second_ip).status_code, 200)

    def test_sec01_forwarded_ip_trust_and_rate_limit_bounds(self):
        from unittest.mock import patch
        from types import SimpleNamespace

        # 1. Forged X-Forwarded-For is ignored when TRUSTED_PROXY_HOPS is 0 (default)
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "PUBLIC_DEMO_REQUESTS_PER_MINUTE", 1), patch.object(local_api, "TRUSTED_PROXY_HOPS", 0), patch.dict("os.environ", {"RENDER": "false"}, clear=False):
            local_api._public_rate_counts.clear()
            self.assertEqual(self.client.get("/api/v1/health", headers={"X-Forwarded-For": "198.51.100.1"}).status_code, 200)
            # Spoofing a different XFF does not bypass the rate limit when hops=0
            self.assertEqual(self.client.get("/api/v1/health", headers={"X-Forwarded-For": "198.51.100.2"}).status_code, 429)

        # 2. Untrusted immediate peer connection ignores X-Forwarded-For even when hops=1
        untrusted_req = SimpleNamespace(
            client=SimpleNamespace(host="198.51.100.200"),
            headers={"x-forwarded-for": "203.0.113.5"},
        )
        with patch.object(local_api, "TRUSTED_PROXY_HOPS", 1):
            self.assertEqual(local_api._resolve_client_ip(untrusted_req), "198.51.100.200")

        # 3. Multiple forwarded IP values select the N-th hop from the right
        trusted_req = SimpleNamespace(
            client=SimpleNamespace(host="10.0.0.5"),
            headers={"x-forwarded-for": "203.0.113.1, 198.51.100.77, 172.16.0.9"},
        )
        with patch.object(local_api, "TRUSTED_PROXY_HOPS", 2):
            self.assertEqual(local_api._resolve_client_ip(trusted_req), "198.51.100.77")

        # 4. Malformed IP in X-Forwarded-For is rejected with HTTP 400
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "TRUSTED_PROXY_HOPS", 1):
            local_api._public_rate_counts.clear()
            bad = self.client.get("/api/v1/health", headers={"X-Forwarded-For": "not-an-ip, 192.0.2.1"})
            self.assertEqual(bad.status_code, 400)
            self.assertIn("Malformed", bad.json()["detail"])

        # 5. Large numbers of unique spoofed addresses cannot grow _public_rate_counts past PUBLIC_RATE_LIMIT_MAX_BUCKETS
        with patch.object(local_api, "PUBLIC_DEMO_MODE", True), patch.object(local_api, "PUBLIC_DEMO_REQUESTS_PER_MINUTE", 5), patch.object(local_api, "PUBLIC_RATE_LIMIT_MAX_BUCKETS", 32), patch.object(local_api, "TRUSTED_PROXY_HOPS", 1):
            local_api._public_rate_counts.clear()
            for idx in range(100):
                ip = f"192.0.2.{idx + 1}"
                res = self.client.get("/api/v1/health", headers={"X-Forwarded-For": ip})
                self.assertEqual(res.status_code, 200)
            self.assertLessEqual(len(local_api._public_rate_counts), 32)

    def test_sec05_origin_host_csrf_and_launch_token_protections(self):
        from unittest.mock import patch

        # 1. Unexpected Host and terminal.local are rejected
        for bad_host in ("evil.example.com", "terminal.local", "127.0.0.1:99999", "localhost/evil"):
            with self.subTest(host=bad_host):
                res = self.client.get("/api/v1/health", headers={"Host": bad_host})
                self.assertEqual(res.status_code, 400)

        # 2. Cross-site mutation via Sec-Fetch-Site or cross-origin Referer is blocked even without Origin
        res_fetch = self.client.post("/api/v1/experiments", json={"name": "Draft"}, headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(res_fetch.status_code, 403)
        res_ref = self.client.post("/api/v1/experiments", json={"name": "Draft"}, headers={"Referer": "https://attacker.example/page.html"})
        self.assertEqual(res_ref.status_code, 403)
        res_form = self.client.post("/api/v1/experiments", content=b"name=Draft", headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(res_form.status_code, 415)

        # 3. Missing Origin is rejected when REQUIRE_ORIGIN_FOR_MUTATIONS=True unless valid token is provided
        with patch.object(local_api, "REQUIRE_ORIGIN_FOR_MUTATIONS", True):
            missing_origin = self.client.post("/api/v1/experiments", json={"name": "Draft"})
            self.assertEqual(missing_origin.status_code, 403)
            with_token = self.client.post("/api/v1/experiments", json={"name": "Draft"}, headers={"X-ATEval-Token": local_api.LAUNCH_TOKEN})
            self.assertEqual(with_token.status_code, 200)

        # 4. Valid same-origin and Tauri desktop application requests succeed
        same_origin = self.client.post("/api/v1/experiments", json={"name": "SameOrigin"}, headers={"Origin": "http://127.0.0.1:8000"})
        self.assertEqual(same_origin.status_code, 200)
        tauri_origin = self.client.post("/api/v1/experiments", json={"name": "TauriApp"}, headers={"Origin": "tauri://localhost"})
        self.assertEqual(tauri_origin.status_code, 200)

        # 5. Invalid or missing per-launch token is rejected when enforced or supplied
        bad_token = self.client.post("/api/v1/experiments", json={"name": "BadToken"}, headers={"X-ATEval-Token": "wrong-token"})
        self.assertEqual(bad_token.status_code, 403)
        with patch.object(local_api, "REQUIRE_LAUNCH_TOKEN", True):
            no_token = self.client.post("/api/v1/experiments", json={"name": "NoToken"}, headers={"Origin": "http://127.0.0.1:8000"})
            self.assertEqual(no_token.status_code, 403)
            good_token = self.client.post("/api/v1/experiments", json={"name": "GoodToken"}, headers={"Origin": "http://127.0.0.1:8000", "X-ATEval-Token": local_api.LAUNCH_TOKEN})
            self.assertEqual(good_token.status_code, 200)

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
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertIn("sandbox", response.headers.get("content-security-policy", ""))
        self.assertEqual(source, "This is a source sentence.")

    def test_sec03_export_header_injection_unicode_and_html_safety(self):
        from ateval.manuscript_analysis.exports import build_content_disposition, sanitize_export_filename

        # 1. Direct unit check for CRLF, quotes, path traversal, and Unicode in filenames
        raw_malicious = "../evil\"\r\nX-Injected: pwned\r\n\"étude.txt"
        sanitized = sanitize_export_filename(raw_malicious, suffix="-reviewed.txt")
        self.assertNotIn("\r", sanitized)
        self.assertNotIn("\n", sanitized)
        self.assertNotIn('"', sanitized)
        self.assertNotIn("/", sanitized)
        disp = build_content_disposition(sanitized)
        self.assertNotIn("\r", disp)
        self.assertNotIn("\n", disp)
        self.assertIn("filename*=UTF-8''", disp)
        self.assertIn("%C3%A9tude-reviewed.txt", disp)

        # 2. End-to-end API export with quotes, semicolons, path separators, and Unicode
        source = "This is a source sentence with <script>alert(1)</script> text."
        malicious_name = "../evil_étude.txt"
        analyzed = self.client.post(
            "/api/v1/manuscripts/analyze",
            files={"file": (malicious_name, source, "text/plain")},
        )
        self.assertEqual(analyzed.status_code, 200, analyzed.text)
        mapped_path = analyzed.json()["passages"][0]["source_map"]["path"]
        edits = f'[{{"source_text":"This","replacement":"That","source_map":{{"editable":true,"path":"{mapped_path}","start":0,"end":4}}}}]'
        response = self.client.post(
            "/api/v1/manuscripts/export",
            files={"file": (malicious_name, source, "text/plain")},
            data={"accepted_edits": edits},
        )
        self.assertEqual(response.status_code, 200, response.text)
        disposition = response.headers.get("content-disposition", "")
        self.assertNotIn("\r", disposition)
        self.assertNotIn("\n", disposition)
        self.assertNotIn("..", disposition)
        self.assertTrue(disposition.startswith("attachment; filename="))
        self.assertIn("filename*=UTF-8''", disposition)
        self.assertIn("evil_%C3%A9tude-reviewed.txt", disposition)
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertIn("default-src 'none'", response.headers.get("content-security-policy", ""))
        self.assertIn("sandbox", response.headers.get("content-security-policy", ""))

        # 2. HTML export content escapes script tags, uses attachment delivery, and sets CSP + nosniff
        html_res = self.client.post(
            "/api/v1/manuscripts/export",
            files={"file": ('draft"<script>.txt', source, "text/plain")},
            data={"export_format": "html"},
        )
        self.assertEqual(html_res.status_code, 200, html_res.text)
        self.assertTrue(html_res.headers.get("content-type", "").startswith("text/html"))
        self.assertTrue(html_res.headers.get("content-disposition", "").startswith("attachment;"))
        self.assertEqual(html_res.headers.get("x-content-type-options"), "nosniff")
        self.assertIn("sandbox", html_res.headers.get("content-security-policy", ""))
        body_text = html_res.content.decode("utf-8")
        self.assertNotIn("<script>alert(1)</script>", body_text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body_text)
        self.assertIn("http-equiv=\"Content-Security-Policy\"", body_text)

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

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "optional revision-ml dependencies are not installed")
    def test_learned_revision_intent_is_advisory_and_not_persisted(self):
        import hashlib
        from unittest.mock import patch
        from ateval.revisions.classic_models import METADATA_SCHEMA, save_declarative_model
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion, Pipeline

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model_path = root / "local_logistic_regression.model.json"
            metadata_path = root / "local_logistic_regression.metadata.json"

            pipeline = Pipeline([
                ("tfidf", FeatureUnion([
                    ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, strip_accents="unicode")),
                    ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
                ])),
                ("classifier", LogisticRegression(max_iter=200, random_state=17)),
            ])
            texts = [
                "section:abstract before: target:The results are not clear. after:This sentence describes the method outcome.",
                "section:introduction before: target:In order to show the result. after:We summarize the finding.",
            ]
            labels = ["clarity_improvement", "concision"]
            pipeline.fit(texts, labels)
            save_declarative_model(pipeline, model_path, context_level="local", kind="logistic_regression")
            digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
            metadata_path.write_text(json.dumps({
                "schema": METADATA_SCHEMA,
                "model_type": "logistic_regression",
                "context_level": "local",
                "weight_file": model_path.name,
                "sha256": digest,
                "label_order": ["clarity_improvement", "concision"],
            }), encoding="utf-8")

            (root / "comparison.json").write_text(json.dumps({
                "models": {"local": {"logistic_regression": {"macro_f1": 0.58}}}
            }), encoding="utf-8")

            with patch.object(local_api, "ALLOWED_MODEL_ROOT", root), \
                 patch.object(local_api, "REVISION_MODEL_DIR", root), \
                 patch.object(local_api, "REVISION_MODEL_PATH", model_path), \
                 patch.object(local_api, "REVISION_MODEL_METADATA", metadata_path):
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

    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "optional revision-ml dependencies are not installed")
    def test_sec04_declarative_model_integrity_and_deserialization_safety(self):
        import hashlib
        import shutil
        from ateval.revisions.classic_models import (
            DeclarativeLinearModel,
            METADATA_SCHEMA,
            load_declarative_model,
            save_declarative_model,
        )
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion, Pipeline

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside_root = Path(tempfile.mkdtemp())
            try:
                pipeline = Pipeline([
                    ("tfidf", FeatureUnion([
                        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, strip_accents="unicode")),
                        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
                    ])),
                    ("classifier", LogisticRegression(max_iter=200, random_state=17)),
                ])
                texts = [
                    "orig: vague statement || rev: clear statement",
                    "orig: wordy phrase in order to || rev: concise phrase",
                    "orig: grammar error is are || rev: grammar fixed",
                ]
                labels = ["clarity_improvement", "concision", "fluency_grammar"]
                pipeline.fit(texts, labels)

                model_path = root / "test.model.json"
                meta_path = root / "test.metadata.json"
                save_declarative_model(pipeline, model_path, context_level="local", kind="logistic_regression")
                digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
                meta_path.write_text(json.dumps({
                    "schema": METADATA_SCHEMA,
                    "model_type": "logistic_regression",
                    "context_level": "local",
                    "weight_file": model_path.name,
                    "sha256": digest,
                    "label_order": sorted(set(labels)),
                }), encoding="utf-8")

                # 1. Valid model artifact loads and matches sklearn predictions
                loaded = load_declarative_model(
                    model_path,
                    metadata_path=meta_path,
                    allowed_root=root,
                    expected_sha256=digest,
                )
                self.assertIsInstance(loaded, DeclarativeLinearModel)
                self.assertEqual(loaded.predict(texts), list(pipeline.predict(texts)))

                # 2. Modified artifact is rejected (digest mismatch)
                tampered_path = root / "tampered.model.json"
                payload = json.loads(model_path.read_text(encoding="utf-8"))
                payload["classifier"]["intercept"][0] += 999.0
                tampered_path.write_text(json.dumps(payload), encoding="utf-8")
                tampered_meta = root / "tampered.metadata.json"
                tampered_meta.write_text(json.dumps({
                    "schema": METADATA_SCHEMA,
                    "weight_file": tampered_path.name,
                    "sha256": digest,
                    "label_order": sorted(set(labels)),
                }), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "SHA-256 digest does not match"):
                    load_declarative_model(tampered_path, metadata_path=tampered_meta, allowed_root=root)

                # 3. Missing manifest is rejected
                missing_meta = root / "missing.metadata.json"
                with self.assertRaisesRegex(FileNotFoundError, "metadata manifest not found"):
                    load_declarative_model(model_path, metadata_path=missing_meta, allowed_root=root)

                # 4. Invalid pinned digest is rejected even if adjacent metadata file was rewritten
                rewritten_meta = root / "rewritten.metadata.json"
                tampered_digest = hashlib.sha256(tampered_path.read_bytes()).hexdigest()
                rewritten_meta.write_text(json.dumps({
                    "schema": METADATA_SCHEMA,
                    "weight_file": tampered_path.name,
                    "sha256": tampered_digest,
                    "label_order": sorted(set(labels)),
                }), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "build-pinned digest"):
                    load_declarative_model(
                        tampered_path,
                        metadata_path=rewritten_meta,
                        allowed_root=root,
                        expected_sha256=digest,
                    )

                # 5. Unexpected model path outside allowed root or unsafe .joblib suffix is rejected
                outside_model = outside_root / "outside.model.json"
                outside_model.write_text(model_path.read_text(encoding="utf-8"), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "outside the trusted model directory"):
                    load_declarative_model(outside_model, allowed_root=root)

                joblib_path = root / "legacy.joblib"
                joblib_path.write_bytes(b"unsafe-pickle-bytes")
                with self.assertRaisesRegex(ValueError, "Refusing to load executable .joblib/pickle"):
                    load_declarative_model(joblib_path, allowed_root=root)

                # 6. Invalid metadata (missing sha256 or wrong schema) is rejected
                bad_meta = root / "bad.metadata.json"
                bad_meta.write_text(json.dumps({
                    "schema": METADATA_SCHEMA,
                    "weight_file": model_path.name,
                    "sha256": "not-a-hex-digest",
                    "label_order": sorted(set(labels)),
                }), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "SHA-256 digest does not match"):
                    load_declarative_model(model_path, metadata_path=bad_meta, allowed_root=root)
            finally:
                shutil.rmtree(outside_root, ignore_errors=True)

    def test_bug01_experiment_execution_disabled_by_default_and_research_mode_provenance(self):
        from unittest.mock import patch

        imported = self.import_csv().json()
        draft = self.client.post(
            "/api/v1/experiments",
            json={"name": "Research evaluation", "dataset_id": imported["id"], "configuration": {"task": "stylometric-baseline"}},
        ).json()

        # 1. Default mode: disabled with 409
        default_run = self.client.post(f"/api/v1/experiments/{draft['id']}/run")
        self.assertEqual(default_run.status_code, 409)
        self.assertIn("No detector", default_run.json()["detail"])

        # 2. Public demo mode: remains inaccessible even if RESEARCH_EXPERIMENTS_ENABLED is True
        with patch.object(local_api, "RESEARCH_EXPERIMENTS_ENABLED", True), \
             patch.object(local_api, "PUBLIC_DEMO_MODE", True):
            demo_run = self.client.post(
                f"/api/v1/experiments/{draft['id']}/run",
                headers={"X-ATEval-Token": local_api.LAUNCH_TOKEN},
            )
            self.assertEqual(demo_run.status_code, 403)

        # 3. Local research mode requires valid per-launch X-ATEval-Token
        with patch.object(local_api, "RESEARCH_EXPERIMENTS_ENABLED", True), \
             patch.object(local_api, "PUBLIC_DEMO_MODE", False):
            unauth_run = self.client.post(f"/api/v1/experiments/{draft['id']}/run")
            self.assertEqual(unauth_run.status_code, 403)

            # Missing dataset_id is rejected with 422
            no_ds_draft = self.client.post("/api/v1/experiments", json={"name": "No dataset draft"}).json()
            no_ds_run = self.client.post(
                f"/api/v1/experiments/{no_ds_draft['id']}/run",
                headers={"X-ATEval-Token": local_api.LAUNCH_TOKEN},
            )
            self.assertEqual(no_ds_run.status_code, 422)

            # Valid dataset and token executes off the event loop and records research provenance
            ok_run = self.client.post(
                f"/api/v1/experiments/{draft['id']}/run",
                headers={"X-ATEval-Token": local_api.LAUNCH_TOKEN},
            )
            self.assertEqual(ok_run.status_code, 200, ok_run.text)
            payload = ok_run.json()
            self.assertEqual(payload["status"], "completed")
            measurement = payload["research_measurement"]
            self.assertEqual(measurement["measurement_mode"], "research_measurement_only")
            self.assertFalse(measurement["definitive_authorship_score"])
            self.assertEqual(measurement["detector"]["version"], "m5.0.0")
            self.assertEqual(measurement["detector"]["benchmark_evidence"]["auroc"], 0.5541)
            self.assertEqual(measurement["dataset"]["dataset_sha256"], imported["sha256"])
            self.assertEqual(measurement["dataset"]["evaluated_rows"], 2)

            # Re-running a completed experiment is rejected with 409
            rerun = self.client.post(
                f"/api/v1/experiments/{draft['id']}/run",
                headers={"X-ATEval-Token": local_api.LAUNCH_TOKEN},
            )
            self.assertEqual(rerun.status_code, 409)

    def test_bug03_async_threadpool_and_sqlite_wal_concurrency(self):
        import concurrent.futures
        import sqlite3
        from unittest.mock import patch

        # 1. Verify WAL mode, busy_timeout, and foreign_keys
        with local_api.get_db() as db:
            journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0].lower()
            busy_timeout = db.execute("PRAGMA busy_timeout").fetchone()[0]
            fk_enabled = db.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(journal_mode, "wal")
        self.assertGreaterEqual(int(busy_timeout), 15000)
        self.assertEqual(int(fk_enabled), 1)

        # 2. Verify transaction rollback leaves DB clean on mid-transaction exception
        before_count = len(self.client.get("/api/v1/experiments").json())
        with self.assertRaises(RuntimeError):
            with local_api.get_db() as db:
                db.execute(
                    "INSERT INTO experiments VALUES (?, ?, 'draft', NULL, '{}', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                    ("rollback-id-1", "Rollback test"),
                )
                raise RuntimeError("simulated mid-transaction failure")
        after_count = len(self.client.get("/api/v1/experiments").json())
        self.assertEqual(before_count, after_count)

        # 3. Parallel reads, parallel writes, simultaneous manuscript analyses, and dataset ingestions
        def worker(idx: int) -> tuple[int, int, int, int]:
            csv_content = (
                "sample_id,text,label,split,domain,source_id\n"
                f"h-{idx},The empirical estimator converges under mild regularity conditions.,human,test,cs,synthetic-v1\n"
                f"m-{idx},Furthermore the methodology demonstrates notable performance across tasks.,machine,test,cs,synthetic-v1\n"
            )
            ds_res = self.client.post(
                "/api/v1/datasets/import",
                files={"file": (f"concurrent-{idx}.csv", csv_content, "text/csv")},
            )
            exp_res = self.client.post(
                "/api/v1/experiments",
                json={"name": f"Concurrent-{idx}", "dataset_id": ds_res.json().get("id")},
            )
            ms_res = self.client.post(
                "/api/v1/manuscripts/analyze",
                files={"file": (f"paper-{idx}.txt", f"Section {idx}. We report the experimental protocol clearly.", "text/plain")},
            )
            list_res = self.client.get("/api/v1/experiments")
            return ds_res.status_code, exp_res.status_code, ms_res.status_code, list_res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(worker, range(6)))
        for statuses in results:
            self.assertEqual(statuses, (200, 200, 200, 200))

        # 4. Database busy/locked OperationalError translates cleanly to HTTP 503
        with patch.object(local_api, "get_db", side_effect=sqlite3.OperationalError("database is locked")):
            busy_res = self.client.get("/api/v1/datasets")
            self.assertEqual(busy_res.status_code, 503)
            self.assertIn("temporarily busy", busy_res.json()["detail"])

    def test_bug04_repeated_sentence_offset_disambiguation_and_unicode_code_points(self):
        # 1. Repeated sentence without explicit offsets is rejected with 409 Conflict
        repeated_para = "The estimate is reported in Table 2. Intermediate context sentence. The estimate is reported in Table 2."
        ambiguous = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": repeated_para,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(ambiguous.status_code, 409, ambiguous.text)
        self.assertIn("multiple times", ambiguous.json()["detail"])

        # 2. Nested repeated substring without offsets is rejected with 409
        nested_para = "We measure α. Therefore, We measure α in Table 1."
        nested_ambiguous = self.client.post("/api/v1/writing/revise", json={
            "sentence": "We measure α",
            "paragraph_context": nested_para,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(nested_ambiguous.status_code, 409)

        # 3. Valid explicit offsets for the second occurrence succeed and preserve exact span
        second_start = repeated_para.rindex("The estimate is reported in Table 2.")
        second_end = second_start + len("The estimate is reported in Table 2.")
        resolved_second = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": repeated_para,
            "paragraph_id": "para-repeated-2",
            "target_start": second_start,
            "target_end": second_end,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(resolved_second.status_code, 200, resolved_second.text)
        body = resolved_second.json()
        self.assertEqual(body["paragraph_id"], "para-repeated-2")
        self.assertEqual(body["target_start"], second_start)
        self.assertEqual(body["target_end"], second_end)
        self.assertEqual(body["offset_unit"], "unicode_code_points")
        self.assertEqual(body["plan"]["target_start"], second_start)
        self.assertEqual(body["plan"]["target_end"], second_end)

        # 4. Stale offsets (where slice does not match sentence) are rejected with 422
        stale = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": repeated_para,
            "target_start": 5,
            "target_end": 5 + len("The estimate is reported in Table 2."),
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(stale.status_code, 422)
        self.assertIn("Stale or mismatched", stale.json()["detail"])

        # 5. Out-of-bounds or partial offsets are rejected with 422
        oob = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": repeated_para,
            "target_start": 0,
            "target_end": 9999,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(oob.status_code, 422)

        partial = self.client.post("/api/v1/writing/revise", json={
            "sentence": "The estimate is reported in Table 2.",
            "paragraph_context": repeated_para,
            "target_start": 0,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(partial.status_code, 422)

        # 6. Unicode character offsets with astral emoji and accented characters
        unicode_target = "L’échantillon 🧪 montre α = 0.05."
        unicode_para = f"Préambule 🧪 initial. {unicode_target} Transition 🧪. {unicode_target}"
        u_start = unicode_para.rindex(unicode_target)
        u_end = u_start + len(unicode_target)
        unicode_res = self.client.post("/api/v1/writing/revise", json={
            "sentence": unicode_target,
            "paragraph_context": unicode_para,
            "paragraph_id": "para-unicode",
            "target_start": u_start,
            "target_end": u_end,
            "intention": "no_edit",
            "author_requested_edit": False,
        })
        self.assertEqual(unicode_res.status_code, 200, unicode_res.text)
        self.assertEqual(unicode_res.json()["target_start"], u_start)
        self.assertEqual(unicode_res.json()["target_end"], u_end)
        self.assertEqual(unicode_para[u_start:u_end], unicode_target)


if __name__ == "__main__":
    unittest.main()
