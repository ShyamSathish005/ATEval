# Known limitations and feature status

| Capability | Status | Boundary |
|---|---|---|
| Local web/API workspace | Implemented; integration-tested | Research prototype, not security-certified. |
| TXT, TeX, project ZIP ingestion | Implemented; parser tests and UI smoke-tested | TeX is a prose projection; unsupported macros/assets are surfaced. No TeX compilation. |
| DOCX / text-layer PDF ingestion | Optional; unit tests are dependency-gated | Extraction is parser-dependent; PDF is read-only. |
| ZIP traversal/decompression safeguards | Implemented and unit-tested | Limits reduce risk but are not a comprehensive sandbox. |
| Linguistic profile | Implemented as descriptive diagnostics | Not an authorship or AI-writing signal. |
| Academic revision suggestions | Experimental; review-required | Structural validation does not prove semantic equivalence. Human evaluation is incomplete. |
| Revision-intention classifier | Experimental baseline | Weak held-out scores; advisory only. |
| AI-writing detection algorithms | Unavailable | No detector is implemented; no score or authorship conclusion is produced. |
| Large model inference | Optional and user-managed | No automatic download; hardware, license, and data-protection constraints apply. |
| Public demo | Not deployable for confidential uploads | Requires a separate public-mode implementation and independent privacy/security review. |
| Scientific validation | Not established | Published research review and local baselines do not establish effectiveness. |
| Apache-2.0 release rights | Unresolved | Workspace ownership and contributor authority must be verified before relicensing. |

Do not use ATEval to make academic-integrity or misconduct determinations.
