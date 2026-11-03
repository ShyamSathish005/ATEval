# Academic humanizer architecture

The humanizer is a separate review-first module, not a detector-evasion
pipeline:

```mermaid
flowchart LR
  Manuscript[Full manuscript] --> Parse[Sections, paragraphs, source maps]
  Parse --> Intent[User-selected revision objective]
  Intent --> Select[Selective edit / no-edit gate]
  Select --> Protect[Typed protected spans]
  Protect --> Generate[Optional local generation]
  Generate --> Validate[Structural and claim validation]
  Validate --> Compare[Original vs proposed diff]
  Compare --> Review[Accept, reject, or edit]
  Review --> Export[Approved export and audit trail]
```

Existing SCAR, protected-content, claim-cue, generation, and export components
provide the foundation. The complete document-level objective selector,
context-aware draft workflow, and end-to-end multi-edit review surface remain
experimental and require a subsequent implementation milestone. No proposal is
applied automatically and no detector score is used as an optimization target.
