# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

## Selected ATEval design direction

- Source visual: third generated direction, the light Research Ledger overview with three factual zero-state counts and a divided dataset/method/configuration setup list.
- Typography preference: Poppins for all UI text, as requested by the user; keep all font files bundled locally through Fontsource.
- The navigation, spacing, restrained cobalt accent, warm-white canvas and local-only labels should follow that visual. Use truthful live API data and preserve clear empty states.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
