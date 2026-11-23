# RemiX Duo V8.158 — Smaart 8 + Smaart Suite user-action E2E QA

Date: 2026-11-16. Device: DESKTOP-VNPRJCI. Installed EXE: C:/Users/Administrator/AppData/Local/Programs/RemiX Duo/RemiXDuo.exe. Commercial RELEASE HOLD.

## Sessions and source isolation

- Initial processes responding: Smaart 8 PID 44468 HWND 525128; Smaart Suite PID 35308 HWND 1579990; RemiX Duo v8.158 PID 36356.
- Smaart 8 active source: TUNNINNGGG-13.trf (806 bins). Suite active source: TUNNINNGGG-13-1.trf (different file; no numerical parity claim).
- Running both Smaarts causes global running_major() to return None by design. Actual App.tick() resolves edition-specific trace path using bound HWND.
- Test harness used foreground HWND, edition, and actual UIA ComboBox ValuePattern contents to verify exact TRF before computing, with the inactive Smaart minimized.
- An early Suite-labeled EQ action actually occurred when Smaart 8 had foreground; the resulting V8 TRF was excluded as a WRONG-FOREGROUND TEST, not accepted as a Suite result.
- Smaart Suite PID 35308 and HWND 1579990 disappeared near end of QA. No related Windows Application Error was found in the recent error window inspected. Root cause unknown; Suite not relaunched.

## Real installed GUI test matrix

| Test | Smaart 8 | Smaart Suite |
|---|---|---|
| Correct edition/HWND and TRF source binding | PASS | PASS, but intermittent 0/3 tick |
| 1 trace disables Auto Phase | PASS | Not signed off |
| 2 actual ticked traces -> SUM and Top 3 | PASS: sub p5 + TUNNINNGGG-13 | HOLD, Suite exited before test |
| Auto Phase first candidate | PASS: invert Trace2, delay 7.10ms | HOLD |
| Restore extra trace tick | PASS: sub p5 OFF, TUNNINNGGG-13 ON | Not applicable |
| FIR PHA calculation and visible purple line | PASS: 1024 taps, 693-2075Hz | PASS: 512 taps, 500-2026Hz |
| FIR MAG solver | PASS: 512 taps | PASS: 512 taps |
| MagFIR line persists after verify | FAIL/HOLD: native plot not verified on repeat | FAIL/HOLD: PASS transient then HOLD and missing line |
| Auto EQ numeric result | PASS: 4 PEQ | HOLD: native tick rearm 0/3 |
| Auto EQ MagEQ visible and Export EQ enabled | HOLD: missing line, export disabled | NOT VERIFIED |
| Tool selection via real toolbar | PASS | PASS |
| Real FIR file export to TXT/WAV | HOLD: source proof 0/3 before menu | NOT TESTED |
| Isolated fresh LF/HF drag+rollback | NOT completed in this two-edition run | NOT TESTED |
| Generator/DSP/audio changes | NONE | NONE |

Smaart 8 2-trace Auto Phase generated V7_SUM_RENDER_READY and V8155_AUTO_PHASE_READY 4 elapsed_ms 177.3. Screenshot shows 3 options, #1 Trace2 inverted delay 7.10ms. Tick sub p5 restored OFF and corroborated with 9-row native pixel map after moving mouse off the icon.
Smaart 8 FIR PHA showed line and PhaseFIR PASS; Excess RMS 134.3 to 125.1 degrees. This correction is weak and retains existing warning.
Suite FIR PHA showed line and PhaseFIR PASS; Excess RMS 18.9 to 14.7 degrees. Mode-specific values are not directly comparable across separate TRF files.
Both MagFIR solves produced 512 taps, but post-solve native verification can drop PASS to HOLD when foreground/source/plot proof is lost. Smaart 8 repeated run reported NO_FRAME: Không xác minh được Phase/Magnitude Smaart 8.
Smaart 8 Auto EQ computed V8152_AUTOEQ_PREVIEW_READY TUNNINNGGG-13 4, but no convincing MagEQ line or authorized export.

## QA automation pitfalls discovered

- Qt checkable FIR MAG/PHA exposed as UIA CheckBox: UIA TogglePattern toggled CHECKED without emitting QPushButton clicked(), resulting in a WRONG MODE first trial. That trial was discarded; retest with real click_input computed MagFIR correctly, then hit HOLD on re-verification.
- UIA ComboBox window_text is a static accessible label; actual TRF must be read from iface_value.CurrentValue. Middle-elision requires edition-specific suffix validation.
- Competing desktop sessions stole foreground and minimized windows. Tests failed closed when the expected exact host or source was unavailable.

## Screenshot evidence (relative to this folder)

- build/qa_dual_safe_suite_fir_phase.jpg — Suite PhaseFIR visible PASS
- build/qa_dual_safe_suite_fir_mag.jpg — Suite MagFIR missing after HOLD
- build/qa_dual_safe_8_fir_phase.jpg — Smaart8 PhaseFIR visible PASS
- build/qa_dual_safe_8_fir_mag.jpg — Smaart8 MagFIR missing on repeat
- build/qa_dual_safe_8_eq.jpg — Smaart8 EQ numerical PASS, visual/export HOLD
- build/qa_dual_v8_autophase_top.jpg — Smaart8 2 traces / Top 3 PASS
- build/qa_dual_8_phase_view.jpg — Smaart8 1-trace negative gate PASS
- build/qa_dual_v8_twotrace_before.jpg / after.jpg — tick event evidence
- Full runtime log: %LOCALAPPDATA%/RemiXDuo/logs/overlay.log
- Test scripts: build/qa_dual_*.py

## Prioritized next gates

P0: Stabilize 3/3 tick rearm and foreground switching across both Smaart editions without reusing another edition's source; preserve data-only cache but strict GUI/export validity.
P0: Stabilize native MagFIR verification after geometry changes and focus loss; preserve fail-closed safety and diagnose PrintWindow/title checks.
P0: Fix Auto EQ paint/export native lifecycle; numeric worker alone is insufficient.
P1: Run actual Suite 2-TRF Auto Phase/Top3 and restore checkbox; native LF/HF drag with rollback; save actual FIR/EQ exports to a QA folder; check 20-minute display continuity and GUI latency.
P1: Sign new installer and retest clean installation.

Previous staged automated V8.158 regression: 828 passed, 54 skipped, 1 warning. The real two-edition GUI gates above remain incomplete, so commercial RELEASE HOLD.
