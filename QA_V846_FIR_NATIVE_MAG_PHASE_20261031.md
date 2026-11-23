# RemiX Dou V8.46 — FIR complex Mag/Phase on shared native Smaart plot overlays

Date: 2026-10-31 / Admin-PC.
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA.
Starting Git HEAD: 6e73ff0, branch qa/remix-signal-v825-checkpoint.

## Delivered
- FIR remains an OFFLINE 1-verified-Trace design with saved Smaart Fs and
  read-only original TRF. V8.45 TXT/WAV Float32 output is preserved.
- After FIR design, the SAME FIR worker also computes the complex
  predicted transfer H_after(f)=H_source(f)*H_FIR(f). FIR response is
  derived from its actual taps via scipy.signal.freqz, retaining
  linear-phase group delay rather than treating FIR as a magnitude-only
  correction.
- NativeFIROverlay (fir_native_v846.py) captures the ORIGINAL Smaart
  window once per registration, checks Magnitude/Phase plot roles, and
  validates the original source's Magnitude pixels independently.
  GRID Y-axis alone can never authorize the source.
- The Phase overlay requires an additional independent native Phase
  pixel-to-source match for the SAME source color, same screenshot,
  same HWND/geometry/revision. Phase axis is assumed to span exactly
  360 degrees and must match pixels at >=0.78 with an ambiguity margin.
  If Phase cannot be confirmed, PhaseFIR HOLD; MagFIR may remain.
- Original source phase is circular-smoothed at 1/6 octave, then
  actual complex FIR phase is applied without smoothing away group
  delay. PhaseFIR wraps at 360-degree boundaries; no false connections.
- MagFIR and PhaseFIR share the existing engine.graph_mag and
  engine.graph_phase transparent, click-through Qt plot windows.
  No new plot widgets, Smaart GUI injection, hardware or DSP writes.
- Old FIR MiniPlot is hidden; right panel shows explicit MagFIR/PhaseFIR
  PASS/HOLD status instead of implying an unregistered prediction is
  native Smaart-corrected.
- Both plots use one immutable FIRFrame for complex data, matched
  source identity, viewport, window rectangle and timestamp.
  Native frame expires after 450ms, and source/token/Fs changes reset
  FIR layer. Background/minimized Smaart, lost focus, mode switch,
  tool HIDE and unverified trace all fail closed.
- The expensive Mag/Phase paths are rasterized as RGBA images in the
  native worker and Qt draws prepared QImages. This removes prior
  expensive, repeated wrapped-phase QPainterPath strokes.
- Explicitly no IIR→FIR→Delay/INV→Complex SUM integration in V8.46.

## Measured QA
- New test_v846_fir_native.py: 8/8 PASS:
  complex response parity; exact delay-dependent phase; same-snapshot
  native Mag/Phase coordinates; positive/negative source pixel Phase
  matching; wrong HWND/stale frame/wrong plot rejection; click-through
  existing plots; native source connected after the FIR worker;
  independent Mag PASS / Phase HOLD; layer disappearance on lost
  source evidence; worker-rendered real RGBA phase data.
- Full V8.28–V8.46 regression: 135/135 PASS (37.00 seconds).
- FIR-only Qt OFFSCREEN redraw benchmark, 40 frames per plot:
  MagFIR P95 0.96ms, PhaseFIR P95 2.04ms.
  Earlier pre-raster PhaseFIR P95 was 49.59ms, and is NOT accepted.
- Python compileall PASS. Git diff --check PASS.
- Smaart original audio and TRF files were never modified.

## Explicit NOT VERIFIED / next acceptance
- Smaart.exe was not running. Real single Trace tick, both original
  native pixel fits, X/Y pan/zoom, physical drag smoothness and native
  PhaseY 360-degree assumption still need live validation.
- Current registration uses standard 20–20k log X; arbitrary zoomed
  Smaart X axis must fail closed until separate X-axis verification
  exists. No 33.33ms end-to-end live mouse-to-present claim.
- Source pixel correlation is a strong independent visual check, but
  does not cryptographically prove the Data Bar archive_order label.
  Saved Smaart Fs may be stale relative to a live unsaved Fs change.
- For real use, if native match fails MagFIR/PhaseFIR is hidden
  rather than drawn with guessed geometry. TXT/WAV offline export
  remains protected by V8.45 exact source token/Fs/SHA checks.
