# RemiX Dou V8.39 — Smaart native 0 dB Y-grid calibration

Date: 2026-10-30 / Admin-PC
Worktree: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting git HEAD: c5cb66f

## Why V8.37 still failed
With pair "sub p5" / "foh p5", SUM Mag was again hidden behind
"SUM MAG: Y CHUA XAC MINH (NATIVE MATCH)" while the Smaart native
Magnitude curves and frequency-only LF/HF ROI were visible.
V8.37 calibration accepted only an unambiguous stored-TRF vs original
pixel-curve match. This is fragile for clipped LF bands, differently
smoothed curves, varying colors, and source views.

Further QA on a saved real Smaart screen established that a 100%
magenta source match had yielded axis Y -25.108..+10.892 dB, while
independent native grid evidence reported -20.957..+14.870 dB.
That is a ~4.1 dB axis-placement discrepancy even when the matcher
reported 100% source agreement. Therefore a matched source curve
should NOT be authoritative for absolute native Magnitude Y.

## New primary Y calibration: native pixels, no curve matching
- Read original Smaart HWND with existing read-only PrintWindow.
- Locate the unique bright neutral interior horizontal 0 dB baseline.
- Detect multiple periodic native gridlines in the same Magnitude ROI.
- Verify spacing is consistent with the 0 dB baseline (>=80% agreement,
  <=2.4 px residual, 5+ independent lines, reasonable grid pitch).
- Read only the dB-per-grid interval from the saved visible Magnitude
  plotProperties; in this Smaart profile, 3 dB/div. Do NOT use saved
  axis min/max/center (which can be stale after Y-pan).
- px_per_db = measured_grid_step_px / saved_grid_interval_db.
- y_max = measured_zero_line_px / px_per_db;
  y_min = y_max - native_plot_height / px_per_db.
- Reject if zero baseline is absent/ambiguous, grid is inconsistent,
  interval unknown, or resulting span is out of bounds.
- On a valid grid fit, source_index=-1 / color=GRID (no false claim of a
  matching trace). Only if grid verification fails, use V8.37
  confidence-gated stored-TRF native pixel matcher.
- Both routes are background worker operations. No changes to
  complex SUM H(f), DSP, delay, physical soundcard, generator, TF
  smoothing algorithms, Phase drawing, or LF-HF independent highlights.
- Native axis label now identifies "0 dB GRID" distinctly from
  MAGENTA/RED trace matching.

## Reproducible QA
- Original Smaart screenshot: QA_V837_LIVE_AFTER_SCREEN.png
  Native plot: (252,539,1442,412) at 1920x1080.
  Native 0 dB line: pixel 171 from top.
  Grid spacing: 34.5 px; saved interval: 3 dB.
  Native Y: -20.9565..+14.8696 dB.
  Pure source-independent confidence: 100%.
- The user-provided second screenshot was analyzed read-only:
  zero baseline likewise at +171px and visible ~34-35px grid steps.
  A stray grid candidate is tolerated by lattice agreement gating.
- Added test_v839_native_mag_grid.py: seven cases covering
  observed screenshot, no-curve synthetic image, missing/ambiguous
  zero line, missing interval, grid-first priority and safe fallback.
- Full focused regression, V8.28-8.39 and AutoEQ V0.19:
  93/93 PASS.
- Qt offscreen paint 4096 bins / 40 frames:
  Phase P95=1.49ms, Mag P95=1.32ms.
  Not a physical Qt mouse-to-present benchmark.

## Limitations and safety
- The saved 3 dB grid step may lag unsaved live changes to Smaart's
  "dB per division". Zero-line and grid pixel locations are read
  live, so vertical offset, native Y-pan and Y zoom are measured fresh,
  but if the operator changes the grid interval without saving, the
  derived dB scale can be wrong. Do not claim absolute guarantee.
- Smaart was minimized during this session's latest live capture
  attempt: physical two-trace screen acceptance HOLD until it is
  visible in the intended UI; do not silently unminimize it.
- Repo contains dirty records and QA PNGs owned by other sessions:
  preserve all, never stage them.
