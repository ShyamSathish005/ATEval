"""Reproducible adapters for approved AI-text detection corpora.

Each adapter:
- Calculates SHA-256 hashes of input files.
- Preserves verbatim class labels.
- Maps records to standardized benchmark tasks without losing source information.
- Strictly separates document-level labels from passage/span annotations.
- Implements strict validation and error handling.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from .schema import AuthorshipClass, DetectionRecord, SpanAnnotation


def compute_sha256(path: str | Path, buffer_size: int = 65536) -> str:
    """Calculate the hex SHA-256 digest of a file in chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(buffer_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class AdapterLoadResult:
    """Summary of loading and validating an external corpus."""
    records: list[DetectionRecord]
    total_rows_read: int
    valid_count: int
    skipped_count: int
    skipped_reasons: Counter[str]
    sha256_hash: str
    class_distribution: Counter[str]
    model_distribution: Counter[str]


class TXD22Adapter:
    """Adapter for TXD-22 (Mendeley Data DOI: 10.17632/prcjcggtjf.1).
    
    66,000 samples balanced across 22 classes:
    - 1 human class: 'Human'
    - 17 AI models: 'ChatGPT', 'Gemini', 'Claude', 'LLaMA', 'Mistral AI', 'Grok',
      'Copilot', 'Perplexity', 'DeepSeek', 'DeepAI', 'Qwen', 'Gemma', 'Poe',
      'Nova', 'Pi', 'Z.ai', 'BLACKBOXAI'
    - 4 mixed-authorship classes:
      'AI-generated + Human-written',
      'AI-generated + AI-refined',
      'Human-written + AI-refined',
      'AI-generated + AI-refined + Human-written'
    """

    EXPECTED_SHA256 = "232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d"
    EXPECTED_SIZE = 121656267
    EXPECTED_CLASSES = 22

    AI_MODELS = frozenset({
        "chatgpt", "gemini", "claude", "llama", "mistral ai", "grok",
        "copilot", "perplexity", "deepseek", "deepai", "qwen", "gemma",
        "poe", "nova", "pi", "z.ai", "blackboxai"
    })

    MIXED_CLASSES = frozenset({
        "ai-generated + human-written",
        "ai-generated + ai-refined",
        "human-written + ai-refined",
        "ai-generated + ai-refined + human-written"
    })

    @classmethod
    def map_source_label(cls, raw_source: str) -> tuple[str, str | None]:
        """Map raw source string to (benchmark_label, generator_model)."""
        normalized = raw_source.strip().casefold()
        if normalized == "human":
            return AuthorshipClass.HUMAN.value, None
        if normalized in cls.MIXED_CLASSES:
            return AuthorshipClass.MIXED.value, None
        if normalized in cls.AI_MODELS:
            return AuthorshipClass.AI.value, raw_source.strip()
        # Fallback for minor capitalization or whitespace discrepancies
        if "human" in normalized and ("ai" in normalized or "refined" in normalized):
            return AuthorshipClass.MIXED.value, None
        return AuthorshipClass.AI.value, raw_source.strip()

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        verify_sha256: bool = True,
        max_records: int | None = None,
    ) -> AdapterLoadResult:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"TXD-22 corpus file not found: {file_path}")

        file_hash = compute_sha256(file_path)
        if verify_sha256 and file_hash != cls.EXPECTED_SHA256:
            raise ValueError(
                f"SHA-256 hash mismatch for {file_path}. "
                f"Expected {cls.EXPECTED_SHA256}, got {file_hash}"
            )

        records: list[DetectionRecord] = []
        skipped_reasons: Counter[str] = Counter()
        class_dist: Counter[str] = Counter()
        model_dist: Counter[str] = Counter()
        total_rows = 0

        with open(file_path, "r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not {"Question", "Answer", "Source"}.issubset(reader.fieldnames):
                raise ValueError(
                    f"Unexpected CSV headers in {file_path}. Expected Question, Answer, Source. "
                    f"Found: {reader.fieldnames}"
                )

            for index, row in enumerate(reader, start=1):
                total_rows += 1
                question = (row.get("Question") or "").strip()
                answer = (row.get("Answer") or "").strip()
                raw_source = (row.get("Source") or "").strip()

                if not answer:
                    skipped_reasons["empty_answer"] += 1
                    continue
                if not raw_source:
                    skipped_reasons["missing_source"] += 1
                    continue

                label, model = cls.map_source_label(raw_source)
                record_id = f"txd22_{index:06d}"

                rec = DetectionRecord(
                    id=record_id,
                    text=answer,
                    label=label,
                    original_label=raw_source,
                    source_dataset="txd_22",
                    generator_model=model,
                    domain="academic_and_professional",
                    prompt=question if question else None,
                    document_id=f"doc_{hashlib.sha256(question.encode('utf-8')).hexdigest()[:12]}" if question else None,
                    has_span_labels=False,
                    spans=[],
                    metadata={
                        "raw_source": raw_source,
                        "question_length": len(question.split()),
                        "answer_length": len(answer.split()),
                    },
                )
                validation_errors = rec.validate()
                if validation_errors:
                    skipped_reasons[f"validation_error_{validation_errors[0]}"] += 1
                    continue

                records.append(rec)
                class_dist[raw_source] += 1
                if model:
                    model_dist[model] += 1

                if max_records and len(records) >= max_records:
                    break

        return AdapterLoadResult(
            records=records,
            total_rows_read=total_rows,
            valid_count=len(records),
            skipped_count=sum(skipped_reasons.values()),
            skipped_reasons=skipped_reasons,
            sha256_hash=file_hash,
            class_distribution=class_dist,
            model_distribution=model_dist,
        )


class RAIDAdapter:
    """Adapter for RAID benchmark (ACL 2024 / github.com/liamdugan/raid).
    
    Supports filtering to the 'abstracts' academic domain and evaluating
    across diverse generation models, decoding strategies, and adversarial attacks.
    """

    @classmethod
    def load_jsonl_or_csv(
        cls,
        path: str | Path,
        *,
        domain_filter: str | None = "abstracts",
        max_records: int | None = None,
    ) -> AdapterLoadResult:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"RAID corpus file not found: {file_path}")

        file_hash = compute_sha256(file_path)
        records: list[DetectionRecord] = []
        skipped_reasons: Counter[str] = Counter()
        class_dist: Counter[str] = Counter()
        model_dist: Counter[str] = Counter()
        total_rows = 0

        # Detect CSV or JSONL
        is_csv = file_path.suffix.casefold() == ".csv"
        rows: Iterable[dict[str, Any]]
        if is_csv:
            with open(file_path, "r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
        else:
            with open(file_path, "r", encoding="utf-8-sig") as stream:
                rows = [json.loads(line) for line in stream if line.strip()]

        for index, row in enumerate(rows, start=1):
            total_rows += 1
            domain = str(row.get("domain", "")).strip().casefold()
            if domain_filter and domain and domain != domain_filter.casefold():
                skipped_reasons["domain_filtered"] += 1
                continue

            text = str(row.get("generation") or row.get("text") or "").strip()
            if not text:
                skipped_reasons["empty_text"] += 1
                continue

            raw_model = str(row.get("model") or "").strip()
            raw_label = str(row.get("label") or "").strip().casefold()

            if raw_model.casefold() in {"human", "none"} or raw_label in {"human", "0"}:
                label = AuthorshipClass.HUMAN.value
                model = None
                orig_label = "human"
            else:
                label = AuthorshipClass.AI.value
                model = raw_model
                orig_label = raw_model or "ai"

            rec = DetectionRecord(
                id=f"raid_{index:06d}",
                text=text,
                label=label,
                original_label=orig_label,
                source_dataset="raid",
                generator_model=model,
                domain="academic" if domain == "abstracts" else domain or "general",
                document_id=str(row.get("document_id") or row.get("id") or f"raid_doc_{index}"),
                has_span_labels=False,
                spans=[],
                metadata={
                    "attack": row.get("attack"),
                    "decoding": row.get("decoding"),
                    "repetition_penalty": row.get("repetition_penalty"),
                },
            )
            records.append(rec)
            class_dist[orig_label] += 1
            if model:
                model_dist[model] += 1

            if max_records and len(records) >= max_records:
                break

        return AdapterLoadResult(
            records=records,
            total_rows_read=total_rows,
            valid_count=len(records),
            skipped_count=sum(skipped_reasons.values()),
            skipped_reasons=skipped_reasons,
            sha256_hash=file_hash,
            class_distribution=class_dist,
            model_distribution=model_dist,
        )


class M4Adapter:
    """Adapter for M4 corpus (EACL 2024 / github.com/mbzuai-nlp/M4)."""

    @classmethod
    def load_jsonl(
        cls,
        path: str | Path,
        *,
        domain_filter: str | None = "arxiv",
        max_records: int | None = None,
    ) -> AdapterLoadResult:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"M4 corpus file not found: {file_path}")

        file_hash = compute_sha256(file_path)
        records: list[DetectionRecord] = []
        skipped_reasons: Counter[str] = Counter()
        class_dist: Counter[str] = Counter()
        model_dist: Counter[str] = Counter()
        total_rows = 0

        with open(file_path, "r", encoding="utf-8-sig") as stream:
            for index, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                total_rows += 1
                row = json.loads(line)

                domain = str(row.get("domain", "")).strip().casefold()
                if domain_filter and domain and domain != domain_filter.casefold():
                    skipped_reasons["domain_filtered"] += 1
                    continue

                text = str(row.get("text") or "").strip()
                if not text:
                    skipped_reasons["empty_text"] += 1
                    continue

                raw_label = str(row.get("label", "")).strip().casefold()
                raw_model = str(row.get("model", "")).strip()

                if raw_label in {"human", "0"}:
                    label = AuthorshipClass.HUMAN.value
                    model = None
                    orig_label = "human"
                else:
                    label = AuthorshipClass.AI.value
                    model = raw_model or "ai"
                    orig_label = raw_model or "ai"

                rec = DetectionRecord(
                    id=f"m4_{index:06d}",
                    text=text,
                    label=label,
                    original_label=orig_label,
                    source_dataset="m4",
                    generator_model=model,
                    domain="academic" if domain == "arxiv" else domain or "general",
                    document_id=str(row.get("doc_id") or f"m4_doc_{index}"),
                    has_span_labels=False,
                    spans=[],
                    metadata={"prompt": row.get("prompt")},
                )
                records.append(rec)
                class_dist[orig_label] += 1
                if model:
                    model_dist[model] += 1

                if max_records and len(records) >= max_records:
                    break

        return AdapterLoadResult(
            records=records,
            total_rows_read=total_rows,
            valid_count=len(records),
            skipped_count=sum(skipped_reasons.values()),
            skipped_reasons=skipped_reasons,
            sha256_hash=file_hash,
            class_distribution=class_dist,
            model_distribution=model_dist,
        )


