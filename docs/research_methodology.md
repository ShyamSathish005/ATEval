# Research methodology and claim policy

ATEval separates document ingestion, descriptive linguistic analysis,
revision-intention classification, optional revision generation, structural
preservation checks, and human review. These components answer different
questions and must not be collapsed into an authorship score.

Evaluation reports should state the exact dataset version and license, source
and document grouping, split manifest and hashes, preprocessing, model and
checkpoint revision, prompts, decoding settings, metrics, uncertainty, and
all exclusions. Compare methods only when data and evaluation protocols are
aligned. Keep test data out of threshold selection and model selection.

Revision evaluation should include identity/no-edit and simple baselines,
meaning and citation preservation, grammaticality, academic clarity,
discourse coherence, terminology integrity, and blinded expert review. Human
participants need appropriate consent and de-identification. Do not optimize
revision generation using AI-detector scores. Detector outputs are not a
valid reward for writing quality or human-likeness.

Current grouped classifier and generation results are exploratory. Their
sample sizes and datasets do not establish generalization to scientific
manuscripts or user satisfaction. Read the individual experiment protocols
and failure analyses before reusing results. No scientific validation is
claimed for ATEval as a product.
