# Milestone 4.1 failure analysis

## Run scope

This report covers the local XtraGPT-1.5B smoke examples and the complete held-out output file for the final frozen run. The smoke prompts are diagnostic examples, not random test predictions. The final benchmark used the published XtraGPT prompt at temperature 0.1, seed 17, 2,048 context, and 128 maximum new tokens on the hash-verified test split. See [`generation_benchmark.md`](milestone_4_1_generation_benchmark.md) and the per-example JSONL for full provenance.

## Confirmed smoke failures

### Unsupported meaning and overclaim

**Input:** “The proposed method improves model performance by 12% on the held-out dataset.” Context mentioned a conventional baseline and said the finding was limited to the evaluated benchmark.

**Output, first prompt run:** “The proposed method demonstrates a significant improvement of 12% in model performance when evaluated on the held-out dataset. This enhancement is specifically validated against a conventional baseline, indicating that our approach not only enhances accuracy but also provides actionable insights for future research.”

The output introduced statistical significance, narrowed unspecified model performance to accuracy, and added a research-impact claim. Those additions are unsupported by the source. Its exact numeric token survived, demonstrating that numeric preservation does not prevent claim drift.

### Context duplication and redundant transition

**Output, follow-up run:** “The proposed method demonstrates an improvement of 12% in model performance when evaluated on a held-out dataset. This result is specifically limited to the benchmark used for evaluation.”

The second sentence repeats context supplied by the following sentence, and changes “the held-out dataset” to “a held-out dataset.” It is a safer candidate than the first output but still adds no necessary value and slightly weakens referential specificity. It is not automatically accepted.

## Failure taxonomy for the full run

The machine-readable predictions record per-output warnings and preservation diagnostics. The automatic report can enumerate numeric/citation/protected-span changes, extra text, edit distance, and no-op-reference overediting. The following require human annotation and are not inferred from surface metrics: changed claims or scope, omitted qualifiers, unsupported additions, generic academic filler, repetitive output, technical-term substitutions, citation meaning, and awkward discourse transitions.

Reviewers should classify each example with one or more failure labels: `meaning_change`, `number_or_unit_change`, `missing_qualifier`, `unsupported_addition`, `technical_term_substitution`, `citation_change`, `unnecessary_edit`, `repetition`, `generic_phrasing`, `awkward_transition`, or `unacceptable_output`. Do not classify every lexical difference as an error; preserve room for stylistic preference and safe alternatives.

## Comparison limits and model status

The identity and phrase-rule outputs are retained as fixed comparators. IteraTeR BART and PEGASUS are not run because their fine-tuned checkpoint cards do not state a checkpoint-specific license. The separate general-instruction comparator is not run because no independently licensed local checkpoint was present. Results in the final XtraGPT report are therefore a three-system machine comparison, not a full model matrix.

Human review has not been performed. There is no evidence yet that XtraGPT improves clarity, acceptability, author satisfaction, or technical correctness over the baseline. The model is enabled in the UI only as an optional local, reversible, review-required draft generator.

## Open failure questions

1. How often does the model add evidence or causal explanations absent from the source?
2. Are mistakes clustered by section, edit intention, sentence length, or citation density?
3. How frequently does it edit when the human reference is a no-op?
4. Does a stronger preservation instruction reduce unsafe additions without suppressing useful revisions?
5. Do expert reviewers prefer any candidates after seeing the source and surrounding paragraph?

Answer these with the blind review packet and annotated examples. Do not optimize prompts against the sealed test rows; use a separate validation sample, freeze settings, then run a new held-out experiment.
