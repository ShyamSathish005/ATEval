# Revision model experiment protocol

**Status:** initial document-grouped CPU benchmark run; expert writing evaluation remains planned and has not been conducted.

## Questions and hypotheses

- **RQ1:** How well does a transparent CPU intention classifier distinguish revision purposes on source-document-held-out data?
- **RQ2:** Does context-aware review reduce unsafe edits and improve expert-rated clarity compared with no edit and the current phrase-rule baseline?
- **RQ3:** Which components (context, protected spans, author preferences, intent conditioning, semantic flags) affect clarity, acceptance, and preservation?

H1: on a rights-cleared held-out corpus, the NB baseline improves macro-F1 over a majority-class baseline. This is exploratory; if it fails, report it. H2: the review workflow improves expert clarity ratings while meeting a preregistered non-inferiority bound on meaning/integrity selected with academic users before test-set inspection. Do not tune the bound post hoc. H3: context and author-authorized preferences reduce terminology inconsistency or rejection compared with sentence-only context. Treat as unconfirmed until measured.

## Data and splits

1. Use only an export with documented source-text permissions and provenance. Keep IteraTeR HUMAN separate from FULL (model-propagated) labels. For arXivEdits, require both version licenses per pair and a use-specific allowlist; do not assume its repository code license covers paper text.
2. Preserve original labels and document IDs. Do not discard annotator disagreement. Keep all versions, revisions, sentences, and near-duplicates of a source manuscript within one split.
3. Use the corpus's official train/dev/test partitions where available, verify document-level disjointness, and fail before scoring if overlap exists. `classification_metrics` rejects any test document identifier stored in the training artifact.
4. Do not sample or download a dataset automatically. Record its URL/release, export hash, access date, exact terms, preprocessing, excluded records and reasons, and license manifest hash.

## Intent baseline

The earlier Multinomial Naive Bayes CLI is retained as a simple local baseline. Milestone 3 additionally compares majority, word+character TF-IDF logistic regression, and sigmoid-calibrated linear SVM under sentence, neighboring-sentence and full-document contexts. C is selected on validation macro-F1 only. Test metrics include per-class scores, confusion counts, calibration diagnostics and exploratory domain slices. Unchanged pairs are omitted from intention classification because the corpus has no edit-necessity label. See `experiments/iterater-human-document-grouped-classical-intent-v1.json` and the saved comparison artifact. Do not interpret confidence as the probability an edit is correct.

## Editing study

Conditions: (A) no-edit, (B) existing narrow phrase-rule proposals, (C) context-carrying intent-tagged proposals, and later (D) pinned local model-assisted proposals. Randomize and blind condition identity. Sample across abstract, introduction, methods, results, discussion, and limitations; multiple academic disciplines and author language backgrounds; and edit intents. Authors decide whether to accept, edit, or reject; use a within-document paired design where feasible.

Two academic reviewers independently score each output for clarity, grammar, discourse coherence, audience readability, authorial preference match, and acceptability. Separately score claim/meaning, modality/scope, numbers/units, equation, terminology, citation, evidence attribution, causality, and limitation integrity. Adjudicate critical disagreements. Authors report satisfaction, control, accept/reject/edit decisions, and time. Keep reviewers blind to system identity and detector output.

## Analysis plan

- Primary effectiveness: paired difference in expert clarity rating (1–5) against no-edit.
- Primary safety: critical meaning/integrity error rate on accepted edits; establish a non-inferiority margin with users in advance.
- Secondary: grammar, coherence, readability, terminology consistency, author preference match, accept-with-changes/reject rates, undo rate, time, and abstention.
- Report inter-rater reliability per dimension (weighted kappa or Krippendorff alpha as appropriate), adjudication, document-cluster bootstrap confidence intervals, and subgroup results.
- Compare the NB classifier with majority; compare editing conditions to no-edit and rules. Include failure cases. Correct for multiplicity on secondary outcomes.
- Ablate context, protected spans, author preferences, and individual analysis families. Use the same data partitions and expert rubric across variants.
- Do not use AI-detector scores or authorship predictions as objective, reward, selection criterion, or evaluation endpoint.

## Reproducibility and execution

Local commands support inspection, training, and evaluation of user-provided local exports:

```sh
python -m ateval revisions inspect iterater local-human-export.json --split train
python -m ateval revisions train-intent iterater local-human-train.json --split train --license "reviewed source terms" --license-verified --output intent-model.json
python -m ateval revisions evaluate-intent intent-model.json iterater local-human-test.json --split test --license "reviewed source terms" --license-verified
```

For arXivEdits also supply `--manifest licenses.json` with per-paper `versions` entries for both version IDs and repeat `--permitted-license EXACT_ID` only for terms independently reviewed for the intended use. The tool is an ingestion gate, not a legal determination. Never write a model/report over an existing path.

Archive command lines, ATEval version, Python and dependency versions, data/export hashes, split leakage result, random seeds, training parameters, system/hardware details, annotation guide, and model artifact hash. The current baseline is deterministic and CPU-only. Synthetic unit fixtures test software behavior and must not be reported as corpus performance.

## Current evidence boundary

Licensed IteraTeR-HUMAN exports were downloaded, inspected and regrouped at source-document level because the upstream partitions overlap. A real held-out test run is reported in `milestone_3_report.md`. Identity and the existing phrase rules were also evaluated on the same held-out human references. These automatic comparisons are not writing-quality judgments. No expert academic review was conducted; no semantic-equivalence rate, general-purpose quality gain, or novelty claim is made. See [`revision_benchmark_report.md`](revision_benchmark_report.md) for the earlier Milestone 2 status and [`milestone_3_report.md`](milestone_3_report.md) for updated evidence.
