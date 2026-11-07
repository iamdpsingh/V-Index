# Opening Lines design package

Start with [the design specification](../../ROLEWISP_FRONTEND_DESIGN.md) and [the Antigravity task](../../ANTIGRAVITY_DESIGN_TASK.md).

PNG files are viewable design studies; SVG files are editable, with self-contained fonts. The study generator is standard-library Python: `uv run python docs/design/rolewisp/generate.py`. It reads captured public design-data.json, the licensed fonts in this directory and the current provider matrix. It never modifies apps/web or the index. Do not import design-data.json into the production application.

The studies are not interactive UI, live screenshots or browser acceptance evidence. The reader studies show a clearly labelled excerpt; the complete description must remain available in the implementation. The profile study uses empty private fields, not a fabricated account. The coverage study shows selected rows; production must include all 78 names and derive its counts from the API.

Sources: actual local public API records and backend/providers.json, captured November 7, 2026. Font instances derive from Google Fonts' Albert Sans and Hanken Grotesk; original OFL notices accompany them. No stock photos, third-party logos or paid assets.

Rendered PNGs were visually inspected. All SVGs were parsed as XML. Measured contrast ratios: ink/paper 11.74:1, muted/paper 5.40:1, ink/coral button 5.47:1, light/header 11.48:1, success label 6.51:1, caution label 5.43:1, control edge/sheet 3.11:1 and focus/paper 6.96:1. This checks specified color pairs, not full application accessibility. Keyboard, responsive HTML, live API wiring and browser acceptance remain Antigravity implementation checks.

The `weekly-update.png` file is a 1200×630 milestone graphic, not a deployed-product screenshot. It is under the challenge's 5 MB image limit. Use with the [draft update](../../CHALLENGE_UPDATE_2026-11-07.md). Nothing was posted to Vaya or sent to the host.
