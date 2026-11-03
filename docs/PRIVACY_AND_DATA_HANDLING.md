# Privacy and data handling

- Manuscripts are processed by the local API by default.
- The default API and Compose bindings are loopback-only.
- Ollama URLs are restricted to loopback HTTP; remote inference is not enabled
  by the humanizer.
- Full source text is not stored by manuscript analysis or browser undo
  history. Browser history is discarded on refresh or browser closure.
- The optional change-audit download contains selected proposal text, source
  locations, decisions, and validation metadata.
- Local SQLite metadata is stored under `.ateval/`; remove it only after
  stopping ATEval and checking that it contains nothing to retain.
- ZIP paths, upload size, and source mappings are validated. PDF is read-only.

ATEval does not advertise end-to-end encryption, hosted confidential manuscript
processing, or remote-provider privacy guarantees.
