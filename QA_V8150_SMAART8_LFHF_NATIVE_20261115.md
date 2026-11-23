# V8.150 Smaart 8 Auto EQ/FIR LF-HF native overlay — 2026-11-15

## Root cause

Smaart 8 exposes no usable UI Automation plot descendants. Its role adapter
still called the Suite UIA geometry detector first and returned no layout.
Therefore `overlay_positioned` stayed false and both Auto EQ and Auto FIR
correctly failed closed, hiding their LF/HF guides despite a verified tick.

API V3/V4 do not replace this geometry path: the verified integration maps
Smaart 8 to `/api/v3/` and Suite 9 to `/api/v4/`; documented read-only GET
does not expose desktop plot rectangles or a verified TF-frame stream.

## Fix and safety

- Added glyph-verified raster profiles for Smaart 8 native two-plot and
  Lin/Phase/Magnitude layouts.
- A profile is accepted only when independent Phase and Magnitude title masks
  verify both rectangles. Unknown layouts remain hidden/fail-closed.
- Future v8 UIA geometry remains preferred if it becomes available.
- No Generator, measurement, routing, trace file or DSP command was sent.

## Evidence

- Pre-fix live `locate_role_plots(9963292)`: `None`.
- Post-fix live: Phase `(215,114,1474,400)`, Mag `(215,538,1474,399)`.
- Focused geometry/EQ/FIR/sidebar regression: **21 PASS, 1 SKIP**.
- Live Auto EQ: LF 60 Hz / HF 8.00 kHz visible on Magnitude.
- Live Auto FIR PHA: LF 500 Hz / HF 2.50 kHz visible on Phase.
- Evidence images: `QA_V8150_SMAART8_AUTOEQ_LFHF.png` and
  `QA_V8150_SMAART8_AUTOFIR_LFHF.png`.

## Runtime

Patched overlay loaded as PID 32256/18836. Smaart processes were not stopped.

