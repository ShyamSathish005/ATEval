# Academic Humanizer acceptance tests

These are repeatable acceptance scenarios for a local synthetic manuscript.
They must be completed manually in the browser for interaction behavior and
are supplemented by the automated tests named below.

1. Upload a `.txt` or `.tex` synthetic manuscript with at least three
   paragraphs. Confirm sections and editable passage mappings appear.
2. Select one passage, choose Academic clarity, request a proposal, and confirm
   the original source is unchanged.
3. Accept the first safe proposal and reject a second proposal. Confirm only
   the accepted proposal appears in the reviewed draft preview.
4. Choose **Edit manually**, change the candidate, and run manual validation.
   Confirm an unsafe protected-number or citation change cannot be accepted.
5. Accept two non-overlapping proposals while leaving another paragraph
   untouched. Export the reviewed document and compare it with the original:
   only approved ranges may differ.
6. Select **Undo last decision** after accepting a proposal. Confirm the
   accepted count and preview revert. Refresh the page and confirm the
   browser-session history is gone.
7. Upload a LaTeX ZIP containing included files, bibliography, equation,
   figure, table, custom macro, Unicode, comments, and cross-reference.
   Confirm unchanged assets survive ZIP export. Confirm passages crossing
   markup boundaries are read-only.
8. Upload a text-layer PDF. Confirm analysis is available but reviewed export
   is disabled.

Automated coverage:

- `tests/test_api.py`: upload, no-op/abstention, unavailable model, timeout,
  and single-edit export.
- `tests/test_manuscript_analysis.py`: source maps, LaTeX/ZIP/DOCX/PDF
  boundaries, stale edits, overlap, and asset preservation.
- `tests/test_scar.py`: author gate, protected content, claim cues, abstention,
  and generation limits.
- `tests/test_m61_humanizer_validation.py`: multi-edit acceptance boundary,
  LaTeX protected-source checks, empty responses, prompt shape, and telemetry.