class SyntheticDetectionFixture:
    """Generates synthetic, deterministic fixtures for offline unit and CI testing.
    
    Creates controlled samples across Task A (Human vs AI), Task B (Mixed),
    Task C (Academic vs News), and Task D (with genuine SpanAnnotation fixtures).
    """

    @classmethod
    def create_fixture_records(cls) -> list[DetectionRecord]:
        records: list[DetectionRecord] = []

        # Human academic samples
        human_samples = [
            ("The asymptotic convergence rate of stochastic gradient estimators depends fundamentally on step-size decay. Under mild convexity assumptions, uniform boundedness of the gradient variance suffices to guarantee almost-sure convergence toward the unique stationary point.", "q_opt_01", "academic", "mathematics", "What is the asymptotic convergence rate of stochastic gradient estimators?"),
            ("Empirical evaluations across three longitudinal cohorts demonstrate that peer review turnaround time correlates weakly with citation velocity. Manuscript acceptance rates remain invariant to seasonal submission fluctuations across all surveyed subdisciplines.", "q_scientometrics_01", "academic", "scientometrics", "How does peer review turnaround time correlate with citation velocity?"),
            ("A double-blind randomised trial evaluated the efficacy of low-dose antimicrobial prophylaxis in post-operative wound healing. Primary endpoints showed no statistically significant reduction in secondary bacterial colonization compared to placebo controls.", "q_med_01", "academic", "clinical_medicine", "What is the efficacy of antimicrobial prophylaxis in post-operative wound healing?"),
            ("We examine the linguistic evolution of passive voice constructions in early modern English philosophical treatises. Syntactic parsing reveals a gradual decrease in periphrastic passive frequency between 1640 and 1720.", "q_ling_01", "academic", "linguistics", "How did passive voice constructions evolve in early modern English philosophy?"),
            ("The thermal conductivity of two-dimensional transition metal dichalcogenides exhibits pronounced anisotropy along the basal plane. Phonon dispersion measurements corroborate strong anharmonic scattering at room temperature.", "q_phys_01", "academic", "solid_state_physics", "What determines the thermal conductivity of two-dimensional transition metal dichalcogenides?"),
        ]
        for idx, (text, q_id, domain, subdomain, prompt_text) in enumerate(human_samples, start=1):
            records.append(DetectionRecord(
                id=f"syn_human_{idx:03d}",
                text=text,
                label=AuthorshipClass.HUMAN.value,
                original_label="Human",
                source_dataset="synthetic_academic_fixture",
                generator_model=None,
                domain=domain,
                subdomain=subdomain,
                prompt=prompt_text,
                document_id=f"doc_{q_id}",
                author_id=f"author_h{idx}",
                has_span_labels=False,
            ))

        # AI generated samples across models
        ai_samples = [
            ("In conclusion, the convergence rate of stochastic gradient descent is a crucial factor in machine learning optimization. Furthermore, it is important to remember that step size decay plays an essential role in ensuring robust performance across diverse tasks and applications.", "ChatGPT", "chatgpt", "q_opt_01", "academic", "What is the asymptotic convergence rate of stochastic gradient estimators?"),
            ("Moreover, it is worth noting that peer review turnaround time plays a vital role in academic publishing workflows. Consequently, understanding the relationship between review duration and subsequent citation impact remains paramount for institutional evaluation.", "Claude", "claude", "q_scientometrics_01", "academic", "How does peer review turnaround time correlate with citation velocity?"),
            ("Certainly! Clinical trials are essential for modern evidence-based medicine. It is crucial to evaluate antibiotic efficacy with rigorous placebo-controlled protocols to ensure safe and effective patient outcomes in all clinical scenarios.", "Gemini", "gemini", "q_med_01", "academic", "What is the efficacy of antimicrobial prophylaxis in post-operative wound healing?"),
            ("Additionally, passive voice structures are fascinating phenomena in historical linguistics. It is widely recognized that authors frequently adopted passive formulations to cultivate an objective, impersonal scholarly demeanor throughout historical prose.", "LLaMA", "llama", "q_ling_01", "academic", "How did passive voice constructions evolve in early modern English philosophy?"),
            ("In summary, two-dimensional materials possess exceptional thermal transport characteristics. Furthermore, phonon scattering mechanisms represent an intriguing area of investigation for advancing next-generation nanoscale thermal dissipation architectures.", "Mistral AI", "mistral ai", "q_phys_01", "academic", "What determines the thermal conductivity of two-dimensional transition metal dichalcogenides?"),
        ]
        for idx, (text, orig_lbl, model, q_id, domain, prompt_text) in enumerate(ai_samples, start=1):
            records.append(DetectionRecord(
                id=f"syn_ai_{idx:03d}",
                text=text,
                label=AuthorshipClass.AI.value,
                original_label=orig_lbl,
                source_dataset="synthetic_academic_fixture",
                generator_model=model,
                domain=domain,
                subdomain="computer_science",
                prompt=prompt_text,
                document_id=f"doc_{q_id}",
                author_id=None,
                has_span_labels=False,
            ))

        # Mixed-authorship samples (Task B)
        mixed_samples = [
            ("The asymptotic convergence rate of stochastic gradient estimators depends fundamentally on step-size decay. Furthermore, it is important to remember that step size decay plays an essential role in ensuring robust performance across diverse tasks and applications.", "AI-generated + Human-written", "q_opt_01", "What is the asymptotic convergence rate of stochastic gradient estimators?"),
            ("A double-blind randomised trial evaluated the efficacy of low-dose antimicrobial prophylaxis in post-operative wound healing. Certainly, clinical trials are essential for modern evidence-based medicine and patient safety.", "Human-written + AI-refined", "q_med_01", "What is the efficacy of antimicrobial prophylaxis in post-operative wound healing?"),
        ]
        for idx, (text, orig_lbl, q_id, prompt_text) in enumerate(mixed_samples, start=1):
            records.append(DetectionRecord(
                id=f"syn_mixed_{idx:03d}",
                text=text,
                label=AuthorshipClass.MIXED.value,
                original_label=orig_lbl,
                source_dataset="synthetic_academic_fixture",
                generator_model=None,
                domain="academic",
                subdomain="hybrid",
                prompt=prompt_text,
                document_id=f"doc_{q_id}",
                author_id=f"author_hybrid_{idx}",
                has_span_labels=False,
            ))

        # Passage-level localisation samples with genuine span annotations (Task D)
        passage_text = "The asymptotic convergence rate depends on step size decay. Furthermore, it is important to remember that step size decay plays an essential role in ensuring robust performance."
        # sentence 1 is human (0-58), sentence 2 is AI (59-173)
        span_human = SpanAnnotation(start_char=0, end_char=58, label="human", source="verified_ground_truth")
        span_ai = SpanAnnotation(start_char=59, end_char=len(passage_text), label="ai", source="verified_ground_truth")

        records.append(DetectionRecord(
            id="syn_passage_001",
            text=passage_text,
            label=AuthorshipClass.MIXED.value,
            original_label="hybrid_with_spans",
            source_dataset="synthetic_academic_fixture",
            generator_model="chatgpt",
            domain="academic",
            subdomain="mathematics",
            prompt="Hybrid with span truth",
            document_id="doc_span_01",
            has_span_labels=True,
            spans=[span_human, span_ai],
        ))

        return records
