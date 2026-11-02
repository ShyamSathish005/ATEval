# Milestone 4.5 — Manuscript Intelligence

## What is implemented

The local workspace now has a **Manuscript Intelligence** page for `.txt`, `.tex`, complete LaTeX project `.zip`, `.docx`, and text-layer `.pdf` input. Analysis produces a document-scoped JSON report with source-mapped passages, section labels, descriptive writing diagnostics, protected or excluded regions, method availability, and limitations. The upload is analyzed in memory; this workflow does not persist manuscript contents to the workspace database.

LaTeX ZIP ingestion checks archive size, expanded size, file count, duplicate paths, symbolic links, and traversal paths before reading content. It resolves a selected or unambiguous root file and recursively follows local `\\input` and `\\include` files. It retains file and character offsets for editable prose. Equations, comments, citations, references, macros, and unsupported constructs are excluded or surfaced as limitations instead of being presented as ordinary prose. PDF extraction is read-only and requires a usable text layer.

Passages can be selected for local SCAR revision at selected, section, or manuscript scope. Objectives include clarity, grammar, concision, structure, technical precision, and terminology consistency. SCAR is invoked without detector inputs, and all generated changes remain proposals. Authors can edit a proposal manually, validate it, accept or reject it individually, accept eligible proposals after explicit confirmation, and restore the original draft. Accepted edits are source-range checked, checked for protected content and claim-cue changes, and included in an audit. Conflicting, stale, protected, or unsupported edits fail closed. PDF is never exported as edited source.

Exports include the original source format for text, TeX, ZIP projects, and supported DOCX files. ZIP exports retain untouched project assets. DOCX mapping and edit-back require the optional `python-docx` dependency and only support edits whose source mapping stays within a single run; cross-run edits are read-only. The report can be saved as JSON or HTML and printed to PDF through the browser print dialog. The workspace also offers a side-by-side prose projection and a downloadable decision audit.

## AI-writing signal availability

The registry currently lists detector methods as planned; there are no supported detector implementations in this build. Accordingly, the report says `not_analyzed`, reports zero detector coverage, uses grey passage states, and leaves detector model, tokenizer, raw score, score direction, calibration, and uncertainty unavailable. It does not generate an AI-written percentage, a human-written label, or an authorship conclusion. Linguistic measures remain writing-quality diagnostics and are not used as authorship signals. Detector outputs do not affect SCAR planning or generation.

## Important limits

- A `.tex` file with external local dependencies should be uploaded with its project ZIP so recursive inputs and assets can be resolved. Remote dependencies are not fetched.
- Ambiguous roots, malformed includes, unsupported LaTeX constructs, PDF extraction problems, and uneditable source spans are reported. The application does not compile LaTeX or claim a complete semantic model of a manuscript.
- PDF is a read-only text projection. Scanned PDFs and uncertain extraction should not be treated as complete analysis.
- The analysis API enforces document and archive limits. Passage identifiers and source offsets are local document coordinates, not stable identifiers across edits to the source.
- Protected-span checks and claim-cue checks are guardrails, not proof of semantic equivalence. Every proposed change needs author review.
- This milestone does not implement a detector, calibrated uncertainty, expert evaluation, or scientific validation of revision quality.

## Validation

The targeted manuscript/API suite covers text mapping, long and repeated passages, LaTeX exclusions and section context, nested project imports and asset-preserving ZIP export, ambiguous roots, unsafe paths, malformed includes, stale and overlapping edits, PDF availability, unsupported uploads, detector-unavailable reporting, local revision failure handling, and export behavior. DOCX mapping/export tests are optional and skipped when `python-docx` is absent. Full project validation is recorded in the delivery summary after running the repository's Python suite and frontend build/site checks.
