# RemiX Dou V8.58 - Auto Phase dock height on tool switch

Date: 2026-10-31, Windows Admin-PC.
Canonical Git repo: D:\REMIX_AUTO_ALIGN_V6_DEV
Working source: windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline: V8.57 commit fb16729.

## Reported fault and reproduction
When switching from Auto EQ into Auto Phase the dock becomes very short
and cuts off the trace/candidate panels until HIDE and re-open.
Exact root cause in RightToolDock.apply_rect:
   invalid_phase = (currentWidget is Phase and quality invalid
                    and not verified)
   if invalid_phase: h = min(h,148)
This incorrectly treats an ineligible or transient Trace classification
as a dock geometry instruction.
Red pre-fix regression: EQ -> Phase with invalid pair and desired
dock 410px produced only 148px, test assertion failed.

## Production fix
Remove only the selection-derived min(h,148) geometry clamp.
Always follow Smaart-derived screen-checked dock rectangle.
Existing _set_tick_presentation(False) can still shrink the trace
card, hide candidates and disable phase solve while two traces
are not verified. This is deliberate, preserving source safety.
QScrollArea already supports physically small viewport heights.

No change to Smaart audio, DSP, TF, selected Trace, Auto Phase
solver, EQ/FIR, native pixels, generator or hardware.

## QA
New test_v858_phase_dock_height_switch.py checks:
- EQ and FIR -> Phase at quality invalid/transient/weak/valid.
- No spurious 148px clamp after mode transition.
- Invalid pairs still disable solve and hide candidates.
- Valid pair restores full card content without HIDE.
- Repeated changes across Phase/EQ/FIR at heights 560/390/310.
- No horizontal scroll.
After fix: 21/21 combined focused + V8.56 layout tests PASS.
Broad regression results appended after execution.

## Final regression
- Selected full V8.16-V8.58 regression: 244/244 PASS, 34.58s.
- Python compileall PASS, git diff --check PASS.
- Updated V8.33 legacy QA test: warning card still compacts to 70px with three ticked traces, but the 310px outer dock is never shortened to 148px.
- Physical Smaart mouse-driven switch acceptance remains separate from deterministic Qt/offscreen regression.
