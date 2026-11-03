# M5.2 Academic-Domain Applicability Gap

## What TXD-22 measures

TXD-22 contains short English question-and-answer responses elicited from
academic and professional prompts. The adapter exposes the source prompt,
response, source class, and a single domain value:
`academic_and_professional`.

The primary Task A test set contains 8,091 pure AI responses and 450 pure
human responses. The corpus also contains 9,000 mixed-authorship responses,
which were excluded from binary metrics and analyzed separately.

## What it does not establish

TXD-22 is not a corpus of complete academic manuscripts. It does not support
claims about:

- introduction, methods, results, discussion, or conclusion structure;
- citation and reference behaviour;
- equations, tables, figures, LaTeX, or structured scientific content;
- long-range coherence across sections;
- discipline-specific terminology or writing conventions;
- human editing of AI text in realistic manuscript workflows;
- proficiency groups or verified human author identities;
- robust domain transfer, because the adapter exposes only one usable domain
  bucket in this run.

The dataset description reports approximately 350 human contributors, but the
downloaded CSV and adapter do not expose participant IDs. Author-level
generalisation and participant-stratified confidence intervals cannot
therefore be computed. Publication date or the `Human written` class is not
proof that no prior AI assistance occurred.

## Consequence for interpretation

The measured AUROC `0.5541` and human FPR `0.2467` describe this TXD-22
response task only. The length-matched AUROC `0.6296` does not close the
manuscript applicability gap. It is not valid to present either number as
performance on full academic papers.

The single-domain subgroup result is identical to the aggregate result:
AUROC `0.5541`, FPR `0.2467`. No domain-matched comparison is possible from
the available metadata. Generator-specific results are exploratory because
each generator subgroup contains AI records only; within-generator AUROC is
therefore undefined and reported as a single-class diagnostic rather than a
performance claim.

## Requirements for a future manuscript-focused corpus

The next qualification effort should require:

1. complete documents or clearly defined manuscript sections with section
   boundaries;
2. human provenance with consent/ethics documentation and author-group IDs
   that can be used only for leakage-resistant splitting;
3. AI provenance including model family, version/date, prompt, decoding
   settings, and whether humans edited the output;
4. document-level and, where genuinely annotated, span-level authorship
   labels;
5. discipline, genre, language, proficiency, citation, equation, and
   formatting metadata where lawful and relevant;
6. document, author, prompt, topic, and generator-disjoint split options;
7. explicit licence and redistribution terms for raw and derived data;
8. length-matched and discipline-matched evaluation cohorts;
9. a human academic negative-control cohort with provenance caveats;
10. a held-out modern-generator and held-out-discipline evaluation design.

Until those requirements are met, ATEval should treat stylometric output as a
descriptive supporting signal only.
