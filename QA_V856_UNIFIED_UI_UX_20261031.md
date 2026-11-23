# RemiX Dou V8.56 — unified Auto Phase / Auto EQ / FIR UI/UX
Date: 2026-10-31. Admin-PC Windows, canonical repo.
Base HEAD: 101b1e8 (V8.55 source).

## Scope
Qt presentation only. No phase/EQ/FIR solver, data/trace identity, audio I/O, DSP, hardware, Smaart or generator changes.

## Design system
- Smaart sidebar remains at original 205px; plots are not covered.
- Dark OLED, high-contrast green for Auto Phase, orange for Auto EQ, cyan for FIR.
- Consistent hierarchy: Trace -> Setup -> Action -> Result.
- Static QSS: no expensive blur, animation or recurring repaint.
- No duplicate heading. Vietnamese labels via Unicode.
- Vertical scrolling on smaller windows, never horizontal scrolling.

## Implementation
New remix_layout_v856.py manages stable static design tokens and safe Qt widget reordering.
signal_tools_gui_v813.py invokes the helper on dock initialization and mode changes.
- Auto Phase retains 2-Trace identity, one action and Top 3 candidate choices.
- Auto EQ retains one verified Trace, native LF/HF, Fs, target, Max PEQ, Boost/Cut, marker and MagEQ. Boost/Cut share one row. Run/Export buttons above long results.
- FIR retains one verified Trace, tap count, Fs, native state, design and TXT/WAV export. Buttons above detailed results.
Original widgets, signals, source verifications and workers remain intact.

## Read-only Qt geometry evidence
At 205x560 dock:
- Phase page 400px, all three candidates present.
- Auto EQ page 510px, primary action y=284px.
- FIR page 455px, primary action y=215px.
- No horizontal scroll for all 3 tabs, tested with height 310/420/560.

## Acceptance
- New test_v856_unified_three_tool_layout.py: 11/11 PASS.
- Selected full regression: 224/224 PASS, 69.10s.
- compileall and git diff --check: PASS.
- No Smaart, hardware, Generator, Sweep or DSP change.
- Real physical Smaart UI acceptance is separate from Qt/offscreen QA.
