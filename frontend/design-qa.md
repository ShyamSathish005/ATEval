# ATEval Design QA

## Evidence

- Selected reference: [`public/design-option-3.png`](public/design-option-3.png), concept 03 chosen by the user.
- [Open the side-by-side reference and live prototype review](http://127.0.0.1:5173/design-qa-preview.html) while the local Vite server is running.
- The live prototype was opened and inspected in Chrome using the CUA browser controls at a 2880 × 1306 desktop capture. Workspace, dataset empty state, experiment wizard and reports were observed. The UI showed no browser error overlay; the local API status was connected.

## Comparison

| Area | Result |
| --- | --- |
| Composition | Preserved the reference's fixed left rail, workspace header, generous title and count row, ruled setup section, and restrained empty state. |
| Color and surfaces | Kept the white and warm-neutral surfaces, dark navy copy, light dividers, cobalt primary action, and subtle blue active navigation. |
| Typography | Applied the user's Poppins choice throughout the application. This intentionally changes the reference's serif headings to Poppins. Font files are bundled locally. |
| Navigation | Expanded the reference's small navigation into the complete requested research workspace sections; the active item, search, local-only status, theme, and new-experiment action remain visible. |
| Data integrity | Empty states use actual local API counts. The prototype does not invent detector scores or completed reports. |
| Responsive behavior | Sidebar, toolbars, tables, wizard and detail layouts have responsive breakpoints; a narrow-screen browser capture was not performed. |

## Findings and iteration

- Fixed a literal `\n` that displayed in the overview description; the copy now wraps as normal text.
- Bound the wizard's random seed to draft configuration so the visible value is persisted.
- The desktop preview and TypeScript/Vite production build pass. Python API and foundation unit tests pass (11 tests).
- The selected mock is an image and does not define behavior for other pages. Those pages were implemented to match the same restrained visual system and keep research state truthful.

## Known implementation limits

- No detector is currently implemented and tested, so experiment execution and result charts remain unavailable and clearly labeled.
- The local LaTeX workspace inspects selected source files in the browser; compilation is only reported when a local TeX compiler is detected.
- Academic quality auditing is a placeholder and does not claim to run an audit.
