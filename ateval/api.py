"""Local-only FastAPI surface over ATEval's shared metadata services.

The service stores experiment metadata and explicitly imported dataset copies
under ``.ateval`` in the project directory. Raw document text is never logged
or returned by overview/list endpoints.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import itertools
import io
import json
import os
import platform
import shutil
import sqlite3
import sys
import threading
import unicodedata
import uuid
from collections import Counter
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from pydantic import BaseModel, Field

from . import __version__
from .registry import DETECTORS
from .detectors import evaluate_stylometric_baseline
from .schema import ALLOWED_LABELS, REQUIRED_FIELDS, DatasetRecord
from .writing import analyze_text, apply_accepted_suggestions, extract_document, validate_preservation
from .revisions.classic_models import context_text
from .revisions.academic_generation import XtraGPTOllamaGenerator
from .revisions.scar import SCARRevisionEngine, compare_claim_cues, revision_necessity_gate
from .revisions.protected_content import protect_content
from .manuscript_analysis import analyze_manuscript, import_manuscript
from .manuscript_analysis.exports import export_reviewed_manuscript
from .revisions.human_evaluation import (
    ANNOTATIONS_PATH,
    PACKET_PATH,
    analyze_annotations,
    append_annotation,
    initialize_evaluation,
    public_packet,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_HOME = Path(os.environ.get("ATEVAL_HOME", PROJECT_ROOT / ".ateval")).expanduser().resolve()
RAW_DATA_DIR = APP_HOME / "datasets" / "raw"
DB_PATH = APP_HOME / "ateval.sqlite3"
MAX_UPLOAD_BYTES = max(1, int(os.environ.get("ATEVAL_UPLOAD_LIMIT_BYTES", str(25 * 1024 * 1024))))
API_HOSTS = {"127.0.0.1", "localhost", "terminal.local"}
_configured_hosts = os.environ.get("ATEVAL_ALLOWED_HOSTS", "")
API_HOSTS.update(host.strip().lower() for host in _configured_hosts.split(",") if host.strip())
PUBLIC_DEMO_MODE = os.environ.get("ATEVAL_PUBLIC_DEMO", "0").lower() in {"1", "true", "yes"}
PUBLIC_DEMO_REQUESTS_PER_MINUTE = max(1, int(os.environ.get("ATEVAL_PUBLIC_RATE_LIMIT_PER_MINUTE", "20")))
_public_rate_counts: dict[tuple[str, int], int] = {}
_public_rate_lock = threading.Lock()
DEFAULT_CORS_ORIGINS = {
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:4173", "http://127.0.0.1:4173",
}
_cors_origins_from_env = os.environ.get("ATEVAL_CORS_ORIGINS")
ALLOWED_CORS_ORIGINS = tuple(
    origin.strip().rstrip("/")
    for origin in (_cors_origins_from_env.split(",") if _cors_origins_from_env else DEFAULT_CORS_ORIGINS)
    if origin.strip() and origin.strip().lower() not in {"null", "*"}
)
_workspace_client_build = PROJECT_ROOT / "frontend" / "dist" / "client"
_packaged_client_build = Path(__file__).resolve().parent / "static"
CLIENT_BUILD_DIR = _workspace_client_build if (_workspace_client_build / "index.html").is_file() else _packaged_client_build
REVISION_MODEL_DIR = PROJECT_ROOT / "models" / "revisions" / "iterater_human_grouped_v1"
REVISION_MODEL_PATH = REVISION_MODEL_DIR / "local-logistic_regression.joblib"
REVISION_MODEL_METADATA = REVISION_MODEL_DIR / "local-logistic_regression.metadata.json"

def _loopback_ollama_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("ATEVAL_OLLAMA_URL must be an HTTP loopback URL")
    return value.rstrip("/")


XTRAGPT_OLLAMA_URL = _loopback_ollama_url(
    os.environ.get("ATEVAL_OLLAMA_URL", "http://127.0.0.1:11434")
)
XTRAGPT_OLLAMA_MODEL = os.environ.get("ATEVAL_OLLAMA_MODEL", "ateval-xtragpt-1_5b-q8_0")
XTRAGPT_GGUF_PATH = Path(
    os.environ.get(
        "ATEVAL_XTRAGPT_GGUF",
        str(Path.home() / ".cache" / "ateval" / "models" / "XtraGPT-1.5B-q4.gguf"),
    )
).expanduser()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def upload_basename(filename: str | None, fallback: str = "manuscript.txt") -> str:
    """Normalize both POSIX and Windows client paths to a filename only."""
    return (filename or fallback).replace("\\", "/").rsplit("/", 1)[-1] or fallback


@contextmanager
def get_db() -> sqlite3.Connection:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, original_filename TEXT NOT NULL,
              stored_path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
              row_count INTEGER NOT NULL, validation_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiments (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
              dataset_id TEXT, config_json TEXT NOT NULL, created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
              payload_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="ATEval Local API", version=__version__, lifespan=lifespan)


class MaxRequestBodyMiddleware:
    """Reject oversized HTTP bodies before multipart parsing can spool them."""

    def __init__(self, application: ASGIApp, max_bytes: int) -> None:
        self.application = application
        self.max_bytes = max_bytes + 1024 * 1024  # Allow multipart framing and form fields.

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            await self.application(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._too_large(send)
                    return
            except ValueError:
                pass
        observed = 0

        async def limited_receive():
            nonlocal observed
            message = await receive()
            if message["type"] == "http.request":
                observed += len(message.get("body", b""))
                if observed > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.application(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await self._too_large(send)

    async def _too_large(self, send: Send) -> None:
        body = b'{"detail":"Request body exceeds configured upload limit"}'
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


class RequestBodyTooLarge(Exception):
    pass


@app.middleware("http")
async def local_origin_guard(request, call_next):
    """Reject cross-site browser writes and host-header rebinding attempts."""
    host_header = request.headers.get("host", "").split(":", 1)[0].lower()
    if host_header and host_header not in API_HOSTS:
        return await _json_error(400, "Host is not allowed")
    if PUBLIC_DEMO_MODE and request.url.path.startswith("/api/"):
        safe_reads = {
            "/api/v1/health", "/api/v1/system", "/api/v1/detectors",
            "/api/v1/datasets", "/api/v1/experiments", "/api/v1/reports",
        }
        if not (request.method == "GET" and request.url.path in safe_reads) and not (
            request.method == "POST" and request.url.path == "/api/v1/demo/sample"
        ):
            return await _json_error(403, "Public demo accepts only the synthetic sample; uploads and state changes are disabled")
        client_host = request.client.host if request.client else "unknown"
        if os.environ.get("RENDER", "").lower() == "true":
            forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            if forwarded_for:
                client_host = forwarded_for
        minute = int(datetime.now(timezone.utc).timestamp() // 60)
        with _public_rate_lock:
            for key in tuple(_public_rate_counts):
                if key[1] < minute - 1:
                    _public_rate_counts.pop(key, None)
            key = (client_host, minute)
            _public_rate_counts[key] = _public_rate_counts.get(key, 0) + 1
            if _public_rate_counts[key] > PUBLIC_DEMO_REQUESTS_PER_MINUTE:
                return await _json_error(429, "Public demo rate limit exceeded; retry next minute")
    origin = request.headers.get("origin")
    if origin:
        request_origin = f"{request.url.scheme}://{request.headers.get('host', '').lower()}"
        normalized_origin = origin.rstrip("/").lower()
        if normalized_origin != request_origin and normalized_origin not in ALLOWED_CORS_ORIGINS:
            return await _json_error(403, "Cross-origin requests are not allowed")
    return await call_next(request)


# CORS wraps the origin guard so even rejected requests from an explicitly
# trusted local frontend receive readable error responses. The normal Vite
# proxy strips Origin because browser-to-frontend requests are same-origin.
app.add_middleware(MaxRequestBodyMiddleware, max_bytes=MAX_UPLOAD_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


async def _json_error(status: int, detail: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status, content={"detail": detail})


def _dataset_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "name": row["name"], "original_filename": row["original_filename"],
        "sha256": row["sha256"], "size_bytes": row["size_bytes"], "row_count": row["row_count"],
        "created_at": row["created_at"], "validation": json.loads(row["validation_json"]),
    }


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": __version__, "storage": "ephemeral demo" if PUBLIC_DEMO_MODE else "local"}


@app.get("/api/v1/system")
def system_status():
    usage = shutil.disk_usage(APP_HOME if APP_HOME.exists() else PROJECT_ROOT)
    torch_available = importlib.util.find_spec("torch") is not None
    accelerator = "not inspected (PyTorch unavailable)"
    if torch_available:
        try:
            import torch
            accelerator = "MPS" if torch.backends.mps.is_available() else ("CUDA" if torch.cuda.is_available() else "CPU")
        except Exception:
            accelerator = "PyTorch installed; accelerator check failed"
    return {
        "version": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
        "local_only": not PUBLIC_DEMO_MODE, "public_demo": PUBLIC_DEMO_MODE,
        "uploads_enabled": not PUBLIC_DEMO_MODE, "offline_default": True, "accelerator": accelerator,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "torch_available": torch_available,
        "transformers_available": importlib.util.find_spec("transformers") is not None,
        "latexmk_available": shutil.which("latexmk") is not None,
        "pdflatex_available": shutil.which("pdflatex") is not None,
        "storage_root": "ephemeral public demo" if PUBLIC_DEMO_MODE else str(APP_HOME),
        "free_bytes": 0 if PUBLIC_DEMO_MODE else usage.free,
        "neural_revision": _ollama_revision_status(),
    }


@app.get("/api/v1/detectors")
def detectors():
    return [{**spec.__dict__, "available": spec.name == "stylometric-baseline",
             "availability_note": "executable but unvalidated" if spec.name == "stylometric-baseline" else "planned"}
            for spec in DETECTORS]


class DetectorEvaluationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)


@app.post("/api/v1/evaluator/stylometric")
def evaluate_stylometric(payload: DetectorEvaluationRequest):
    try:
        return evaluate_stylometric_baseline(payload.text)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/datasets")
def list_datasets():
    with get_db() as db:
        rows = db.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
    return [_dataset_dict(row) for row in rows]


def _parse_dataset(path: Path, extension: str) -> dict[str, Any]:
    if extension == ".csv":
        def csv_rows():
            nonlocal headers
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames or []
                yield from reader
        headers = []
        rows = csv_rows()
    else:
        headers = []
        def jsonl_rows():
            nonlocal headers
            with path.open("r", encoding="utf-8-sig") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid JSON on line {line_number}") from exc
                    if not isinstance(item, dict):
                        raise ValueError(f"Each JSONL line must be an object (line {line_number})")
                    if not headers:
                        headers = list(item.keys())
                    yield item
        rows = jsonl_rows()
    first_row = next(rows, None)
    missing_columns = [field for field in REQUIRED_FIELDS if field not in headers]
    label_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    generator_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    invalid_labels = 0
    invalid_records: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    duplicate_ids = 0
    text_hashes: set[str] = set()
    duplicate_texts = 0
    row_count = 0
    row_stream = itertools.chain([first_row], rows) if first_row is not None else ()
    for index, row in enumerate(row_stream, start=1):
        row_count = index
        for key in REQUIRED_FIELDS:
            if not str(row.get(key, "")).strip():
                missing_counts[key] += 1
        if row.get("label") not in ALLOWED_LABELS:
            invalid_labels += 1
        else:
            label_counts[str(row["label"])] += 1
        if row.get("source_id"):
            source_counts[str(row["source_id"])] += 1
        if row.get("domain"):
            domain_counts[str(row["domain"])] += 1
        if row.get("generator"):
            generator_counts[str(row["generator"])] += 1
        sample_id = str(row.get("sample_id", ""))
        if sample_id and sample_id in sample_ids:
            duplicate_ids += 1
        elif sample_id:
            sample_ids.add(sample_id)
        text = str(row.get("text", ""))
        if text:
            normalized = unicodedata.normalize("NFKC", text).strip()
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if digest in text_hashes:
                duplicate_texts += 1
            else:
                text_hashes.add(digest)
        try:
            DatasetRecord.from_mapping(row)
        except (ValueError, TypeError) as exc:
            if len(invalid_records) < 20:
                invalid_records.append({"row": index, "reason": str(exc)})
    return {
        "schema_valid": not missing_columns and not missing_counts and not invalid_labels and not invalid_records,
        "headers": headers, "missing_columns": missing_columns, "row_count": row_count,
        "label_distribution": dict(label_counts), "source_distribution": dict(source_counts),
        "domain_distribution": dict(domain_counts), "generator_distribution": dict(generator_counts),
        "missing_value_counts": dict(missing_counts), "invalid_label_rows": invalid_labels,
        "invalid_record_examples": invalid_records, "duplicate_sample_ids": duplicate_ids,
        "exact_duplicate_texts": duplicate_texts, "near_duplicates": "not evaluated",
    }


class DatasetImportResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    sha256: str
    size_bytes: int
    row_count: int
    created_at: str
    validation: dict[str, Any]


@app.post("/api/v1/datasets/import", response_model=DatasetImportResponse)
async def import_dataset(file: UploadFile = File(...), name: str | None = None):
    original_name = Path(file.filename or "dataset").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".csv", ".jsonl"}:
        raise HTTPException(status_code=415, detail="Choose a CSV or JSONL file")
    dataset_id = uuid.uuid4().hex
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    destination = RAW_DATA_DIR / f"{dataset_id}{suffix}"
    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Dataset exceeds the 50 MiB import limit")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="The selected file is empty")
        validation = _parse_dataset(destination, suffix)
        created = now_utc()
        dataset_name = (name or Path(original_name).stem).strip()[:120] or "Imported dataset"
        with get_db() as db:
            db.execute(
                "INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (dataset_id, dataset_name, original_name, str(destination), digest.hexdigest(), size,
                 validation["row_count"], json.dumps(validation), created),
            )
        return {"id": dataset_id, "name": dataset_name, "original_filename": original_name,
                "sha256": digest.hexdigest(), "size_bytes": size, "row_count": validation["row_count"],
                "created_at": created, "validation": validation}
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/api/v1/datasets/{dataset_id}/validation")
def dataset_validation(dataset_id: str):
    with get_db() as db:
        row = db.execute("SELECT validation_json FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return json.loads(row["validation_json"])


@app.delete("/api/v1/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    with get_db() as db:
        row = db.execute("SELECT stored_path FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        # Only delete files under the app's managed raw-data directory.
        stored = Path(row["stored_path"]).resolve()
        if RAW_DATA_DIR.resolve() not in stored.parents:
            raise HTTPException(status_code=400, detail="Dataset path is outside managed storage")
        stored.unlink(missing_ok=True)
        db.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    return {"deleted": True}


class ExperimentDraft(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dataset_id: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class WritingAnalysisRequest(BaseModel):
    text: str = Field(max_length=2_000_000)
    document_name: str = Field(default="Untitled document", max_length=255)
    document_format: str = Field(default="txt", max_length=12)


class RevisionIntentRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=5000)
    context_before: str = Field(default="", max_length=12000)
    context_after: str = Field(default="", max_length=12000)
    section_type: str = Field(default="unknown", max_length=120)


class WritingAuditRequest(BaseModel):
    text: str = Field(max_length=2_000_000)
    document_name: str = Field(default="Untitled document", max_length=255)
    document_format: str = Field(default="txt", max_length=12)
    accepted_suggestion_ids: list[str] = Field(default_factory=list, max_length=2000)
    rejected_suggestion_ids: list[str] = Field(default_factory=list, max_length=2000)
    neural_revision: dict[str, Any] | None = None


class RevisionProposalRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=20_000)
    paragraph_context: str = Field(default="", max_length=80_000)
    previous_sentence: str = Field(default="", max_length=20_000)
    next_sentence: str = Field(default="", max_length=20_000)
    section_type: str = Field(default="unknown", max_length=120)
    instruction: str = Field(default="Improve academic clarity conservatively.", min_length=1, max_length=2000)
    intention: Literal["no_edit", "clarity", "grammar", "redundancy", "structure", "technical_review"] | None = None
    author_requested_edit: bool = False
    protected_terminology: list[str] = Field(default_factory=list, max_length=100)
    citations: list[str] = Field(default_factory=list, max_length=100)


class ManuscriptEditValidationRequest(BaseModel):
    original: str = Field(min_length=1, max_length=20_000)
    candidate: str = Field(min_length=1, max_length=20_000)
    protected_terminology: list[str] = Field(default_factory=list, max_length=100)


class HumanEvaluationAnnotationRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=100)
    reviewer_id: str = Field(min_length=1, max_length=64)
    editing_necessity: str = Field(min_length=1, max_length=64)
    confidence: int = Field(ge=1, le=5)
    candidate_assessments: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    abstained: bool = False
    reviewer_comments: str = Field(default="", max_length=4000)


def _ollama_revision_status() -> dict[str, Any]:
    try:
        import urllib.request
        request = urllib.request.Request(f"{XTRAGPT_OLLAMA_URL.rstrip('/')}/api/tags")
        with urllib.request.urlopen(request, timeout=0.45) as response:
            available = json.loads(response.read().decode("utf-8")).get("models", [])
        model_names = {str(item.get("name", "")) for item in available}
        model_available = any(
            value == XTRAGPT_OLLAMA_MODEL or value.startswith(XTRAGPT_OLLAMA_MODEL + ":")
            for value in model_names
        )
        return {
            "available": model_available,
            "model": XTRAGPT_OLLAMA_MODEL if model_available else None,
            "runtime": "Ollama loopback API",
            "quantization": "Q8_0",
            "reason": None if model_available else "The configured local XtraGPT model tag is not installed.",
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "available": False, "model": None, "runtime": "Ollama loopback API",
            "quantization": "Q8_0", "reason": "Local Ollama is not responding.",
        }


@app.get("/api/v1/writing/status")
def writing_status():
    torch_available = importlib.util.find_spec("torch") is not None
    spacy_available = importlib.util.find_spec("spacy") is not None
    model_available = False
    if spacy_available:
        try:
            import spacy
            model_available = spacy.util.is_package("en_core_web_sm") or spacy.util.is_package("en_core_web_trf")
        except Exception:
            model_available = False
    neural_revision = _ollama_revision_status()
    return {
        "baseline": "available",
        "torch_available": torch_available,
        "spacy_available": spacy_available,
        "local_english_pipeline_available": model_available,
        "remote_models": False,
        "model_downloads_automatic": False,
        "source_text_saved_by_analysis": False,
        "revision_intent_model_available": REVISION_MODEL_PATH.is_file() and REVISION_MODEL_METADATA.is_file() and importlib.util.find_spec("sklearn") is not None,
        "revision_intent_model_dependency_available": importlib.util.find_spec("sklearn") is not None,
        "neural_revision": neural_revision,
    }


@app.post("/api/v1/writing/revise")
def writing_revision_proposal(payload: RevisionProposalRequest):
    paragraph = payload.paragraph_context or payload.sentence
    target_start = paragraph.find(payload.sentence)
    if target_start < 0:
        raise HTTPException(status_code=422, detail="The target sentence must occur exactly in the supplied paragraph context")
    try:
        gate = revision_necessity_gate(
            selected_text=payload.sentence,
            paragraph_context=paragraph,
            intention=payload.intention,
            author_requested_edit=payload.author_requested_edit,
        )
        generator = None
        if gate.decision in {"CLARITY_IMPROVEMENT", "GRAMMAR_IMPROVEMENT", "REDUNDANCY_REVIEW", "STRUCTURAL_IMPROVEMENT"}:
            status = _ollama_revision_status()
            if not status["available"]:
                raise HTTPException(status_code=503, detail=status["reason"])
            generator = XtraGPTOllamaGenerator(
                XTRAGPT_OLLAMA_MODEL,
                model_file=XTRAGPT_GGUF_PATH,
                base_url=XTRAGPT_OLLAMA_URL,
                mode="ateval",
                max_new_tokens=192,
                context_length=2048,
            )
        engine = SCARRevisionEngine(generator)
        result = engine.revise(
            paragraph,
            target_start=target_start,
            target_end=target_start + len(payload.sentence),
            intention=payload.intention,
            author_requested_edit=payload.author_requested_edit,
            protected_terms=tuple(payload.protected_terminology),
            citations=tuple(payload.citations),
            section=payload.section_type,
        )
        return result.to_dict()
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Local XtraGPT revision failed: {exc}") from exc


@app.post("/api/v1/review/initialize")
def initialize_human_review():
    """Create the immutable local M4.4 packet once without exposing its key."""
    try:
        return initialize_evaluation()
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not initialize review packet: {exc}") from exc


@app.get("/api/v1/review/packet")
def human_review_packet(reviewer_id: str):
    """Return blinded, reviewer-specific candidate order without model identities."""
    try:
        if not PACKET_PATH.is_file():
            raise HTTPException(status_code=404, detail="The human-evaluation packet is not initialized")
        return {"reviewer_id": reviewer_id, "items": public_packet(reviewer_id)}
    except HTTPException:
        raise
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/review/annotations")
def save_human_review_annotation(payload: HumanEvaluationAnnotationRequest):
    try:
        append_annotation(payload.model_dump())
        return {"saved": True, "item_id": payload.item_id, "reviewer_id": payload.reviewer_id}
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/review/status")
def human_review_status():
    annotation_count = (
        sum(1 for line in ANNOTATIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
        if ANNOTATIONS_PATH.is_file() else 0
    )
    return {
        "initialized": PACKET_PATH.is_file(),
        "annotation_count": annotation_count,
        "analysis": analyze_annotations() if ANNOTATIONS_PATH.is_file() else {"status": "pending_human_annotations"},
        "blind": True,
        "model_identities_exposed": False,
        "detector_scores_exposed": False,
    }


@app.get("/api/v1/review/export")
def export_human_review_annotations():
    if not ANNOTATIONS_PATH.is_file():
        return {"schema": "ateval-m44-review-annotations-v1", "annotations": []}
    annotations = [
        json.loads(line) for line in ANNOTATIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return {"schema": "ateval-m44-review-annotations-v1", "annotations": annotations}


@app.post("/api/v1/writing/revision-intent")
def writing_revision_intent(payload: RevisionIntentRequest):
    """Predict one likely edit label as an advisory; never implies an edit is needed."""
    if not REVISION_MODEL_PATH.is_file() or not REVISION_MODEL_METADATA.is_file():
        raise HTTPException(status_code=503, detail="The trained IteraTeR intent model is not installed")
    try:
        import joblib
        metadata = json.loads(REVISION_MODEL_METADATA.read_text(encoding="utf-8"))
        digest = hashlib.sha256(REVISION_MODEL_PATH.read_bytes()).hexdigest()
        if digest != metadata.get("sha256"):
            raise HTTPException(status_code=503, detail="Intent model checksum does not match its metadata")
        model = joblib.load(REVISION_MODEL_PATH)
        from types import SimpleNamespace
        record = SimpleNamespace(
            section_type=payload.section_type,
            context_before=payload.context_before,
            context_after=payload.context_after,
            original_text=payload.sentence,
            metadata={},
        )
        features = [context_text(record, "local")]
        probabilities = model.predict_proba(features)[0]
        classes = list(map(str, model.classes_))
        best = max(range(len(probabilities)), key=lambda index: float(probabilities[index]))
        label = classes[best]
        score = float(probabilities[best])
        return {
            "model": "IteraTeR-HUMAN grouped local word/character TF-IDF logistic regression",
            "predicted_intent": label,
            "top_class_score": score,
            "score_kind": "uncalibrated LogisticRegression predict_proba output; not a probability of correctness",
            "suggested_action": label.replace("_", " "),
            "modification_necessary": None,
            "decision": "advisory_only",
            "author_review_required": True,
            "automatic_edit_applied": False,
            "model_macro_f1": json.loads((REVISION_MODEL_DIR / "comparison.json").read_text(encoding="utf-8"))["models"]["local"]["logistic_regression"]["macro_f1"],
            "limitations": [
                "This model predicts an annotation found on a human-edited example; it does not decide whether the supplied sentence needs an edit.",
                "Held-out macro F1 is weak; treat the predicted intention as a research cue, not a recommendation to change text.",
                "The score is not a probability that an edit is correct or that meaning will be preserved.",
            ],
        }
    except HTTPException:
        raise
    except (OSError, ValueError, KeyError, ImportError, AttributeError) as exc:
        raise HTTPException(status_code=503, detail=f"Intent model is unavailable: {exc}") from exc


@app.post("/api/v1/writing/analyze")
def writing_analyze(payload: WritingAnalysisRequest):
    try:
        return analyze_text(payload.text, document_name=payload.document_name, document_format=payload.document_format)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/writing/ingest")
async def writing_ingest(file: UploadFile = File(...)):
    filename = upload_basename(file.filename, "document.txt")
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_BYTES}-byte limit")
        result = extract_document(filename, content)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=415 if "optional" in str(exc) else 422, detail=str(exc)) from exc
    finally:
        await file.close()
    return result


@app.post("/api/v1/manuscripts/analyze")
async def manuscript_analyze(file: UploadFile = File(...)):
    """Analyze a manuscript locally and return source-mapped, method-honest results."""
    filename = upload_basename(file.filename)
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Manuscript exceeds the {MAX_UPLOAD_BYTES}-byte upload limit")
        bundle = import_manuscript(filename, content)
        result = analyze_manuscript(bundle, requested_config={"detectors_requested": "registered methods", "editing_requested": False})
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await file.close()
    return result


@app.post("/api/v1/demo/sample")
def analyze_public_synthetic_sample():
    """Analyze a fixed synthetic document without accepting user-provided text."""
    source = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{Introduction}\n"
        "This synthetic sample demonstrates local manuscript analysis. "
        "It contains no research findings, personal data, or unpublished work.\n"
        "\\end{document}\n"
    ).encode("utf-8")
    bundle = import_manuscript("ateval-synthetic-demo.tex", source)
    return analyze_manuscript(bundle, requested_config={"detectors_requested": "registered methods", "editing_requested": False})


@app.post("/api/v1/manuscripts/export")
async def manuscript_export(file: UploadFile = File(...), accepted_edits: str = Form(...)):
    """Export individually approved patches into the original writable format."""
    filename = upload_basename(file.filename)
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Upload exceeds the {MAX_UPLOAD_BYTES}-byte limit")
        patches = json.loads(accepted_edits)
        if not isinstance(patches, list) or len(patches) > 5000:
            raise ValueError("accepted_edits must be a list containing at most 5,000 reviewed edits")
        output, media_type, output_name = export_reviewed_manuscript(filename, content, patches)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="accepted_edits must be valid JSON") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await file.close()
    headers = {"Content-Disposition": f'attachment; filename="{output_name}"'}
    return StreamingResponse(io.BytesIO(output), media_type=media_type, headers=headers)


@app.post("/api/v1/manuscripts/validate-edit")
def manuscript_validate_edit(payload: ManuscriptEditValidationRequest):
    try:
        original = protect_content(payload.original, payload.protected_terminology)
        candidate = protect_content(payload.candidate, payload.protected_terminology)
        before = [item.original for item in original.mapping]
        after = [item.original for item in candidate.mapping]
        structural = {"passed": before == after, "source_protected_spans": len(before), "candidate_protected_spans": len(after)}
        if not structural["passed"]:
            return {"review_decision": "REJECT_STRUCTURAL_CHANGE", "structural_validation": structural, "claim_integrity": None, "semantic_equivalence": "not_assessed"}
        claim = compare_claim_cues(payload.original, payload.candidate)
        decision = "REJECT_POTENTIAL_MEANING_CHANGE" if claim.status == "cue_mismatch" else "ACCEPT_FOR_AUTHOR_REVIEW"
        return {"review_decision": decision, "structural_validation": structural, "claim_integrity": claim.to_dict(), "semantic_equivalence": "not_assessed"}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/writing/audits")
def writing_save_audit(payload: WritingAuditRequest):
    try:
        analysis = analyze_text(payload.text, document_name=payload.document_name, document_format=payload.document_format)
        suggestions = analysis["suggestions"]
        by_id = {item["id"]: item for item in suggestions}
        accepted = set(payload.accepted_suggestion_ids)
        rejected = set(payload.rejected_suggestion_ids)
        unknown = (accepted | rejected) - set(by_id)
        if unknown:
            raise HTTPException(status_code=422, detail="One or more suggestion IDs do not belong to this document analysis")
        if accepted & rejected:
            raise HTTPException(status_code=422, detail="A suggestion cannot be both accepted and rejected")
        transformed, applied = apply_accepted_suggestions(payload.text, suggestions, accepted)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit_id = uuid.uuid4().hex
    created = now_utc()
    audit = {
        "audit_schema": "ateval-writing-audit-v1",
        "created_at": created,
        "document": analysis["document"],
        "source_text_stored": False,
        "source_sha256": analysis["document"]["sha256"],
        "candidate_suggestions": [
            {key: item[key] for key in ("id", "start", "end", "source", "replacement", "intent", "edit_intention", "issue", "reason", "risk", "review_required", "stage_one") if key in item}
            for item in suggestions
        ],
        "accepted_suggestion_ids": sorted(accepted),
        "rejected_suggestion_ids": sorted(rejected),
        "unresolved_suggestion_ids": sorted(set(by_id) - accepted - rejected),
        "applied_changes": applied,
        "preservation_validation": validate_preservation(payload.text, transformed),
        "result_sha256": hashlib.sha256(transformed.encode("utf-8")).hexdigest(),
        "accepted_change_count": len(applied),
        "neural_revision_review": payload.neural_revision,
        "privacy_note": "The full source and revised manuscript are not stored. The audit includes candidate edit snippets, decisions, and source/result hashes.",
    }
    with get_db() as db:
        db.execute("INSERT INTO reports VALUES (?, ?, ?, ?, ?)", (audit_id, "writing_audit", f"Writing review · {Path(payload.document_name).name}", json.dumps(audit, ensure_ascii=False), created))
    return {"id": audit_id, "kind": "writing_audit", "title": f"Writing review · {Path(payload.document_name).name}", "created_at": created, "audit": audit}


@app.get("/api/v1/experiments")
def list_experiments():
    with get_db() as db:
        rows = db.execute("SELECT * FROM experiments ORDER BY created_at DESC").fetchall()
    return [{"id": row["id"], "name": row["name"], "status": row["status"],
             "dataset_id": row["dataset_id"], "configuration": json.loads(row["config_json"]),
             "created_at": row["created_at"], "updated_at": row["updated_at"]} for row in rows]


@app.post("/api/v1/experiments")
def create_experiment_draft(payload: ExperimentDraft):
    experiment_id = uuid.uuid4().hex
    created = now_utc()
    with get_db() as db:
        if payload.dataset_id and not db.execute("SELECT 1 FROM datasets WHERE id = ?", (payload.dataset_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Dataset not found")
        db.execute("INSERT INTO experiments VALUES (?, ?, 'draft', ?, ?, ?, ?)",
                   (experiment_id, payload.name.strip(), payload.dataset_id,
                    json.dumps(payload.configuration), created, created))
    return {"id": experiment_id, "name": payload.name.strip(), "status": "draft",
            "dataset_id": payload.dataset_id, "configuration": payload.configuration,
            "created_at": created, "updated_at": created}


@app.post("/api/v1/experiments/{experiment_id}/run")
def run_experiment(experiment_id: str):
    with get_db() as db:
        exists = db.execute("SELECT 1 FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Experiment not found")
    raise HTTPException(status_code=409, detail="No detector is currently implemented and tested; this draft cannot run yet")


@app.post("/api/v1/experiments/{experiment_id}/cancel")
def cancel_experiment(experiment_id: str):
    with get_db() as db:
        cursor = db.execute("UPDATE experiments SET status = 'cancelled', updated_at = ? WHERE id = ? AND status = 'draft'",
                            (now_utc(), experiment_id))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=409, detail="Only saved drafts can be cancelled")
    return {"id": experiment_id, "status": "cancelled"}


@app.get("/api/v1/events/{experiment_id}")
async def experiment_events(experiment_id: str):
    with get_db() as db:
        row = db.execute("SELECT id, status, updated_at FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    async def event_stream() -> AsyncIterator[str]:
        yield f"event: status\ndata: {json.dumps(dict(row))}\n\n"
        yield ": draft has no running worker\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/reports")
def list_reports():
    with get_db() as db:
        rows = db.execute("SELECT id, kind, title, created_at FROM reports ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/v1/reports/{report_id}")
def get_report(report_id: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"id": row["id"], "kind": row["kind"], "title": row["title"],
            "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}


@app.get("/{frontend_path:path}", include_in_schema=False)
def local_frontend(frontend_path: str, request: Request):
    """Serve the built local UI through the API origin for production runs."""
    if frontend_path == "api" or frontend_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index_file = CLIENT_BUILD_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend build is unavailable; use the Vite development proxy.")
    if frontend_path:
        candidate = (CLIENT_BUILD_DIR / frontend_path).resolve()
        try:
            candidate.relative_to(CLIENT_BUILD_DIR.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Asset not found") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        if not request.headers.get("accept", "").lower().startswith("text/html"):
            raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(index_file)
