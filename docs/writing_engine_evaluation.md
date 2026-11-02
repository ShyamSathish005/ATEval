# Academic Writing Engine: Dataset and Evaluation Protocol

**Status:** preregistration draft for Milestone 2; no benchmark claims yet.

## Research hypothesis

H1: A local, intent-conditioned, protected-span-aware suggestion workflow improves expert-rated clarity and grammar over no-edit and a transparent phrase-rule baseline, while remaining non-inferior on claim/meaning preservation, citation integrity, technical-term integrity, and author satisfaction.

H2: Adding document/section context and authorized author preferences reduces terminology inconsistency and rejected edits compared with sentence-only editing. This is tested only after the baseline and must not be assumed.

Primary estimand: paired difference in expert clarity rating (1–5) for accepted suggestion sets versus the same author text under no-edit, with all conditions shown in randomized order. Safety co-primary: rate of accepted edits judged to alter claims, hedging, negation, numbers/units, equations, citations, or limitations.

## Conditions

1. No-edit control.
2. Transparent phrase-suggestion baseline (the initial implementation).
3. Local model-assisted, intent-conditioned suggestions, only after a fixed, documented model is available.
4. Author's own revision, where a versioned revision exists; this is a naturalistic comparator, not a perfect quality oracle.

Do not use any AI-detector output, score, or probability as a target, reward, inclusion criterion, or model-selection signal.

## Baseline algorithm definition

For a source document (x), let (W(x)) be its case-folded word tokens, (S(x)) its sentence spans, (P(x)) its blank-line-delimited paragraphs, and (L(x)) the ordered spans matching the protected LaTeX/citation/reference/code/URL/number patterns. The current descriptive features include:

- length-sensitive type-token ratio: (|\mathrm{unique}(W)| / |W|);
- heuristic lexical density: count of tokens outside the fixed stop-word set divided by (|W|);
- sentence length mean and population standard deviation over token counts in (S(x)), and coefficient of variation (\sigma/\mu) when (\mu>0);
- adjacent paragraph content-word overlap: Jaccard (J_i=|C(P_i)\cap C(P_{i+1})|/|C(P_i)\cup C(P_{i+1})|), where (C) removes fixed stop words and tokens shorter than three characters;
- MTLD using threshold (\tau=0.72), with forward and reverse factor counts; values are withheld below 20 tokens.

These are descriptive statistics with language-, length-, and genre-specific limitations. They are not combined into a target score. For each configured phrase pattern (r_j), the editor emits a suggestion (g=(a,b,s,t,mathrm{intent},mathrm{reason})) only when (x[a:b]=s) and ([a,b)) has no intersection with any protected span in (L(x)). Applying an accepted set (G_A) processes spans in descending offset order, requires exact source-span equality and drops overlaps; it never writes to the source file. The preservation check compares the ordered SHA-256 sequence of protected spans before and after. This catches some accidental edits but is neither a semantic model nor evidence of meaning equivalence; every transformation remains subject to author review.

## Data sources and restrictions

- arXivEdits (versioned scientific papers; 751 papers, with a smaller manually intent-annotated subset) is useful for revision-operation and intent research. The paper reports a domain imbalance, so stratify by subject and inspect source permissions/terms before redistribution or model training. Do not treat arXiv version changes as guaranteed human-only edits or as proof that each later version is better.
- IteraTeR supplies iterative revisions across multiple formal-writing domains and edit intentions. Inspect the dataset card, annotation methodology, licenses, and split before use.
- AESW and other academic-error corpora can support grammar-error experiments, but may reflect learner English, venue-specific edits, or synthetic error construction; they are not general academic rewriting gold standards.
- A new expert-reviewed set should span disciplines, sections (abstract, introduction, methods, results, discussion, limitations), author language backgrounds, text lengths, and edit intents. Obtain informed consent, anonymize where possible, respect publisher/copyright and institutional rules, and keep source manuscripts local. Never collect private manuscripts from logs.
- Author-style profiles may only be built from the author's explicitly supplied, authorized samples. Store them locally, allow deletion, and do not pool profiles across users.

