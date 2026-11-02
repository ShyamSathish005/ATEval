# Milestone 4.2 M4.1 failure taxonomy

## Audit scope and preservation of the prior run

This audit reads the original M4.1 JSONL as an immutable artifact. It does not rewrite or regenerate predictions. The file contains 588 unique record IDs from 70 source documents; the manifest check in the M4.1 report found no document leakage. Its SHA-256 is `5c7da1abaed3723d79cf89925e4c14c4e56857c0f4fcf08348279e31fa6d1535`.

The detailed machine-readable analysis is [`m4_1_failure_analysis_refined.json`](../reports/milestone4_1/m4_1_failure_analysis_refined.json). The original run aggregate remains in [`xtragpt_1_5b_q8_0_benchmark.json`](../reports/milestone4_1/xtragpt_1_5b_q8_0_benchmark.json), and every output and its original telemetry remain in [`xtragpt_1_5b_q8_0_predictions.jsonl`](../reports/milestone4_1/xtragpt_1_5b_q8_0_predictions.jsonl).

## Quantitative findings

| Failure / behavior | M4.1 observation | Classification |
|---|---:|---|
| Output changed from source | 587/588 (99.83%) | Generation/selectivity failure |
| Human reference was a no-op | 4 rows | Dataset includes too few no-op examples for a necessity model |
| No-op references changed | 4/4 (100%) | Missing revision-necessity gate; the request supplied an edit intention for each row |
| Numeric sequence changed | 140/588 (23.81%) | Structural preservation failure; includes invented values and dropped/rewritten values |
| Citation sequence changed, refined detector | 1/588 (0.17%) | One unsupported author-year citation was added |
| Protected sequence changed, refined detector | 140/588 (23.81%) | The unique affected rows are numeric-sequence failures; the citation addition overlaps one of them |
| Protected sequence failures from original detector | 143/588 (24.32%) | Three were false positives because `[URL]` was treated as a citation |
| Generated tokens reached configured cap | 14/588 (2.38%) | 13 visibly stop mid-sentence; finish reason was not recorded, so truncation is probable rather than confirmed for all 14 |
| Prompt plus generated tokens | maximum 685 of 2,048 | No context-window overflow is indicated by recorded token counts |
| JSON parser warning | 588/588 | Evaluator-format mismatch: published XtraGPT returns free-form text, while the M4.1 wrapper expected JSON |

The model emitted an output for all 588 requests. Per-request generation latency averaged 2.30 seconds (median 2.13; p95 4.34). Aggregate wall time was 1,353.85 seconds. These are runtime observations, not quality evidence.

The phrase-rule and identity comparisons remain unchanged. XtraGPT changed every reference no-op. The grouped set has only four no-op references, so its no-op frequency is not sufficient to train or validate a reliable edit-necessity estimator.

## Failure categories with examples

### Unrequested additions and claim inflation

Source: “The proposed method improves model performance by 12% on the held-out dataset.”

Smoke output: “The proposed method demonstrates a significant improvement of 12% in model performance when evaluated on the held-out dataset. This enhancement is specifically validated against a conventional baseline, indicating that our approach not only enhances accuracy but also provides actionable insights for future research.”

The 12% string survived, but the model added statistical significance, narrowed unspecified performance to accuracy, and claimed actionable research insights. The original does not support those additions. This is a claim-integrity failure, not a numeric-regex failure.

### Unsupported numerical claims and number rewriting

One source says that a model achieved the best scores on **7 of 10 datasets**. XtraGPT rewrote this as a score “**1.0 point higher**” and recast “datasets” as “evaluation metrics.” The values are unsupported and the evaluation unit changes. A different output changed the enumerated source points `1)`, `2)`, `3)` into prose and omitted the explicit enumeration. These are material failures even if a generic text-similarity score remained high.

### Citation invention and citation-detector false positive

One source sentence contains no citation; the generated passage adds “(Seyfarth, 2014)” and further asserts findings not present in the source. The refined citation detector flags this one actual citation addition.

The earlier broad citation regex also treated the dataset placeholder `[URL]` as an author citation in three records. Those outputs retained `[URL]`; they were not citation modifications. M4.2 narrows the citation pattern and protects `[URL]` as an acronym/identifier instead. This corrects evaluator false positives without altering the source prediction file.

### Long rewrites and output truncation

The first held-out source is a short sentence about supervised training. The output expands it into an explanation of PET and extra context. More generally, 587 rows changed, so the published instruction-conditioned setting applied broad revision pressure even to already-acceptable source text.

Fourteen responses used all 128 allowed new tokens. Thirteen end without sentence-final punctuation and visibly stop mid-clause, including an output ending “The results indicate that our IT”. M4.1 telemetry did not preserve Ollama's finish reason, so the retrospective report labels all 14 as cap-hit and the 13 unfinished rows as likely truncations. The M4.2 engine now rejects outputs that consume its configured generation budget.

## Why the changed rate was 99.83%

The M4.1 prompt construction mapped an existing IteraTeR revision-intention label to an editing instruction and submitted every item to XtraGPT. Those labels describe the kind of change found in an edited pair; they are not labels for whether editing is necessary. The prompt therefore asked the model to revise every input. There was no independent gate that could return `NO_EDIT_REQUIRED`, and the data had only four unchanged references. This explains the high change rate more directly than model size or quantization.

The M4.1 source and output tokens do not establish an effect of Q8_0 quantization. Only one official GGUF tensor quantization was run; neither BF16 nor another quant was evaluated. No quantization-quality conclusion is supported.

## Extraction and validation audit

- **Response format:** the official XtraGPT prompt returns free-form revision text. The earlier generic parser attempted to parse JSON and attached a parse warning to every result. This is a software/parser mismatch; it does not mean each model response was malformed. The published-mode adapter now treats this output as free text.
- **Numbers:** exact token and unit comparison correctly catches values the model added, dropped, or changed. It cannot decide whether a number written as a word is equivalent; such cases need human inspection. The new protector also detects number words in addition to numeric strings.
- **Citations:** the broad `[AUTHOR]` alternative generated three false positives on `[URL]`. A refined form handles numeric bracket citations, author-year citations, and LaTeX citation/reference commands.
- **Protected spans:** 143 historical flags fall to 140 after removing the three `[URL]` false positives. All 140 refined failures include a changed numeric expression; the added `(Seyfarth, 2014)` is among them. Structural matching detects span differences but does not test claim equivalence.
- **Context truncation:** the maximum recorded prompt had 574 tokens; maximum prompt-plus-output was 685 under a 2,048 window. No input overflow is visible in telemetry. This does not prove that all M4.1 prompts represented enough document context: inputs contained only the target and paired adjacent context, not a full paper.
- **Output truncation:** prompt token counts and completion counts are recorded, but no finish reason was preserved. Fourteen outputs reached 128 tokens; thirteen are visibly incomplete.

## Implications for SCAR

SCAR addresses these failures with author-controlled no-edit/intention decisions, a target-span plan, typed sentinel protection, an independent completeness gate, conservative claim-cue comparison, and fail-closed review states. It will keep identity output when no edit is requested, require expert review for technical-review requests, reject missing/duplicate/modified sentinels, reject protected values introduced outside sentinels, and reject generation-cap hits. A structurally accepted revision still requires author review; automated checks do not establish semantic equivalence.

The M4.1 full-rewrite output remains a baseline. The M4.2 selective and SCAR development runs are separate artifacts and do not overwrite it. Human academic review remains pending.
