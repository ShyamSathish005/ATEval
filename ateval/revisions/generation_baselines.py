"""Reviewable identity and rule-editor generation comparisons."""

from __future__ import annotations

import json
import re
import statistics
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .schema import RevisionRecord
from ..writing.editing import apply_accepted_suggestions, suggestions_for_text
from ..writing.latex import protected_spans
from ..writing.semantic import validate_preservation

WORD = re.compile(r"\w+(?:[’'-]\w+)*|[^\w\s]", re.UNICODE)
NUMBER = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?(?:\s*(?:×|\*|±|\+/-|%|‰|°|mm|cm|m|km|µm|nm|kg|mg|g|ml|mL|L|s|ms|min|h|Hz|kHz|MHz|GHz|Pa|kPa|MPa|GPa|V|mV|W|kW|J|kJ|eV|K|°C|°F|mol|mmol|M|mM|µM|nM|dB|dpi|fps|ppm|ppb))?(?!\w)")
CITATION = re.compile(r"\\(?:cite[a-zA-Z*]*|parencite|textcite|autocite|ref|eqref)\s*(?:\[[^\]]*\]\s*)*\{[^}]*\}|\[(?:\d+(?:\s*[,;–-]\s*\d+)*)\]|\[(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\](?:;\s*\[(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\])*|\((?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\)(?:;\s*(?:[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.)?),\s*(?:19|20)\d{2}[a-z]?\))*")


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in WORD.finditer(text)]


def _ngram_counts(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    return Counter(tuple(tokens[i:i + n]) for i in range(max(0, len(tokens) - n + 1)))


def _corpus_bleu(sources: list[str], outputs: list[str], references: list[str], max_n: int = 4) -> float:
    clipped, totals = [0] * max_n, [0] * max_n
    out_len = ref_len = 0
    for output, reference in zip(outputs, references):
        hyp, ref = _tokens(output), _tokens(reference)
        out_len += len(hyp)
        ref_len += len(ref)
        for n in range(1, max_n + 1):
            h, r = _ngram_counts(hyp, n), _ngram_counts(ref, n)
            clipped[n - 1] += sum(min(count, r[gram]) for gram, count in h.items())
            totals[n - 1] += sum(h.values())
    if not out_len or not ref_len:
        return 0.0
    # Add-one smoothing for corpus-level single-reference BLEU; disclose this
    # so short academic sentences are not all forced to a zero score.
    precisions = [(clipped[i] + 1) / (totals[i] + 1) for i in range(max_n)]
    brevity = min(1.0, __import__("math").exp(1 - ref_len / out_len))
    return brevity * __import__("math").exp(sum(__import__("math").log(value) for value in precisions) / max_n)


def _rouge_l(output: str, reference: str) -> float:
    left, right = _tokens(output), _tokens(reference)
    if not left or not right:
        return 1.0 if left == right else 0.0
    # Dynamic-programming LCS using O(min(n,m)) space.
    if len(right) > len(left):
        left, right = right, left
    previous = [0] * (len(right) + 1)
    for token in left:
        current = [0]
        for j, other in enumerate(right, 1):
            current.append(previous[j - 1] + 1 if token == other else max(previous[j], current[-1]))
        previous = current
    lcs = previous[-1]
    precision, recall = lcs / len(left), lcs / len(right)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _edit_operations(source: str, target: str) -> Counter[str]:
    src, tgt = _tokens(source), _tokens(target)
    result: Counter[str] = Counter()
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=src, b=tgt, autojunk=False).get_opcodes():
        if tag in {"delete", "replace"}:
            result.update(f"D:{token}" for token in src[i1:i2])
        if tag in {"insert", "replace"}:
            result.update(f"A:{token}" for token in tgt[j1:j2])
    return result


