# M5 product requirements

ATEval has two distinct product modules:

1. **AI Writing Evaluator:** a local, evidence-reporting analysis surface for
   passage-level signals associated with machine-generated text. It must expose
   method, configuration, uncertainty, limitations, and document/author/domain
   coverage. It must never present a signal as proof of authorship.
2. **Academic Humanizer:** a review-first revision surface for clarity,
   coherence, terminology, transitions, and sentence structure. It must
   preserve protected technical content, support selective no-edit decisions,
   compare original and revised text, and export only author-approved edits.

The M5 foundation implements only the first deterministic stylometric signal
baseline. It is executable but uncalibrated and has no labelled detector
benchmark. The humanizer remains an experimental author-review workflow built
on SCAR and local generation; complete document-level humanizer work is a
subsequent milestone.
