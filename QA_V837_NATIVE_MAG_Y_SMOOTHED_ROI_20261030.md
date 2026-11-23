# RemiX Dou — V8.37 native Magnitude Y and LF–HF visibility repair
Date: 2026-10-30 / Admin-PC

## Original symptom
For Smaart two selected traces "boh p5" and "sub p5", Phase SUM and
Phase crossover LF/HF still displayed but Magnitude SUM and highlight
disappeared. The Mag overlay stated "SUM MAG: Y CHUA XAC MINH (NATIVE MATCH)".

## Reproduced root causes (READ ONLY)
1. overlay_v7.SumGraph.paintEvent returned immediately before drawing ROI
   whenever require_native_axis and not native_axis_ready. This hid the
   independent LF–HF frequency-only highlight, plus the unverified SUM Mag.
2. The original native MAG matcher supported only cyan, blue, red; Smaart
   traces here are magenta/gold in the Magnitude graph.
3. Stored raw TRF magnitude is not the same as Smaart's displayed
   fractional-octave-smoothed curve. This Smaart view is 1/6 octave.
4. On live PrintWindow (1920x1040, Mag plot 252,539,1442,412):
   boh p5 raw + magenta score 0.416 (rejected);
   boh p5 1/6-Oct smoothed + magenta score 1.000 (accepted);
   sub p5 gold 1/6-Oct score 0.712 (not accepted).
   One securely matched source is enough to calibrate the shared Y axis,
   but source ambiguity still rejects all outputs.
5. Original strict native matcher reported "No verified native MAG source
   match" and the early QPainter return hid the ROI.

## Focused changes
- overlay_v7.py: draw the LF–HF X-only crossover highlight before
  gating unverified SUM Mag. Do not render any untrusted SUM amplitude.
  Phase rendering, cached SUM bitmap, Y-panning and AutoEQ paths unchanged.
- smaart_native_mag_fit.py: add explicitly selected magenta and gold
  pixel masks; existing cyan/blue/red are identical. Native AutoEQ color
  selection preference list is not changed.
- mag_sum_native_v826.py: match stored TF using independently verified
  original and display-only smoothed Magnitude (1/6, Off, 1/12, 1/3 octave),
  against only the visibly present native colors. Preserve strict
  per-fit >=.82 score, unique source margin >=.08, and fail-closed
  insufficient/ambiguous fit logic. Do not change H(f), gain or delay.
- test_v837_native_mag_roi.py: three focused tests covering
  LF/HF while native Y is unavailable, accepted smoothed single-source
  match and rejection of ambiguous source identity.

## Acceptance evidence
- Live read-only capture with boh p5 / sub p5:
  accepted=True, score=1.0, source_index=0, color=magenta,
  native Y_min=-25.108 dB / Y_max=+10.892 dB,
  inferred smoothing=0.166667 Oct, worker 701.57 ms.
- Full focused integration suite: 80/80 PASS.
- Qt offscreen 4096-bin/40-frame P95: Phase 2.22 ms, Mag 2.17 ms;
  this is NOT mouse-to-display real-time latency.
- No DSP SET, no soundcard/Generator/Smaart configuration modification.
- Previously dirty docs and V8.34 PNG files remain untouched.

## Remaining live UI acceptance
After an exact owner-controlled companion restart, verify that current
two selected Smaart traces show the green SUM Mag and Mag LF/HF highlight,
without losing Phase SUM/ROI. Verify native Y source match when moving
Smaart's real Magnitude ruler; gate must recover or HOLD without
inventing viewport shifts. 8.34 drag-to-present P95 remains separate HOLD.

## LIVE GUI ACCEPTANCE — PASS (2026-10-30 23:43 local)
- Exact source restarted, Git HEAD 7be369b, no independent AutoEQ instance.
- RemiX child PID 9548, wrapper PID 4928; Smaart PID 18904 remained alive.
- Screenshot: QA_V837_LIVE_AFTER_SCREEN.png (1920x1080, actual Smaart).
- Active source "boh p5" and "sub p5" verified in Auto Phase panel.
- Native Magnitude reports "SUM MAG NATIVE Y | MAGENTA 100%".
- Green SUM Mag is visible in Smaart Magnitude plot.
- LF–HF turquoise highlight and border markers visible in BOTH Phase
  and Magnitude. Magnitude caption CROSSOVER 60–338 Hz present.
- Auto Phase SUM/controls remain visible. No Smaart config, Generator,
  or DSP data was modified.
- LIVE VISUAL PASS for original disappearing-SUM/ROI defect.
- Physical mouse-to-screen large-drag P95 remains a separate HOLD.
