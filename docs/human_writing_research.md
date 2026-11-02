# Human Writing and Academic Editing Research Review

**Review date:** 2026-11-01
**Scope:** evidence for a local academic writing assistant that diagnoses clarity and presents author-controlled revisions.
**Non-goal:** classifying authorship, imitating a generic “human style”, or optimizing against AI-detector scores.

## Review method and limits

This is a focused, source-led review of peer-reviewed work and primary research records relevant to register variation, text cohesion, lexical/syntactic measures, revision behavior, and semantic preservation. It is not a systematic review: searches were not exhaustive, no formal screening protocol was preregistered, and some references are research corpora or books rather than journal articles. Findings should guide a baseline and evaluation plan, not be presented as settled universal laws.

## Findings by research area

### Human writing, register, and authorial variation

Biber’s multidimensional analysis represents registers using co-occurring linguistic features and latent functional dimensions. Its central implication for this project is methodological: register is multidimensional, genre-dependent, and cannot be reduced to one “human” feature profile. Academic writing varies across disciplines, tasks, audiences, and authors. Features such as nominalization, stance, elaboration, and explicit reference can be useful descriptive measurements, but a single preferred value is not a quality target. [Biber, *Variation across Speech and Writing* (1988)](https://doi.org/10.1017/CBO9780511621024).

Authorial voice is therefore treated as an optional within-writer reference, supplied with authorization, and used to surface terminology/preferences for review. The engine must not infer that a writer should match a corpus average. A short or single-genre sample is insufficient to establish a stable personal style.

### Vocabulary and lexical diversity

Type-token ratio changes strongly with text length. McCarthy and Jarvis evaluate lexical-diversity measures and warn against treating a raw type-token ratio as length-invariant. MTLD and related measures are preferable descriptive options for longer text, but remain sensitive to text length, domain, tokenization, morphology, and topic. Report sample size and measure definition alongside every value; never reward diversity by itself. [McCarthy & Jarvis (2007)](https://doi.org/10.1177/0265532207080767); [McCarthy & Jarvis (2010)](https://doi.org/10.1016/j.lingua.2010.02.001).

### Syntax and complexity

Fine-grained clausal and phrasal indices can characterize syntactic complexity more precisely than sentence length or traditional readability formulas. They were developed and evaluated in an L2-writing context, so construct validity does not transfer automatically to expert academic prose or other languages. [Kyle & Crossley (2018)](https://doi.org/10.1111/modl.12468). ATEval reports sentence-length and parser-derived indices as observations; it does not infer that longer, shorter, simpler, or more complex syntax is intrinsically better.

### Cohesion, coherence, and discourse

Coh-Metrix operationalizes linguistic and discourse features at multiple levels, including referential and causal cohesion. These measures are proxies for textual cues that may support comprehension; reader knowledge, task, and context still affect coherence. [Graesser et al., *Coh-Metrix* (2014)](https://doi.org/10.1017/CBO9780511894664); [McNamara et al. (2010)](https://doi.org/10.1080/01638530902959943). ATEval can flag repeated terms, weak lexical overlap between adjacent paragraphs, or missing connective references as prompts for author inspection. Such flags are not judgments that a passage is incoherent.

### Academic conventions and argumentation

Academic communication is a set of situated genres. Claims, evidence, hedging, limitations, citations, and section moves must be interpreted in the discipline and rhetorical context. A pattern detector can identify candidate claim language and nearby citation markers, but cannot determine whether evidence actually supports a claim. The product must display those as review cues and retain original wording.

### Human revision behavior and edit intentions

arXivEdits contains 751 versioned arXiv papers with sentence alignments and a manually annotated sample of fine-grained edits and intentions. It demonstrates that scholarly revision includes language refinement, grammar/typo correction, content updates, and formatting, including paragraph and sentence insertion, deletion, rephrasing, splitting, merging, and reordering. Coverage is skewed toward physics and mathematics and only 1,000 sentence pairs receive fine-grained human intent labels; it is not a universal editing gold standard. [Zhao et al., *arXivEdits* (2022)](https://arxiv.org/abs/2210.15067).

IteraTeR annotates iterative revisions across multiple formal-writing domains. Its reported model performance varies substantially by intention: fluency and clarity were easier to identify than style and coherence, and model revisions remained distinguishable from human revisions in human evaluation. This supports intent-specific suggestions, explicit abstention, and iterative author control instead of a single rewrite objective. [Du et al., *Understanding Iterative Revision from Human-Written Text* (2022)](https://arxiv.org/abs/2203.03802).

### Context-aware rewriting and semantic preservation

Meaning preservation must be evaluated separately from readability or simplicity. Agrawal and Carpuat’s reading-comprehension-based evaluation found that even the best evaluated system produced simplified content that left at least 14% of questions unanswerable. Sentence-level similarity and lexical overlap are not guarantees of preserved claims, modality, causal direction, or limitations. [Agrawal & Carpuat, TACL (2024)](https://doi.org/10.1162/tacl_a_00653).

For academic manuscripts, protected spans should include equations and math delimiters, citations, references, numbers with units, named entities, technical terminology, and author-designated locked text. A semantic model may assist with review, but must not automatically certify equivalence. Candidate changes that touch these spans, change a claim/hedge/negation, or require paragraph restructuring should be marked high risk and require author review.

### Readability and evaluation

Readability formulas compress text into a small number of surface counts and do not account adequately for specialist knowledge, task, argument quality, or target audience. They can be reported as descriptive, language-specific diagnostics only. Meaning, clarity, grammar, discourse flow, terminology, citations, and author satisfaction need separate evaluation dimensions; a composite score would hide trade-offs.

## Closest prior methods and proposed positioning

The closest prior systems and resources are (1) register/multidimensional analysis, (2) Coh-Metrix-style text easability and cohesion analysis, (3) parser-based syntactic complexity tools such as L2SCA/TAASSC, (4) edit-intention models and corpora such as arXivEdits and IteraTeR, and (5) controllable simplification/revision systems evaluated for meaning preservation. The proposed ATEval contribution is not a novel detector or a claim to generate uniquely human text. The testable contribution is a local, academic-document editor workflow that combines **rhetorical context + transparent multilevel diagnostics + protected-span-aware revision proposals + explicit author acceptance + a replayable audit**, then evaluates these as separate dimensions against no-edit, local rule-based, and model-assisted baselines.

This is a research hypothesis, not a novelty claim. A literature search and comparative experiments are required before asserting that the combination is new or improves outcomes.

## Current implementation boundary

The first working baseline uses transparent, conservative diagnostics and narrowly scoped phrase suggestions. Linguistic analysis, phrase editing, protected-span processing, semantic-preservation checks, and document extraction live in separate modules. Its measures are descriptive and its suggestions require review. It does not generate whole-document paraphrases, run semantic-entailment models, claim authorial-style imitation, or use detector scores. spaCy can provide an explicitly installed local dependency parser; PyTorch is reserved for a later model-assisted milestone and is not invoked by this baseline. No model weights are downloaded implicitly. See [`writing_engine_evaluation.md`](writing_engine_evaluation.md) for the corpus protocol and primary metrics.

## Selected bibliography

1. Biber, D. (1988). *Variation across Speech and Writing*. Cambridge University Press. [DOI](https://doi.org/10.1017/CBO9780511621024).
2. McCarthy, P. M., & Jarvis, S. (2007). vocd: A theoretical and empirical evaluation. *Language Testing, 24*(4), 459–488. [DOI](https://doi.org/10.1177/0265532207080767).
3. McCarthy, P. M., & Jarvis, S. (2010). MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment. *Behavior Research Methods, 42*, 381–392. [DOI](https://doi.org/10.3758/BRM.42.2.381).
4. Kyle, K., & Crossley, S. A. (2018). Measuring syntactic complexity in L2 writing using fine-grained clausal and phrasal indices. *The Modern Language Journal, 102*(2), 333–349. [DOI](https://doi.org/10.1111/modl.12468).
5. Graesser, A. C., McNamara, D. S., & colleagues (2014). *Automated Evaluation of Text and Discourse with Coh-Metrix*. Cambridge University Press. [DOI](https://doi.org/10.1017/CBO9780511894664).
6. McNamara, D. S., Graesser, A. C., McCarthy, P. M., & Cai, Z. (2010). Coh-Metrix: Capturing linguistic features of cohesion. *Discourse Processes, 47*(4), 292–330. [DOI](https://doi.org/10.1080/01638530902959943).
7. Du, W. et al. (2022). Understanding iterative revision from human-written text. *Proceedings of ACL 2022*. [Paper and data links](https://arxiv.org/abs/2203.03802).
8. Zhao, Y. et al. (2022). arXivEdits: Understanding the human revision process in scientific writing. [Paper and data links](https://arxiv.org/abs/2210.15067).
9. Agrawal, S., & Carpuat, M. (2024). Do text simplification systems preserve meaning? A human evaluation via reading comprehension. *Transactions of the Association for Computational Linguistics, 12*, 432–448. [DOI](https://doi.org/10.1162/tacl_a_00653).
