# RemiX Dou V8.35 — Visible LF–HF crossover band
Date: 2026-10-30 / Admin-PC / Windows / Smaart Suite
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Parent HEAD: 30ca888 (V8.34 cached SUM raster / native Y follow).

## Request
Highlight the entire LF–HF crossover ROI simultaneously in Phase and
Magnitude; update when LF or HF is moved. Preserve native Smaart traces
and V8.34 60Hz cached rendering.

## Implemented
- overlay_v7.py SumGraph.paintEvent: native Hz->X mapping shared with
  LF/HF strips; translucent cyan band from LF to HF in both plots.
- Phase alpha 43; Mag alpha 31, cyan top/bottom thin rails, existing
  teal LF / amber HF dashed edge guides.
- Subtle CROSSOVER LF–HF Hz chip at bottom of Mag when ROI >=165px
  wide; no label overlapping the Phase Match pill.
- Presentation only, drawn separately from cached SUM trace_bitmap.
  Moving LF/HF or viewport Y does not rebuild 4096-bin raster.
- No modifications to H(f), SUM math, DSP, Generator, soundcard or
  user's selected traces.

## Acceptance evidence
- 52/52 pytest PASS; new two-plot highlight test + baseline tests.
- Test verifies fill restricted to ROI, moves from LF 60/HF 200 to
  LF 90/HF 450, and cache rebuild count remains unchanged.
- V8.34 raster parity PASS; F1 1.0 for tested Phase/Mag Y pans.
- Qt-offscreen 4096-bin P95 Phase 2.72ms, Mag 2.91ms (40 frames).
  NOT end-to-end desktop GUI or GPU presentation latency.
- Exact process restart completed: wrapper PID 5004, child PID 4044.
- Smaart native foreground screenshot: V835_CROSSOVER_LIVE_QA.png;
  both plot canvases display LF 60–HF 200 cyan ROI, SUM traces and
  native traces still visible, with RemiX Dou header intact.
- Test screenshot assets: V835_HIGHLIGHT_PHASE_QA.png and
  V835_HIGHLIGHT_MAG_QA.png.

## Rollback / limitations
- Parent 30ca888 retained; previous V8.33 tag unchanged.
- Real native gesture-to-present Y-follow timing remains V8.34 HOLD;
  this change addresses crossover highlight only.
- Preserve unrelated root changes and already-dirty V8.34 screenshots.
