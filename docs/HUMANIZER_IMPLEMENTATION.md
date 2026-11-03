# Academic Humanizer implementation

The Academic Humanizer is a review-first, document-level workflow. It is
separate from the detector modules and does not use detector scores as an
editing objective.

## Workflow

1. `import_manuscript` reads TXT, TEX, LaTeX ZIP, DOCX, or a text-layer PDF.
2. The importer builds a prose projection and source pointers. LaTeX commands,
   included files, equations, citations, and unsupported structures remain
   represented in the source bundle rather than being flattened for export.
3. `analyze_manuscript` identifies sections, paragraphs, protected spans, and
   deterministic phrase-rule opportunities. These are proposals, not automatic
   edits.
4. The author selects passages and an objective. Optional local generation is
   routed through SCAR, which applies the author-request gate, context checks,
   protected-content validation, and claim-cue validation.
5. Each proposal is shown side by side. The author may accept, reject, manually
   edit, or leave it pending. Manual edits are revalidated before acceptance.
6. Accepted source-mapped patches are exported only after review. Undo affects
   the in-browser proposal state; the imported source is never overwritten.

Technical, terminology, and structural objectives conservatively require expert
review. A no-change result is valid and is not treated as a failure.

## Local-first and privacy

Inference is local by default. The review history stores proposal metadata in
browser state only; it does not persist manuscript text. The downloadable
change audit is explicitly author-requested and contains the selected edit
snippets, source locations, decisions, and validation results. PDF imports are
read-only.

## Validation commands

```bash
python -m pytest -q
cd frontend && npm run build
```

Optional document support is enabled with
`python -m pip install -e '.[writing-docs]'`. No external service is required
for deterministic analysis or phrase-rule proposals.
