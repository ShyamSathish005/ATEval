"""Command-line entry point for ATEval foundation commands."""

import argparse
import importlib.util
import importlib.metadata
import json
import logging
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__
from .config import load_config
from .logging_config import configure_logging
from .registry import DETECTORS, MODELS

LOG = logging.getLogger("ateval")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _doctor_report(config) -> dict:
    """Inspect local runtime components without contacting external services."""
    package_names = {
        "fastapi": "fastapi", "uvicorn": "uvicorn", "python-multipart": "multipart",
        "torch": "torch", "transformers": "transformers", "scikit-learn": "sklearn",
        "python-docx": "docx", "PyMuPDF": "pymupdf", "spaCy": "spacy",
    }
    packages = {}
    for distribution, module in package_names.items():
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[distribution] = {"installed": version is not None, "version": version,
                                  "importable": importlib.util.find_spec(module) is not None}

    storage = Path(os.environ.get("ATEVAL_HOME", Path.cwd() / ".ateval")).expanduser()
    storage_parent = storage if storage.exists() else storage.parent
    try:
        free_bytes = shutil.disk_usage(storage_parent).free if storage_parent.exists() else None
    except OSError:
        free_bytes = None
    storage_report = {
        "configured": str(storage), "exists": storage.exists(),
        "readable": os.access(storage, os.R_OK) if storage.exists() else None,
        "writable": os.access(storage, os.W_OK) if storage.exists() else os.access(storage_parent, os.W_OK),
        "free_bytes": free_bytes,
    }

    ollama_url = os.environ.get("ATEVAL_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urllib.parse.urlparse(ollama_url)
    ollama_status: dict = {"url": ollama_url, "available": False, "model_configured": False, "model_available": False}
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        ollama_status["model"] = os.environ.get("ATEVAL_OLLAMA_MODEL", "ateval-xtragpt-1_5b-q8_0")
        ollama_status["model_configured"] = bool(ollama_status["model"])
        try:
            with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=0.5) as response:
                tags = json.loads(response.read(1_000_000))
            models = {item.get("name", "") for item in tags.get("models", [])}
            model = ollama_status["model"]
            ollama_status["available"] = True
            ollama_status["model_available"] = model in models or any(name.startswith(f"{model}:") for name in models)
        except (OSError, ValueError, urllib.error.URLError):
            pass
    else:
        ollama_status["reason"] = "Ollama health checks are limited to loopback HTTP URLs."

    api_dependencies = all(packages[name]["importable"] for name in ("fastapi", "uvicorn", "python-multipart"))
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=0.4) as response:
            api_running = response.status == 200
    except (OSError, urllib.error.URLError):
        api_running = False
    try:
        disk_free = shutil.disk_usage(Path.cwd()).free
    except OSError:
        disk_free = None
    return {
        "python": {"version": sys.version.split()[0], "supported": sys.version_info >= (3, 11)},
        "packages": packages,
        "backend": {"dependencies_available": api_dependencies, "local_api_running": api_running},
        "frontend": {"build_available": (PROJECT_ROOT / "frontend" / "dist" / "client" / "index.html").is_file()},
        "ollama": ollama_status,
        "latex": {"latexmk": shutil.which("latexmk"), "pdflatex": shutil.which("pdflatex")},
        "storage": storage_report,
        "working_directory_free_bytes": disk_free,
        "offline_default": config.offline,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ateval", description="Reproducible academic text evaluation research CLI")
    parser.add_argument("--config", help="Optional TOML configuration file")
    parser.add_argument("--json-logs", action="store_true", help="Emit structured JSON logs")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check runtime and optional components")
    api = sub.add_parser("api", help="Run the local ATEval API")
    api.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1", "localhost", "0.0.0.0"), help="Bind host; 0.0.0.0 is for explicitly configured container/proxy deployments only")
    api.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")), help="API port; defaults to PORT or 8000")
    papers = sub.add_parser("papers", help="Inspect the research registry")
    papers.add_subparsers(dest="papers_command", required=True).add_parser("audit", help="Check registered paper identifiers and source links")
    detector = sub.add_parser("detector", help="Inspect detector implementations")
    detector.add_subparsers(dest="detector_command", required=True).add_parser("list", help="List detector status")
    model = sub.add_parser("model", help="Inspect configured model components")
    model.add_subparsers(dest="model_command", required=True).add_parser("list", help="List model status")
    writing = sub.add_parser("writing", help="Analyze academic writing without changing the source")
    writing_sub = writing.add_subparsers(dest="writing_command", required=True)
    writing_analyze = writing_sub.add_parser("analyze", help="Analyze a manuscript and print review-only suggestions")
    writing_analyze.add_argument("file", help="Input .txt, .tex, .docx or .pdf file")
    writing_analyze.add_argument("--output", help="Write analysis JSON to a new report file (never modifies input)")
    from .revisions.cli import add_revisions_parser
    add_revisions_parser(sub)
    sub.add_parser("version", help="Show ATEval version")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    configure_logging(config.log_level, json_output=args.json_logs)
    if args.command == "version":
        print(__version__)
    elif args.command == "doctor":
        print(json.dumps(_doctor_report(config), indent=2))
        LOG.info("doctor checks completed")
        return 0 if sys.version_info >= (3, 11) else 2
    elif args.command == "api":
        try:
            import uvicorn
        except ImportError as exc:
            parser.error("Install the UI API dependencies with: python -m pip install -e '.[ui-server]'")
        uvicorn.run("ateval.api:app", host=args.host, port=args.port, log_level=config.log_level.lower())
    elif args.command == "detector":
        print(json.dumps([spec.__dict__ for spec in DETECTORS], indent=2))
    elif args.command == "model":
        print(json.dumps([spec.__dict__ for spec in MODELS], indent=2))
    elif args.command == "writing" and args.writing_command == "analyze":
        from pathlib import Path
        from .writing import analyze_text, extract_document
        source_path = Path(args.file)
        try:
            extracted = extract_document(source_path.name, source_path.read_bytes())
            report = analyze_text(extracted["text"], document_name=extracted["name"], document_format=extracted["format"])
            report["ingestion"] = {key: value for key, value in extracted.items() if key != "text"}
            serialized = json.dumps(report, indent=2, ensure_ascii=False)
            if args.output:
                target = Path(args.output)
                if target.resolve() == source_path.resolve():
                    parser.error("Analysis output must not overwrite the source manuscript")
                if target.exists():
                    parser.error(f"Analysis output already exists: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(serialized + "\n", encoding="utf-8")
                print(f"Analysis report written to {target}")
            else:
                print(serialized)
        except (OSError, ValueError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == "revisions":
        from .revisions.cli import run_revisions
        try:
            return run_revisions(args)
        except (OSError, ValueError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == "papers":
        from pathlib import Path
        registry = Path(__file__).resolve().parent.parent / "docs" / "literature_review.md"
        content = registry.read_text(encoding="utf-8")
        sections = re.split(r"(?=^### P\d{2} — )", content, flags=re.MULTILINE)
        entries = [section for section in sections if re.match(r"^### P\d{2} — ", section)]
        missing_sources = [re.match(r"^### (P\d{2})", section).group(1) for section in entries if not re.search(r"https?://|\[[^]]+\]\([^)]*\)", section)]
        print(json.dumps({"registry_file": str(registry), "records": len(entries), "records_without_any_source_url": missing_sources, "bibliographic_and_licence_verification": "incomplete; see review method and per-entry status"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
