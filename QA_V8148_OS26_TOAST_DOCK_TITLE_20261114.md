# V8.148 OS26-style Toast + clean tool title — 2026-11-14

## Changes

- Removed `DOCK/OVERLAP/FLOATING` suffixes from the visible Auto Phase/EQ/FIR
  title. Placement mode remains available in the heading tooltip for diagnosis.
- Rebuilt the shared Toast shell for Windows and portable UI:
  - compact dark glass-like card without continuous blur/repaint;
  - 10 px radius, subtle shadow and 4 px semantic accent;
  - `info`, `busy`, `success`, `warning`, `error` tone tokens;
  - maximum plot width 520 px and height 84 px;
  - bottom-right safe inset and 5 second auto-dismiss;
  - one reused label, full message retained in tooltip;
  - accessibility name and semantic description retained.
- Auto Phase trace/tick notices target the Phase plot when visible instead of
  covering the compact right-side control panel.

The UI/UX Pro Max guidance was used for transient 3–5 second feedback,
non-obstruction, high contrast, stable bounds and restrained motion. Continuous
blur/animation was intentionally avoided on the Smaart overlay to reduce
repaint/flicker risk.

## Evidence

- TDD RED: old 8 s timeout, 640 px Toast and visible `AUTO PHASE · OVERLAP`
  reproduced as three failures.
- Focused Toast/layout/dock final: 33 PASS in 5.17 s.
- Shared/contracts final: 114 PASS, 4 SKIP in 9.78 s.
- Controlled cutover loaded overlay PID 35952/34580 and watcher PID
  32800/29188. Smaart PID 39912 was preserved.
- Native screenshot visibly shows `AUTO PHASE` without `DOCK`; PASS.
- Live appearance of a transient Toast during a real calculation remains HOLD;
  the overlay is a separate top-level Qt Tool window and was not force-clicked
  through the Smaart UI automation target. Styling/geometry/timer/tone routing
  are covered by the focused Qt tests.

No Generator/Sweep, soundcard routing, Smaart trace data or DSP write occurred.

