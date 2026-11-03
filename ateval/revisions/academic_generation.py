"""Local academic revision generation with explicit human-review metadata.

This module has no model dependency at import time. XtraGPT weights are loaded
only from a caller-provided local checkpoint path; it never downloads a model
or changes the source manuscript.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from ..writing.semantic import validate_preservation


@dataclass(frozen=True)
class AcademicRevisionRequest:
    original_text: str
    paragraph_context: str = ""
    previous_sentence: str = ""
    next_sentence: str = ""
    document_section: str = "unknown"
    editing_instruction: str = "Improve academic clarity conservatively."
    iterater_intent: str = "clarity"
    protected_terminology: tuple[str, ...] = ()
    relevant_citations: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.original_text.strip():
            raise ValueError("original_text must not be empty")
        if not self.editing_instruction.strip():
            raise ValueError("editing_instruction must not be empty")
        if len(self.original_text) > 20_000:
            raise ValueError("original_text exceeds the 20,000-character request limit")
        if len(self.paragraph_context) > 80_000:
            raise ValueError("paragraph_context exceeds the 80,000-character request limit")


@dataclass(frozen=True)
class AcademicRevisionProposal:
    original_text: str
    proposed_text: str
    rationale: str
    expected_benefit: str
    potential_technical_risk: str
    preservation: dict[str, Any]
    warnings: tuple[str, ...] = ()
    provider: str = "unknown"
    checkpoint: str | None = None
    status: str = "review_required"
    author_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TextGenerator(Protocol):
    provider: str

    def generate(self, request: AcademicRevisionRequest) -> AcademicRevisionProposal: ...


_PROMPT = """Act as a careful academic paper revision assistant. Improve only the selected passage according to the question. Avoid adding length, unsupported claims, unrelated details, or generic filler. Use the context only to resolve meaning and terminology.

Preserve scientific claims, scope, negation, causal relationships, qualifications, limitations, numbers, units, equations, LaTeX, citations, references, and protected terminology exactly. Do not invent evidence or citations. If no safe, useful edit is justified, return the original passage unchanged. The result is a proposal for author review, not an assertion of semantic equivalence.

Return exactly one JSON object with string fields: revision, rationale, expected_benefit, potential_technical_risk. No markdown fences.

<PAPER_CONTENT>
{paper_content}
</PAPER_CONTENT>
<SELECTED_CONTENT>
{selected_content}
</SELECTED_CONTENT>
<QUESTION>
{user_question}
Protected terminology (preserve exactly): {protected_terms}
Relevant citations (preserve exactly): {citations}
Document section: {section}
</QUESTION>"""

_GENERAL_PROMPT = """You are an academic writing editor. Revise only the selected passage according to the user's instruction. Use the supplied section and context to preserve the argument and technical meaning. Do not add evidence, citations, claims, or generic filler. Preserve numbers, units, symbols, equations, LaTeX, citations, references, and the protected terms listed below exactly. If no safe useful edit is justified, return the original passage unchanged.

Return one JSON object with string fields revision, rationale, expected_benefit, potential_technical_risk. Do not use markdown fences.

Section: {section}
Paragraph and adjacent context:
{context}

Protected terms: {protected_terms}
Relevant citations: {citations}
Instruction: {instruction}

Selected passage:
{selected_content}
"""


def build_xtragpt_prompt(request: AcademicRevisionRequest, *, mode: str = "ateval") -> str:
    """Use XtraGPT's published XML-like input fields with bounded context."""
    request.validate()
    surrounding = "\n".join(
        value.strip()
        for value in (request.previous_sentence, request.paragraph_context, request.next_sentence)
        if value and value.strip()
    )
    paper_content = f"Section: {request.document_section}\n{surrounding}" if surrounding else f"Section: {request.document_section}\n{request.original_text}"
    terms = "; ".join(request.protected_terminology) or "none supplied"
    citations = "; ".join(request.relevant_citations) or "preserve any citation in the selected content"
    question = request.editing_instruction.strip()
    if mode == "published":
        # XtraGPT's repository prompt structure and concise, evidence-grounded instruction.
        return (
            "Act as an expert model for improving articles. The output needs to answer the QUESTION on SELECTED_CONTENT. "
            "Avoid unnecessary length, unrelated details, overclaims, or vague statements. Focus on clear, concise, evidence-based "
            "improvements aligned with the paper context.\n<PAPER_CONTENT>\n"
            + paper_content
            + "\n</PAPER_CONTENT>\n<SELECTED_CONTENT>\n"
            + request.original_text
            + "\n</SELECTED_CONTENT>\n<QUESTION>\n"
            + question
            + "\n</QUESTION>"
        )
    if mode != "ateval":
        raise ValueError("mode must be 'published' or 'ateval'")
    return _PROMPT.format(
        paper_content=paper_content,
        selected_content=request.original_text,
        user_question=question,
        protected_terms=terms,
        citations=citations,
        section=request.document_section,
    )