def _sari_single_reference(source: str, output: str, reference: str, max_n: int = 4) -> float:
    """Single-reference SARI diagnostic; this mixed-intention task is not simplification."""
    src, out, ref = _tokens(source), _tokens(output), _tokens(reference)
    scores: list[float] = []
    for n in range(1, max_n + 1):
        source_ngrams = set(tuple(src[i:i + n]) for i in range(max(0, len(src) - n + 1)))
        output_ngrams = set(tuple(out[i:i + n]) for i in range(max(0, len(out) - n + 1)))
        reference_ngrams = set(tuple(ref[i:i + n]) for i in range(max(0, len(ref) - n + 1)))
        predicted_keep = source_ngrams & output_ngrams
        target_keep = source_ngrams & reference_ngrams
        good_keep = predicted_keep & target_keep
        keep_precision = len(good_keep) / len(predicted_keep) if predicted_keep else (1.0 if not target_keep else 0.0)
        keep_recall = len(good_keep) / len(target_keep) if target_keep else (1.0 if not predicted_keep else 0.0)
        keep_f1 = 2 * keep_precision * keep_recall / (keep_precision + keep_recall) if keep_precision + keep_recall else 0.0

        predicted_add = output_ngrams - source_ngrams
        target_add = reference_ngrams - source_ngrams
        good_add = predicted_add & target_add
        add_precision = len(good_add) / len(predicted_add) if predicted_add else (1.0 if not target_add else 0.0)
        add_recall = len(good_add) / len(target_add) if target_add else (1.0 if not predicted_add else 0.0)
        add_f1 = 2 * add_precision * add_recall / (add_precision + add_recall) if add_precision + add_recall else 0.0

        predicted_delete = source_ngrams - output_ngrams
        target_delete = source_ngrams - reference_ngrams
        good_delete = predicted_delete & target_delete
        delete_precision = len(good_delete) / len(predicted_delete) if predicted_delete else (1.0 if not target_delete else 0.0)
        scores.append((keep_f1 + add_f1 + delete_precision) / 3)
    return sum(scores) / len(scores)


def _micro_edit_prf(records: list[RevisionRecord], outputs: list[str]) -> dict[str, Any]:
    true_positive = predicted_total = reference_total = 0
    for record, output in zip(records, outputs):
        predicted, reference = _edit_operations(record.original_text, output), _edit_operations(record.original_text, record.revised_text)
        true_positive += sum((predicted & reference).values())
        predicted_total += sum(predicted.values())
        reference_total += sum(reference.values())
    precision = true_positive / predicted_total if predicted_total else (1.0 if not reference_total else 0.0)
    recall = true_positive / reference_total if reference_total else (1.0 if not predicted_total else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "unit": "micro token insertion/deletion operations, multiset counted"}


def _structural_integrity(records: list[RevisionRecord], outputs: list[str]) -> dict[str, Any]:
    number_ok = citation_ok = protected_ok = 0
    for record, output in zip(records, outputs):
        number_ok += [match.group(0) for match in NUMBER.finditer(record.original_text)] == [match.group(0) for match in NUMBER.finditer(output)]
        citation_ok += [match.group(0) for match in CITATION.finditer(record.original_text)] == [match.group(0) for match in CITATION.finditer(output)]
        protected_ok += bool(validate_preservation(record.original_text, output)["protected_span_sequence_preserved"])
    denominator = len(records) or 1
    return {"numeric_sequence_preservation_rate": number_ok / denominator, "citation_sequence_preservation_rate": citation_ok / denominator, "protected_sequence_preservation_rate": protected_ok / denominator, "n": len(records), "semantic_equivalence": "not_assessed"}


def _system_metrics(records: list[RevisionRecord], outputs: list[str]) -> dict[str, Any]:
    references = [record.revised_text for record in records]
    no_op = [i for i, record in enumerate(records) if _normalize(record.original_text) == _normalize(record.revised_text)]
    unnecessary = sum(_normalize(outputs[i]) != _normalize(records[i].original_text) for i in no_op)
    edit_distances = [sum(count for key, count in _edit_operations(record.original_text, output).items()) for record, output in zip(records, outputs)]
    return {
        "examples": len(records),
        "corpus_bleu_1_to_4_add_one_smoothed": _corpus_bleu([r.original_text for r in records], outputs, references),
        "mean_rouge_l_f1_single_reference": sum(_rouge_l(hyp, ref) for hyp, ref in zip(outputs, references)) / len(records) if records else None,
        "sari_single_reference_macro_1_to_4": sum(_sari_single_reference(record.original_text, output, record.revised_text) for record, output in zip(records, outputs)) / len(records) if records else None,
        "sari_interpretation": "diagnostic only: SARI was designed for text simplification; these IteraTeR labels mix edit intentions",
        "bertscore": {"status": "not_run", "reason": "No local BERTScore model checkpoint was preinstalled; this run does not fetch another model."},
        "token_edit_distance": {
            "mean": sum(edit_distances) / len(edit_distances) if edit_distances else None,
            "median": statistics.median(edit_distances) if edit_distances else None,
            "unit": "inserted plus deleted/replaced token operations from SequenceMatcher",
        },
        "edit_operation_micro": _micro_edit_prf(records, outputs),
        "preservation": _structural_integrity(records, outputs),
        "changed_output_rate": sum(_normalize(output) != _normalize(record.original_text) for record, output in zip(records, outputs)) / len(records) if records else None,
        "unnecessary_edit_rate_on_noop_references": unnecessary / len(no_op) if no_op else None,
        "no_op_reference_count": len(no_op),
    }


