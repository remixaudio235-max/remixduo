# RemiX Dou Auto EQ V8.42 - native LF/HF draggable ROI and Max PEQ label

Date: 2026-10-31. Admin-PC.
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting HEAD: 0923674 (V8.41 automatic saved Smaart sample rate).
DO NOT copy/merge the old AutoEQ worktree over this integrated source.

## User request
- Remove visible Auto EQ LF 60 Hz and HF 8000 Hz spin inputs.
- Draw two independent, draggable -- LF/HF line markers on Smaart's
  original Magnitude plot, same native drag UX as Auto Phase.
- PEQ8 means MAXIMUM allowed EQ bands, not required result count.
  Label now says "Max PEQ 8" (range 1-12).

## Implementation
- EQDialog retains two hidden validated numeric controls for its solver
  parameters, but neither is in the right-side visible layout.
- One compact range label displays the current numeric ROI and directs
  the user to the native Magnitude line handles.
- Reuse the existing ROIMarker and ROILineGrip classes for two EQ-owned
  top labels + full-height narrow hit strips; drag anywhere on the line.
  No full-size mouse interception. LF and HF are bounded, ordered and
  mapped through log frequency, using actual Smaart plot geometry.
- EQ and AutoPhase have DISTINCT ROI states. Dragging EQ LF/HF does not
  touch AutoPhase LF/HF, SUM, delay, DSP, or Source / Sample Rate.
- Two dashed LF/HF lines and a subtle highlighted EQ region render
  before Auto EQ is computed, with one verified Smaart tick.
- The same lines remain when MagEQ + numbered PEQ markers and gradient
  are drawn. If EQ ROI changes, invalidate the old preview and Export EQ
  immediately; a new Auto EQ execution uses the new LF/HF.
- Switching to AutoPhase, FIR, Hide or live tuning removes EQ ROI widgets;
  returning to EQ restores only EQ state. Native Qt window lifecycle
  closes all four EQ marker/grip windows without leaks.
- The original overlay SUM Phase/Mag and V8.35 crossover paint paths
  are unmodified other than an EQ-only early paint branch.
- Native source remains read-only. No Smaart writes, soundcard,
  generator, DSP, TF data or stored TRF modification.

## Verification
- New test_v842_eq_roi_drag_native.py: 3/3 PASS:
  (1) LF/HF spinboxes absent from visible GUI, Max PEQ default 8,
      separate draggable line head and full-height hit strips,
      EQ Mag overlay visible before solver.
  (2) LF/HF drag updates the exact solver args, invalidates old result,
      preserves AutoPhase's independent ROI and prevents crossing.
  (3) Native EQ dashed Mag lines render without MagEq source and
      hide on mode switch / workspace hide.
- Full V8.28-V8.42 + AutoEQ 0.19 selected regression: 114/114 PASS.
  Last focused post-text-fix regression: 56/56 PASS, compileall PASS.
- V8.34 Qt paint (4096 bins / 40 frames):
  Initial mixed-load Mag P95 spike 47.31 ms; isolated repeated 4 runs:
    Phase P95 1.34-1.73 ms, Mag P95 1.64-1.99 ms.
  A mixed-load spike is not automatically excused as a pass of real
  mouse-to-present latency; live drag P95 remains HOLD.

## Deployment and acceptance
- Git: commit only focused overlay_v7.py, signal_tools_gui_v813.py,
  test_v842_eq_roi_drag_native.py, and this QA document.
- Keep all pre-existing dirty documents/images from other sessions.
- Restart only exact RemiX Dou companion PID/source after confirming owner.
- Smaart was not running at initial session inspection; do not claim
  actual Smaart drag acceptance based on Qt offscreen simulations.
- When Smaart is visible, verify two dashed EQ markers are present
  before pressing AUTO EQ, dragging each matches cursor frequency,
  MagEq re-computes for updated range, and switching tools hides lines.
