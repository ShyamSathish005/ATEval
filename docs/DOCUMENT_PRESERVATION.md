# Document preservation

ATEval keeps the original uploaded bytes separate from the editable prose
projection.

| Format | Analysis | Export | Preservation boundary |
|---|---|---|---|
| TXT | Source-mapped prose | Supported | Exact character ranges |
| TEX | Sections and prose projection | Supported | Exact ranges; markup and unresolved boundaries are read-only |
| LaTeX ZIP | Recursive root/include mapping | Supported | Original archive assets are retained |
| DOCX | Paragraph/run mapping | Supported where `python-docx` is installed | Exact run ranges; tables are reported as unsupported |
| Text-layer PDF | Text projection | Read-only | No write-back to PDF |

Export validates the original source text, exact source ranges, overlap, and
protected content before applying approved patches. It never regenerates a
whole manuscript from the projection. Unsupported elements are returned in the
coverage report so that authors can review them before exporting.

LaTeX equations, citations, references, numeric values, URLs, identifiers,
acronyms, and configured technical terminology are protected by the revision
pipeline. Preservation checks are conservative and are not a claim of
semantic equivalence.
