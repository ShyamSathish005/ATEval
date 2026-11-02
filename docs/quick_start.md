# Quick start

1. Install Python 3.11+, then follow [Installation](installation.md).
2. Run `python -m ateval doctor` to inspect optional components.
3. Start local UI/API with `python -m ateval api` and open
   `http://127.0.0.1:8000` after building the frontend.
4. In Manuscript Intelligence, choose a permitted `.txt`, `.tex`, `.zip`,
   `.docx`, or text-layer `.pdf` file. The API enforces its byte limit and
   parses the file locally.
5. Inspect source-mapped passages and limitations. Suggestions require author
   review; export creates a separate reviewed artifact and never overwrites
   the selected original.

No AI detector is currently implemented. A blank detector result is not
evidence that a text was written by a human. Do not submit confidential work
to a remote service.
