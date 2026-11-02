# Milestone 4.2 experiment report

## Scope and reproducibility

This report separates the completed immutable M4.1 full-passage baseline from the M4.2 SCAR prototype. No M4.1 prediction was edited. Original predictions: `reports/milestone4_1/xtragpt_1_5b_q8_0_predictions.jsonl` (588 rows; SHA-256 `5c7da1abaed3723d79cf89925e4c14c4e56857c0f4fcf08348279e31fa6d1535`). The original benchmark is `reports/milestone4_1/xtragpt_1_5b_q8_0_benchmark.json`; refined failure analysis is `reports/milestone4_1/m4_1_failure_analysis_refined.json`.

The first SCAR implementation is deterministic up to the local generator call. Its decision and validation behavior is covered by tests. Human ratings are not claimed. The original M4.1 test set was not used for prompt tuning.

## M4.1 reference findings

- Full-passage XtraGPT revised 587/588 (99.83%) including every one of four no-op references (100% unnecessary edits on the no-op subset).
- 140/588 outputs had a protected numeric-sequence failure under the refined validator (23.81%). This includes introduced, dropped, reordered, or altered number/unit/statistic content.
- Refined citation analysis found one unsupported author-year citation addition; three of four legacy citation matches were `[URL]` placeholder false positives.
- 14/588 generations reached the output-token cap; 13 had visibly incomplete endings and are described as probable truncations.
- The earlier parser warned on all 588 free-form responses because it expected a JSON object. This is an evaluation adapter mismatch, not evidence that the model returned malformed JSON. Published-mode parsing was corrected.
- Quantization effects cannot be isolated: no matched BF16 or alternate-quant run exists.
- Semantic equivalence has not been assessed.

Examples and full distributions are in the linked immutable JSON analysis and [`milestone_4_2_failure_taxonomy.md`](milestone_4_2_failure_taxonomy.md).

## M4.2 selective engine status

SCAR now requires author intent and a target span, returns `NO_EDIT_REQUIRED` without inference when no edit is requested, abstains on missing context or technical review requests, wraps protected spans in typed sentinels, checks exact count and order, rejects new protected spans, checks claim-sensitive lexical cues, and produces an author-review-only suggestion. Structural or claim-cue failures return no patch. The system labels semantic equivalence `not_assessed`.

Current implementation checks do not amount to benchmark reproduction or proof of superior writing. The API and CLI require a locally installed XtraGPT model only for explicit eligible edit requests; no-edit and abstention decisions are model-independent.

## Fixed development comparison

One fixed paired run compared full-passage XtraGPT with SCAR on 30 document-distinct IteraTeR-HUMAN development examples (10 each for clarity, fluency, and coherence). It used the same local XtraGPT tag, published prompt mode, 2048 context, temperature 0.1, seed 17, and 128-token cap. The source-side document supplied adjacent context; the revised reference was not included in the prompt. The script, JSON results, and per-example raw outputs are [`run_scar_dev_comparison.py`](../scripts/run_scar_dev_comparison.py), [`scar_dev_comparison.json`](../reports/milestone4_2/scar_dev_comparison.json), and [`scar_dev_comparison_predictions.jsonl`](../reports/milestone4_2/scar_dev_comparison_predictions.jsonl). The sample is fixed by seed and input hashes and was not used for iterative tuning.

Full-passage generation changed 30/30 inputs; its post-hoc protected-span check passed 10/30. SCAR produced a candidate differing from the source on 30/30, but that count includes candidates rejected before any patch can be applied. SCAR marked 6/30 `ACCEPT_FOR_AUTHOR_REVIEW`, rejected 17/30 for structural changes, and rejected 7/30 for claim-cue changes. Structural checks passed 13/30; the seven remaining structurally valid candidates were then rejected by the cue check. Mean observed inference latency was 3.53 seconds full-passage and 3.33 seconds SCAR; SCAR used 9,685 prompt tokens versus 7,484 for full-passage, reflecting its protection instructions and sentinel mapping.

These are automatic development observations only. IteraTeR labels are not necessity labels; this dataset cannot estimate unnecessary-edit rate or a no-edit gate's precision/recall. The six candidates allowed for author review have not been judged by people, and automated checks do not establish semantic preservation. Do not interpret acceptance as a writing-quality result.

## Required comparison protocol

The next controlled study should add identity, current phrase rules, and qualified human revision references, then collect necessity labels on appropriate no-edit examples. Freeze prompts and model revision before any untouched M4.1 test comparison. Record no-edit selection, unnecessary-edit rate, protected-span integrity, claim-review outcomes, wall time, prompt/output tokens, and memory. Do not treat automatic text-overlap metrics as writing quality.

## Human study

Blind 30–50 suitable examples with shuffled method labels and paired source/context. Qualified reviewers should rate: improvement, original acceptability, meaning preservation, scientific precision, disciplinary appropriateness, acceptability, confidence, and disagreement. No qualified-reviewer study has been conducted in this milestone; the result is explicitly pending. The annotation template and protocol are under `data/annotations/revision_necessity/`.

## Limitations and status

This milestone establishes an implementation prototype and a small paired development comparison, not scientific validation. No annotated no-edit data were supplied, so no annotations have been fabricated and no learned necessity classifier was trained. Human outcomes, calibration, model ablations, qualified domain review, and scientific novelty claims remain pending. The existing weak M3 intent classifier is not used as an automatic gate.