## Split and leakage controls

Split by paper/author group and source document, not by sentence. Keep all versions of a manuscript in a single partition. Use chronological/version-aware test sets where possible. Report cross-discipline and cross-section tests separately. Deduplicate exact and near-duplicate documents before splitting. Freeze the test set and annotations before tuning.

## Annotation design

Two independent academic-writing reviewers annotate each source/suggestion pair; adjudicate disagreements with a third reviewer. Hide system identity and condition. Record:

- edit intent (grammar, clarity, concision, terminology, transition, argument structure, citation/format, factual/content update, no change needed);
- clarity, grammatical correctness, discourse coherence, readability for the stated audience, and usefulness (ordinal scales with anchored examples);
- meaning preservation, claim strength/modality, causal direction, negation, numeric/unit, equation, named-entity, terminology, citation, and limitation integrity (each separately; binary plus uncertainty option);
- accept / accept with changes / reject and reason;
- author satisfaction and perceived control after the review session.

Report inter-annotator agreement per dimension (weighted kappa or Krippendorff's alpha as appropriate), confidence intervals, adjudication rates, and subgroup variation. A single “quality” total is not primary.

## Metrics

- **Meaning:** expert claim-preservation ratings; structured proposition/number/negation checks; reading-comprehension questions for a document/passage subset. Semantic similarity is diagnostic only.
- **Integrity:** exact preservation and span-level error rates for citations, equations, numbers/units, protected terminology, named entities, and limitations.
- **Clarity/grammar/coherence:** separate expert ordinal ratings; issue-level precision/recall for diagnostic flags where labels exist.
- **Readability:** report language-specific metrics and audience comprehension; never optimize a readability score alone.
- **Editing:** suggestion acceptance, acceptance-with-changes, rejection, undo rate, edit count, and time; acceptance is not itself correctness.
- **Authorial consistency:** author-approved terminology/preference adherence, measured within writer/discipline; no generic author-style score.
- **System:** latency, memory, model/device/version, reproducibility hash, and abstention/unsupported-span rate.

Use paired bootstrap confidence intervals clustered by document and author. Predefine multiplicity correction for secondary endpoints. Run ablations removing section context, protected spans, author preferences, and each analysis family. Include no-edit, rule baseline, and (if available) local NLP/model baselines. Publish failures and negative findings.

## Safety and release gates

- A candidate edit is never applied to the source file automatically.
- Every accepted or rejected suggestion is timestamped, keyed to a source hash, and exportable as an audit record; retain manuscript text only with explicit user action.
- Any disagreement in claim, modality, causality, negation, numeric/unit, equation, citation, technical term, evidence, or limitation preservation is a critical failure and requires author review.
- Before any rewrite model is exposed, meet a preregistered non-inferiority bound for meaning/integrity and pass expert review. The bound must be set with academic users, not tuned after seeing the test data.
- PDF ingestion is allowed only when extraction quality is measurable; scanned/poorly extracted pages must abstain and request a text/PDF source with a reliable text layer.

## Baseline status

The first engine milestone implements descriptive lexical, sentence, paragraph, section, repetition, and shallow cohesion diagnostics plus review-only phrase suggestions. A deterministic validator compares the exact sequence of protected spans before and after accepted edits; it explicitly abstains on semantic equivalence. The API and CLI are local, and the UI applies accepted edits only to an in-memory draft. Audit records contain hashes, edit snippets, and author decisions rather than full manuscripts. This baseline is not a learned academic rewriting model and has not undergone expert evaluation. PyTorch is packaged as an optional dependency for a later model-assisted milestone but is not invoked by the current baseline. Later proposal models require a separate benchmark, model/data provenance, offline installation, and human safety evaluation.