def _normal(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def checkpoint_manifest(model_path: str | Path) -> dict[str, Any]:
    """Hash local checkpoint assets for benchmark provenance."""
    root = Path(model_path).expanduser().resolve()
    files = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = str(path.relative_to(root))
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        files[relative] = {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}
    tree = hashlib.sha256()
    for name, metadata in files.items():
        tree.update(f"{name}\0{metadata['sha256']}\n".encode("utf-8"))
    return {"files": files, "tree_sha256": tree.hexdigest()}


def runtime_metadata() -> dict[str, str]:
    result = {"python": __import__("platform").python_version(), "platform": __import__("platform").platform()}
    for module_name in ("torch", "transformers"):
        module = __import__(module_name)
        result[module_name] = str(getattr(module, "__version__", "unknown"))
    torch = __import__("torch")
    result["cuda_available"] = str(bool(torch.cuda.is_available()))
    result["mps_available"] = str(bool(getattr(getattr(torch, "backends", None), "mps", None) and torch.backends.mps.is_available()))
    try:
        result["physical_memory_bytes"] = str(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        result["physical_memory_bytes"] = "unknown"
    return result


def _parse_response(raw: str) -> tuple[str, str, str, str, list[str]]:
    warnings: list[str] = []
    decoded = raw.strip()
    if decoded.startswith("```"):
        decoded = re.sub(r"^```(?:json)?\s*|\s*```$", "", decoded, flags=re.I | re.S).strip()
    try:
        payload = json.loads(decoded)
        if not isinstance(payload, dict):
            raise ValueError("response JSON is not an object")
        revision = str(payload.get("revision", "")).strip()
        if not revision:
            raise ValueError("response JSON has no revision text")
        return (
            revision,
            str(payload.get("rationale", "")).strip(),
            str(payload.get("expected_benefit", "")).strip(),
            str(payload.get("potential_technical_risk", "")).strip(),
            warnings,
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        warnings.append("The model did not return the requested JSON schema; the raw response is shown for manual review.")
        return decoded, "", "", "Unstructured model response; technical risk has not been assessed.", warnings


def _make_proposal(
    request: AcademicRevisionRequest,
    raw: str,
    *,
    provider: str,
    checkpoint: str | None,
) -> AcademicRevisionProposal:
    proposed, rationale, benefit, risk, warnings = _parse_response(raw)
    preservation = validate_preservation(request.original_text, proposed)
    for term in request.protected_terminology:
        if term and term not in proposed:
            preservation = {**preservation, "protected_terminology_preserved": False}
            warnings.append(f"Protected term not found exactly in proposal: {term}")
    for citation in request.relevant_citations:
        if citation and citation not in proposed:
            preservation = {**preservation, "relevant_citations_preserved": False}
            warnings.append(f"Relevant citation not found exactly in proposal: {citation}")
    if preservation["protected_span_sequence_preserved"] is False:
        warnings.append("A protected structural span changed; do not accept without checking the source and proposal.")
    preservation["semantic_equivalence"] = "not_assessed"
    preservation["requires_author_review"] = True
    status = "no_change" if _normal(proposed) == _normal(request.original_text) else "review_required"
    return AcademicRevisionProposal(
        original_text=request.original_text,
        proposed_text=proposed,
        rationale=rationale,
        expected_benefit=benefit,
        potential_technical_risk=risk,
        preservation=preservation,
        warnings=tuple(warnings),
        provider=provider,
        checkpoint=checkpoint,
        status=status,
    )


class XtraGPTLocalGenerator:
    """XtraGPT Transformers adapter; loads only a local checkpoint directory."""

    provider = "xtragpt-local-transformers"

    def __init__(
        self,
        model_path: str | Path,
        *,
        mode: str = "ateval",
        max_new_tokens: int = 512,
        max_input_tokens: int = 8192,
        dtype: str = "float16",
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Local model directory not found: {self.model_path}")
        if max_new_tokens < 1 or max_new_tokens > 2048:
            raise ValueError("max_new_tokens must be between 1 and 2048")
        if max_input_tokens < 256 or max_input_tokens > 16384:
            raise ValueError("max_input_tokens must be between 256 and 16384")
        if dtype not in {"float16", "bfloat16", "float32"}:
            raise ValueError("dtype must be float16, bfloat16, or float32")
        self.mode = mode
        self.max_new_tokens = max_new_tokens
        self.max_input_tokens = max_input_tokens
        self.dtype = dtype
        self._tokenizer = None
        self._model = None
        self._torch = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Install the optional revision-transformer dependencies to run local generation") from exc
        dtype = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}[self.dtype]
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path), local_files_only=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            str(self.model_path), local_files_only=True, torch_dtype=dtype, use_safetensors=True,
        )
        self._model.eval()
        self._torch = torch

    def generate(self, request: AcademicRevisionRequest) -> AcademicRevisionProposal:
        request.validate()
        self._load()
        tokenizer, model, torch = self._tokenizer, self._model, self._torch
        prompt = build_xtragpt_prompt(request, mode=self.mode)
        messages = [{"role": "user", "content": prompt}]
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt",
        )
        if encoded["input_ids"].shape[-1] > self.max_input_tokens:
            raise ValueError(
                f"Prompt is {encoded['input_ids'].shape[-1]} tokens, above {self.max_input_tokens}; "
                "shorten/select context explicitly rather than silently truncating claims."
            )
        device = next(model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.inference_mode():
            outputs = model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                num_beams=1,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = outputs[0, encoded["input_ids"].shape[-1]:]
        raw = tokenizer.decode(generated, skip_special_tokens=True).strip()
        checkpoint = str(self.model_path)
        return _make_proposal(request, raw, provider=self.provider, checkpoint=checkpoint)

    def checkpoint_manifest(self) -> dict[str, Any]:
        """Hash local checkpoint assets for benchmark provenance."""
        return checkpoint_manifest(self.model_path)

    def runtime_metadata(self) -> dict[str, str]:
        return runtime_metadata()


class GeneralInstructionGenerator(XtraGPTLocalGenerator):
    """Local general instruction-following causal model comparator."""

    provider = "general-instruction-local-transformers"

    def generate(self, request: AcademicRevisionRequest) -> AcademicRevisionProposal:
        request.validate()
        self._load()
        tokenizer, model, torch = self._tokenizer, self._model, self._torch
        context = "\n".join(
            value.strip()
            for value in (request.previous_sentence, request.paragraph_context, request.next_sentence)
            if value and value.strip()
        )
        prompt = _GENERAL_PROMPT.format(
            section=request.document_section,
            context=context or "No additional context supplied.",
            protected_terms="; ".join(request.protected_terminology) or "none",
            citations="; ".join(request.relevant_citations) or "preserve any citation in the selected passage",
            instruction=request.editing_instruction,
            selected_content=request.original_text,
        )
        encoded = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt",
        )
        if encoded["input_ids"].shape[-1] > self.max_input_tokens:
            raise ValueError(
                f"Prompt is {encoded['input_ids'].shape[-1]} tokens, above {self.max_input_tokens}; "
                "shorten/select context explicitly rather than silently truncating claims."
            )
        device = next(model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.inference_mode():
            outputs = model.generate(
                **encoded, max_new_tokens=self.max_new_tokens, do_sample=False,
                num_beams=1, pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(outputs[0, encoded["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
        return _make_proposal(request, raw, provider=self.provider, checkpoint=str(self.model_path))


class IteraTeRSeq2SeqGenerator:
    """Official sentence-only IteraTeR BART/PEGASUS inference protocol."""

    provider = "iterater-seq2seq-local-transformers"

    def __init__(self, model_path: str | Path, *, model_name: str) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Local model directory not found: {self.model_path}")
        if model_name not in {"iterater_bart", "iterater_pegasus"}:
            raise ValueError("model_name must be iterater_bart or iterater_pegasus")
        self.model_name = model_name
        self._tokenizer = None
        self._model = None
        self._torch = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Install the optional revision-transformer dependencies to run local generation") from exc
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path), local_files_only=True)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(
            str(self.model_path), local_files_only=True, use_safetensors=True,
        )
        self._model.eval()
        self._torch = torch

    def generate(self, request: AcademicRevisionRequest) -> AcademicRevisionProposal:
        request.validate()
        self._load()
        tokenizer, model, torch = self._tokenizer, self._model, self._torch
        # Published cards use an intent tag followed by the original sentence.
        encoded = tokenizer(f"<{request.iterater_intent}> {request.original_text}", return_tensors="pt")
        if encoded["input_ids"].shape[-1] > 1024:
            raise ValueError("IteraTeR input exceeds the published 1,024-token generation limit")
        device = next(model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.inference_mode():
            outputs = model.generate(**encoded, num_beams=8, max_length=1024)
        raw = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip()
        return _make_proposal(
            request,
            json.dumps({
                "revision": raw,
                "rationale": f"Conditioned on the published IteraTeR {request.iterater_intent} intent token.",
                "expected_benefit": request.editing_instruction,
                "potential_technical_risk": "Sentence-only model; surrounding paragraph context is not consumed by this official baseline.",
            }),
            provider=self.provider,
            checkpoint=f"{self.model_name}:{self.model_path}",
        )


class XtraGPTOllamaGenerator:
    """Official XtraGPT GGUF through a local Ollama server.

    The API remains loopback-only, uses Ollama's GGUF-embedded chat template,
    and sends only the published XtraGPT field structure as the user message.
    """

    provider = "xtragpt-local-ollama-gguf"

    def __init__(
        self,
        model_name: str,
        *,
        model_file: str | Path,
        base_url: str = "http://127.0.0.1:11434",
        mode: str = "published",
        max_new_tokens: int = 192,
        context_length: int = 2048,
        timeout_seconds: int = 600,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty")
        if max_new_tokens < 1 or max_new_tokens > 2048:
            raise ValueError("max_new_tokens must be between 1 and 2048")
        if context_length < 512 or context_length > 16384:
            raise ValueError("context_length must be between 512 and 16384")
        if mode not in {"published", "ateval"}:
            raise ValueError("mode must be 'published' or 'ateval'")
        parsed_url = urlsplit(base_url)
        if (
            parsed_url.scheme != "http"
            or parsed_url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
            or parsed_url.path not in {"", "/"}
        ):
            raise ValueError("the Ollama base URL must use loopback; remote inference is disabled")
        self.model_name = model_name
        self.model_file = Path(model_file).expanduser().resolve()
        self.base_url = base_url.rstrip("/")
        self.mode = mode
        self.max_new_tokens = max_new_tokens
        self.context_length = context_length
        self.timeout_seconds = timeout_seconds
        self.telemetry: list[dict[str, Any]] = []

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Local Ollama request failed: {exc}") from exc

    def generate_raw(self, request: AcademicRevisionRequest) -> str:
        request.validate()
        prompt = build_xtragpt_prompt(request, mode=self.mode)
        start = time.perf_counter()
        result = self._post("/api/chat", {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "num_ctx": self.context_length,
                "num_predict": self.max_new_tokens,
                "temperature": 0.1,
                "seed": 17,
            },
        })
        elapsed = time.perf_counter() - start
        raw = str(result.get("message", {}).get("content", "")).strip()
        if not raw:
            raise RuntimeError("Local Ollama returned an empty XtraGPT response")
        self.telemetry.append({
            "elapsed_seconds": elapsed,
            "load_duration_ns": result.get("load_duration"),
            "prompt_eval_count": result.get("prompt_eval_count"),
            "prompt_eval_duration_ns": result.get("prompt_eval_duration"),
            "eval_count": result.get("eval_count"),
            "eval_duration_ns": result.get("eval_duration"),
            "total_duration_ns": result.get("total_duration"),
            "done_reason": result.get("done_reason"),
        })
        return raw

    def generate(self, request: AcademicRevisionRequest) -> AcademicRevisionProposal:
        raw = self.generate_raw(request)
        if self.mode == "published":
            # XtraGPT's published contract returns free-form revised text, not
            # ATEval's earlier JSON object. Treating it as malformed JSON was
            # an evaluator/parser error, not a generation failure.
            return AcademicRevisionProposal(
                original_text=request.original_text,
                proposed_text=raw,
                rationale="Free-form output under the published XtraGPT prompt.",
                expected_benefit=request.editing_instruction,
                potential_technical_risk="Meaning, evidence, and technical accuracy remain unverified; author review is required.",
                preservation=validate_preservation(request.original_text, raw),
                warnings=(),
                provider=self.provider,
                checkpoint=f"{self.model_name} ({self.model_file})",
            )
        return _make_proposal(
            request,
            raw,
            provider=self.provider,
            checkpoint=f"{self.model_name} ({self.model_file})",
        )

    def checkpoint_manifest(self) -> dict[str, Any]:
        if not self.model_file.is_file():
            return {"model_file": str(self.model_file), "available": False}
        digest = hashlib.sha256()
        with self.model_file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return {
            "model_file": str(self.model_file),
            "size_bytes": self.model_file.stat().st_size,
            "sha256": digest.hexdigest(),
            "available": True,
        }

    def runtime_metadata(self) -> dict[str, Any]:
        try:
            request = urllib.request.Request(f"{self.base_url}/api/version")
            with urllib.request.urlopen(request, timeout=5) as response:
                version = json.loads(response.read().decode("utf-8")).get("version")
        except (OSError, ValueError):
            version = None
        try:
            request = urllib.request.Request(f"{self.base_url}/api/ps")
            with urllib.request.urlopen(request, timeout=5) as response:
                running = json.loads(response.read().decode("utf-8")).get("models", [])
            model_runtime = next((item for item in running if item.get("name", "").startswith(self.model_name)), {})
        except (OSError, ValueError):
            model_runtime = {}
        return {
            "runtime": "Ollama local REST API",
            "ollama_version": version,
            "python": __import__("platform").python_version(),
            "platform": __import__("platform").platform(),
            "base_url": self.base_url,
            "context_length": self.context_length,
            "device_mode": "Ollama automatic CPU/Metal placement; see machine feasibility report",
            "loaded_model_size_bytes": model_runtime.get("size"),
            "metal_allocated_bytes": model_runtime.get("size_vram"),
        }


def proposal_for_record(record: Any, generator: TextGenerator) -> AcademicRevisionProposal:
    """Adapt an IteraTeR record to the generation request contract."""
    labels = tuple(getattr(record, "canonical_labels", ()) or ())
    intent = labels[0] if labels else "academic clarity"
    instructions = {
        "grammar_correction": "Correct grammar and fluency while preserving the author's meaning.",
        "clarity_improvement": "Improve clarity without adding claims or changing scope.",
        "cohesion_improvement": "Improve local cohesion and transitions while preserving the argument.",
        "author_style": "Make a conservative academic style edit while retaining the author's voice.",
        "meaning_changed": "Review the passage conservatively; do not change scientific meaning. If a meaning-changing edit would be required, abstain and return the original.",
        "other": "Make a conservative academic edit only if a clear, safe improvement is evident; otherwise return the original.",
    }
    intent_tags = {
        "grammar_correction": "fluency",
        "clarity_improvement": "clarity",
        "cohesion_improvement": "coherence",
        "author_style": "style",
        "meaning_changed": "meaning-changed",
        "other": "others",
    }
    request = AcademicRevisionRequest(
        original_text=record.original_text,
        previous_sentence=record.context_before,
        next_sentence=record.context_after,
        document_section=str(record.section_type or "unknown"),
        editing_instruction=instructions.get(intent, f"Review this passage for {intent}; preserve all scientific meaning."),
        iterater_intent=intent_tags.get(intent, "clarity"),
        relevant_citations=tuple(re.findall(r"\\(?:cite[a-zA-Z*]*|ref|eqref)\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}|\[[^\]]+\]|\([A-Z][^)]*\b(?:19|20)\d{2}[a-z]?\)", record.original_text)),
    )
    return generator.generate(request)
