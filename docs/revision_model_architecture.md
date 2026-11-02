# Revision analysis and academic editing architecture

## Research position

The implementation is a working CPU baseline and staged architecture, not a trained academic rewriting model. It does not claim novelty, generate whole-document rewrites, estimate a universal human-style score, or use AI-detector scores. The closest prior resources are IteraTeR's iterative intent dataset and arXivEdits' scientific revision pairs; both show that revision labels are heterogeneous and that coherence/style/meaning-change prediction is substantially less reliable than simpler fluency and clarity labels. See [dataset analysis](revision_dataset_analysis.md) and [literature review](human_writing_research.md).

## Processing stages

```text
local manuscript / local revision export
             │
             ├── document extraction and format-aware protected spans
             ├── section / paragraph / sentence segmentation
             ├── monotonic revision alignment (training-analysis path)
             ├── lexical, syntax, repetition, and cohesion observations
             ├── stage 1: candidate cue + abstention
             ├── stage 2: intent-tagged, context-carrying edit proposal
             ├── semantic and structural preservation checks
             └── human review, decision, draft application, audit
```

The existing interfaces remain: `ateval writing analyze FILE` produces a read-only analysis report; the local API powers the review interface, where Accept/Reject decisions are explicit and applied changes affect an in-memory draft. Proposed edits carry original offsets, exact source text, risk, rationale, section, paragraph, and neighboring sentences. An absent cue yields `no_change_candidate` rather than a forced rewrite. The current UI suggestions are still the conservative phrase rules in `ateval/writing/editing.py`.

The revision-data path is separate from manuscript editing. Dataset adapters ingest only user-supplied local exports. Alignment records sentence grouping and exact character diff spans. The intention classifier is a transparent multinomial Naive Bayes CPU baseline; it is a corpus analysis comparator and does not generate user prose. Training requires a verified-license flag. Model artifacts retain training document identifiers so evaluation fails closed on source overlap.

## Component boundaries

| Module | Responsibility | Current method / boundary |
|---|---|---|
| `ateval/revisions/schema.py` | Versioned provenance record and validation | Stores raw + canonical intents, split, version stage, offsets, context, confidence, and rights review |
| `ateval/revisions/datasets.py` | Local IteraTeR and arXivEdits adapters | No downloads; arXivEdits requires exact source/target version license manifest and allowlist |
| `ateval/revisions/alignment.py` | Sentence splitting, monotonic sequence alignment, edit spans | CPU token/character similarity DP; not the paper's neural CRF; diffs do not infer intent |
| `ateval/revisions/taxonomy.py` | Dataset label crosswalk | Keeps raw labels; does not guess unknown classes |
| `ateval/revisions/classification.py` | Intention classification baseline | Multinomial NB over before/after tokens and edit features; first label only |
| `ateval/revisions/evaluation.py` | Accuracy, macro-F1, per-class F1, confusion and baseline metrics | Hard source-ID holdout check; human review is still required |
| `ateval/revisions/revision_depth.py` | Revision-stage summary | Descriptive only; does not assume later means better |
| `ateval/writing/analysis.py` | Descriptive features and review-only proposals | Heuristic measures and protected-span detection |
| `ateval/writing/editing.py` | Narrow transformations and exact-span application | Rule-based; author accepts; no silent source write |
| `ateval/writing/semantic.py` | Preservation validation | Structural token checks; explicitly abstains on semantic equivalence |
| `ateval/writing/latex.py` | LaTeX/citation/math protection | Conservative span protection; malformed/unrecognized markup needs inspection |

## Algorithm definition: implemented baseline

Let `x` be the source text. Stage one computes supported rule cues `C(x)` and protected spans `L(x)`. It proposes candidate `c_j=(a_j,b_j,s_j,t_j,r_j)` only if the configured phrase pattern matches exactly at `[a_j,b_j)`, `x[a_j:b_j]=s_j`, and that span does not intersect `L(x)`. Its decision is `review_candidate` when a cue exists and `no_change_candidate` otherwise. This is an eligibility check, not a learned need-for-edit score.

Stage two passes eligible cues through the transparent phrase baseline. It adds edit intent, section, containing paragraph, and previous/current/next sentence for reviewer context. The proposal is `g_j=(a_j,b_j,s_j,t_j,i_j,q_j,k_j)` where `i` is mapped intent, `q` is explanatory reason, and `k` is review risk. Only explicit author acceptance applies the change, in descending offsets, after verifying the current source substring still equals `s_j`. Rejected edits are audit events. The document remains a draft until a user exports/saves it through an explicit action.

For revision-analysis data, `align_sentences(A,B)` maximizes a sequence score over transitions `(1,1)`, `(1,2)`, `(2,1)`, insertion, and deletion. Match similarity is a weighted combination of token-set Jaccard, character-trigram Jaccard, and token-length ratio. The returned path is monotonic, deterministic, and intended as a reproducible baseline. `SequenceMatcher` then returns exact changed character intervals. Neither score implies semantic preservation.

The classifier estimates `argmax_y P(y) Π_f P(f|y)` with Laplace smoothing over source/target tokens, added/removed tokens, and coarse change-ratio bins. It emits descriptive probabilities, not calibrated confidence. The current single-label baseline takes the first canonical label. This baseline is intentionally modest so corpus restrictions, leakage controls, and evaluation can be made reproducible before a neural editor is introduced.

## Planned model-assisted extension

Only after a rights-cleared, grouped, human-labeled training/evaluation set exists, consider a local encoder or sequence-to-sequence model. Candidate inputs should include the target sentence, paragraph/section context, task intent, locked technical terms, and authorized author preferences. Separate (1) a change-necessity/abstention decision, (2) a small set of candidate edits, and (3) semantic/structural validation. Train with edit demonstrations rather than an objective to mimic a corpus-average voice. Keep factual additions, citations, numbers, equations, limitations, and claim-strength changes out of autonomous generation. A local CPU baseline remains available when model weights or GPU resources are absent.

Model choice, weights, tokenizer, decoding, data license, preprocessing, seed, and hardware must be pinned and documented. PyTorch is optional and should be introduced only when an experiment demonstrates a need; model installation must not download weights implicitly. No model-assisted feature is enabled by this milestone.
