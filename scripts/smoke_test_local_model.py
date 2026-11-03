#!/usr/bin/env python3
"""Run real local Ollama revision scenarios; never substitutes a mock response."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ateval.revisions.academic_generation import AcademicRevisionRequest, XtraGPTOllamaGenerator  # noqa: E402
from ateval.revisions.scar import SCARRevisionEngine  # noqa: E402


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    base_url = os.environ.get("ATEVAL_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("ATEVAL_OLLAMA_MODEL", "ateval-xtragpt-1_5b-q8_0")
    model_file = os.environ.get("ATEVAL_XTRAGPT_GGUF", str(Path.home() / ".cache/ateval/models/XtraGPT-1.5B-q4.gguf"))
    try:
        tags = _get_json(f"{base_url}/api/tags")
        version = _get_json(f"{base_url}/api/version").get("version", "unknown")
    except Exception as exc:
        print(f"Local Ollama is unavailable at {base_url}: {exc}", file=sys.stderr)
        return 2
    names = {str(item.get("name", "")) for item in tags.get("models", [])}
    if model not in names and not any(name.startswith(f"{model}:") for name in names):
        print(f"Configured model is not installed: {model}", file=sys.stderr)
        return 2
    try:
        model_details = _post_json(f"{base_url}/api/show", {"name": model}).get("details", {})
    except Exception as exc:
        print(f"Could not inspect model metadata for {model}: {exc}", file=sys.stderr)
        return 2

    generator = XtraGPTOllamaGenerator(model, model_file=model_file, base_url=base_url, mode="ateval", max_new_tokens=192)
    engine = SCARRevisionEngine(generator)
    scenarios = [
        ("grammar", "The results shows a clear improvement.", "The results shows a clear improvement. This paragraph reports the experiment.", ()),
        ("clarity", "The method is useful for this task.", "The method is useful for this task. The section describes the evaluation setting.", ()),
        ("structure", "The method uses the data and reports the result.", "The method uses the data and reports the result. This is the complete sentence.", ()),
        ("redundancy", "The method is effective and it is effective in practice.", "The method is effective and it is effective in practice. The section summarizes the finding.", ()),
        ("no_edit", "The estimate is reported in Table 2.", "The estimate is reported in Table 2. This sentence is already specific.", ()),
        ("clarity", r"We follow Smith \cite{smith2024}.", r"We follow Smith \cite{smith2024}. This sentence contains a citation.", (r"\cite{smith2024}",)),
        ("clarity", r"The value is 12\% in Eq.~\ref{eq:one}.", r"The value is 12\% in Eq.~\ref{eq:one}. This sentence contains a number and equation reference.", (r"\ref{eq:one}",)),
        ("technical_review", "The ATEval pipeline uses SCAR.", "The ATEval pipeline uses SCAR. Preserve the method name and claim scope.", ("ATEval", "SCAR")),
    ]
    results = []
    for intention, sentence, context, protected in scenarios:
        started = time.perf_counter()
        try:
            result = engine.revise(
                context,
                target_start=context.index(sentence),
                target_end=context.index(sentence) + len(sentence),
                intention=intention,
                author_requested_edit=intention != "no_edit",
                protected_terms=protected,
                section="synthetic smoke test",
            )
            results.append({
                "intention": intention,
                "review_decision": result.review_decision,
                "candidate_changed": result.candidate_text != sentence,
                "candidate_text": result.candidate_text,
                "structural_validation": result.structural_validation,
                "claim_integrity": result.claim_integrity.to_dict() if result.claim_integrity else None,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "warnings": list(result.warnings),
            })
        except Exception as exc:
            results.append({"intention": intention, "error": str(exc), "elapsed_seconds": round(time.perf_counter() - started, 3)})

    report = {
        "model": model,
        "ollama_version": version,
        "quantization": model_details.get("quantization_level", "not reported by Ollama"),
        "parameter_size": model_details.get("parameter_size", "not reported by Ollama"),
        "runtime": "Ollama loopback REST API",
        "hardware": {"system": platform.platform(), "machine": platform.machine(), "processor": platform.processor()},
        "context_length": generator.context_length,
        "max_new_tokens": generator.max_new_tokens,
        "temperature": 0.1,
        "seed": 17,
        "scenarios": results,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all("error" not in item for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