def compare_generation_baselines(records: list[RevisionRecord], *, output_path: str | Path | None = None) -> dict[str, Any]:
    """Compare identity and current rules on the same held-out human references."""
    sources = [record.original_text for record in records]
    identity = list(sources)
    rule_outputs = []
    for source in sources:
        suggestions = suggestions_for_text(source, protected_spans(source))
        result, _ = apply_accepted_suggestions(source, suggestions, {item["id"] for item in suggestions})
        rule_outputs.append(result)
    report = {
        "schema": "ateval-generation-baselines-v1",
        "dataset": "IteraTeR-HUMAN grouped test",
        "test_document_count": len({record.source_document_id for record in records}),
        "systems": {"identity_no_edit": _system_metrics(records, identity), "ateval_phrase_rules_autoaccepted_for_benchmark_only": _system_metrics(records, rule_outputs)},
        "metrics_note": "Single-reference BLEU/ROUGE are overlap diagnostics, not quality judgments. SARI is omitted because the held-out set mixes fluency, cohesion, style, meaning-change, and clarity rather than being a text-simplification benchmark.",
        "human_evaluation": "not conducted",
        "semantic_equivalence": "not assessed; protected spans and change operations do not prove meaning preservation",
    }
    if output_path is not None:
        target = Path(output_path)
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite generation report: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def compare_generation_systems(
    records: list[RevisionRecord],
    generated: dict[str, list[str]],
    *,
    model_metadata: dict[str, Any],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Score model outputs beside identity and rule baselines on same rows.

    This reports lexical overlap and structural checks only. It intentionally
    does not turn these diagnostics into a writing-quality or semantic score.
    """
    if not records:
        raise ValueError("generation comparison requires held-out records")
    if not generated:
        raise ValueError("at least one generated system is required")
    expected = len(records)
    for name, outputs in generated.items():
        if len(outputs) != expected:
            raise ValueError(f"system {name!r} returned {len(outputs)} outputs for {expected} records")
        if any(not isinstance(item, str) or not item.strip() for item in outputs):
            raise ValueError(f"system {name!r} returned an empty or invalid output")

    sources = [record.original_text for record in records]
    rule_outputs = []
    for source in sources:
        suggestions = suggestions_for_text(source, protected_spans(source))
        result, _ = apply_accepted_suggestions(source, suggestions, {item["id"] for item in suggestions})
        rule_outputs.append(result)
    systems = {
        "identity_no_edit": _system_metrics(records, sources),
        "ateval_phrase_rules_autoaccepted_for_benchmark_only": _system_metrics(records, rule_outputs),
    }
    systems.update({name: _system_metrics(records, outputs) for name, outputs in generated.items()})
    report = {
        "schema": "ateval-generation-systems-v1",
        "dataset": "IteraTeR-HUMAN document-grouped test",
        "test_document_count": len({record.source_document_id for record in records}),
        "model_metadata": model_metadata,
        "systems": systems,
        "metrics_note": "BLEU, ROUGE-L, and token edit-operation overlap are diagnostics, not writing-quality scores. Exact structural preservation is not semantic equivalence.",
        "human_evaluation": "not conducted",
        "semantic_equivalence": "not assessed; every model output requires author review",
    }
    if output_path is not None:
        target = Path(output_path)
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite generation report: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
