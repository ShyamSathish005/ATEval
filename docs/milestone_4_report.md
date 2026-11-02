# ATEval Milestone 4 report

**Run date:** 2026-11-01  
**Scope:** audit M3 intention results, research four additional resources, implement a context-aware generation path, and benchmark available systems without inventing unavailable results.

## Completed

### Milestone 3 failure analysis

Created [`intent_model_failure_analysis.md`](intent_model_failure_analysis.md) before increasing model size. It includes class distributions, the label crosswalk, per-class precision/recall/F1, confusion matrix, grouped split details, training convergence, tokenizer/truncation analysis, context construction, dataset alignment and leakage, and a protocol comparison with the original IteraTeR paper.

The main conclusion is that 0.2050 held-out macro-F1 is for a smaller, six-class **source-only** intention task. The original IteraTeR classifier receives both original and revised text, uses a different split and five reported intent categories, and reports class-wise F1. Those numbers are not directly comparable. Saved logistic-regression and SVM artifacts converged well below their iteration caps; there is no convergence evidence supporting a larger model.

### Additional corpus and benchmark research

Created [`extended_revision_research.md`](extended_revision_research.md) covering XtraGPT, Re3-Sci2.0, CASIMIR, EditEval, licenses, dataset-source rights, inference, hardware, suitable use, and benchmark availability. Re3-Sci2.0 remains restricted to non-commercial use as specified by its dataset record. CASIMIR's MIT repository declaration is kept separate from source-paper/review rights. No restricted dataset was added to model training or distribution.

### Context-aware generation component

Added [`academic_generation.py`](../ateval/revisions/academic_generation.py), a modular local XtraGPT Transformers adapter with request/response dataclasses. Inputs include a selected sentence or passage, paragraph context, adjacent sentences, section, editing instruction, protected terminology, and citations. Outputs include a proposed revision, rationale, expected benefit, potential technical risk, preservation report, warnings, and review status.

The adapter uses XtraGPT's published `<PAPER_CONTENT>`, `<SELECTED_CONTENT>`, and `<QUESTION>` contract. It loads only from a supplied local checkpoint directory, never downloads weights implicitly, refuses overlong context instead of silently truncating, permits no-change proposals, uses deterministic decoding, and never writes over the manuscript. It checks protected-span, supplied-term, and citation presence. Structural checks do not establish semantic equivalence; all candidates require author review.

Added two CLI paths:

```sh
python -m ateval revisions propose \
  "The original academic sentence." \
  --paragraph-context "Relevant surrounding paragraph." \
  --section discussion \
  --instruction "Improve clarity without changing the claim." \
  --protected-term "treatment effect" \
  --model-path /path/to/local/XtraGPT-1.5B

python -m ateval revisions benchmark-generation-model \
  data/processed/iterater_human_grouped_v1/sentence_test.jsonl \
  --test-documents data/processed/iterater_human_grouped_v1/document_test.jsonl \
  --test-manifest data/manifests/revision_test_manifest.json \
  --license-verified \
  --model-path /path/to/local/XtraGPT-1.5B \
  --model-id Xtra-Computing/XtraGPT-1.5B@<pinned-revision> \
  --model-license MG0-2.0 \
  --training-data-license-note "not independently verified" \
  --model-license-reviewed \
  --prompt-mode ateval \
  --output reports/milestone4/xtragpt-ateval-comparison.json
```

The benchmark reports identity and current rules on the same held-out rows alongside model output, records model-file checksums and runtime versions, and notes that the held-out intent label is used as an oracle instruction. It stores aggregate metrics, not manuscript predictions. It reports BLEU/ROUGE/edit overlap and structural preservation as diagnostics only. The optional backend runner supports XtraGPT, a generic local instruction-following Transformers model, and IteraTeR BART/PEGASUS using their official intent-prefix, beam-search, and length settings.

### Generation benchmark status

Re-ran the identity and rule baselines on the hash-verified grouped test set: 588 examples from 70 document groups. The identity baseline has BLEU 0.7921, ROUGE-L 0.8665, zero edit overlap F1, and 0% change rate. The existing rule editor has BLEU 0.7918, ROUGE-L 0.8664, edit-operation F1 0.00129, and 0.68% change rate. These are copying/overlap diagnostics and do not demonstrate better academic writing. The output is [`generation-baselines.json`](../reports/milestone4/generation-baselines.json).

The full generation system matrix is recorded in [`generation-benchmark-status.json`](../reports/milestone4/generation-benchmark-status.json). IteraTeR BART/PEGASUS runners are implemented but remain unrun because their fine-tuned checkpoint cards do not assert a license for those weights. XtraGPT 1.5B/3B and a general instruction model remain unrun because no checkpoint is local, the project Python environment lacks Torch/Transformers, and the machine has 8 GB unified memory with no CUDA/MPS. The 1.5B checkpoint is a later quantized-inference candidate; full-precision 3B or larger models do not fit the current resource budget with adequate runtime headroom. No model output or benchmark score has been fabricated.

## Checks performed

- Compiled the modified Python modules with `py_compile`.
- Confirmed both new commands appear in the revision CLI and reviewed `propose --help`.
- Parsed the new experiment and benchmark JSON files.
- Recomputed DistilBERT tokenizer lengths with the pinned local tokenizer. Local context exceeded 256 tokens in 122/3,936 examples (3.10%); the target was partly truncated in 4 examples. Truncation is a measurable but small issue, not the primary explanation for low F1.
- Verified the M4 test file hashes, row/document counts, record IDs, and disjoint train/dev/test document groups against the immutable manifests before running generation baselines.
- Inspected saved sklearn estimators: logistic regression used 28–35 iterations of 600; calibrated linear SVM estimators used 551–940 iterations of 1,200.
- No unit-test suite was run in this milestone. No checkpoint was loaded and no expert evaluation was conducted.

## Remaining evidence gates

1. Resolve rights for IteraTeR fine-tuned BART/PEGASUS checkpoints and XtraGPT's ReviseQA source text before using them in the intended distribution context.
2. Place a version-pinned, reviewed XtraGPT checkpoint on a machine that can run its local inference stack; then run the same 588 held-out rows through both the published prompt and the ATEval prompt.
3. Add a licensed general instruction-following local comparator and exact official BART/PEGASUS runners once their checkpoint licenses are explicit.
4. Run the M4 benchmark and preserve outputs only where the research corpus terms permit; use document-disjoint scoring and record software/model checksums.
5. Conduct blinded academic review with multiple qualified reviewers, report agreement and cluster-aware uncertainty, and assess technical meaning/citation integrity independently. Until then, no quality improvement or semantic-preservation claim is supported.

No AI-detector score was used as an objective, reward, selection criterion, or evaluation metric. No novelty, human-authorship, or authorship-consistency claim is made.
