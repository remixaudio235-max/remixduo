# RemiX Dou Auto Phase V8.36 — native signed Y recovery QA (2026-10-30)

## Ownership and safety
- Same repository / branch / active source as V8.35 handoff:
  `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA`.
- Starting HEAD: `cd66e76`; rollback tag:
  `checkpoint/remix-dou-v835-new-chat-handoff-20261030`.
- Live overlay process at entry: pythonw wrapper PID 5004, child 4044;
  Smaart PID 20372 (responsive at entry). PIDs must be rechecked.
- No changes to .trf, soundcard, generator, Smaart binaries, DSP, AutoEQ,
  LF/HF ROI, overlay SUM raster, or other sessions' dirty documents/images.
- Real drag QA remains HOLD: the Smaart window became minimized while
  checking the desktop; no attempted drag against a minimized target.

## Reproduced algorithmic defect (read-only source image)
- Used the existing V8.35 native Smaart image
  `V835_CROSSOVER_LIVE_QA.png` as the source, shifted the image ROI
  vertically in memory (not a real Smaart UI gesture).
- Phase -30/-65px: half-region 1D row-density correlation was biased by
  roughly 10px relative to the real translation; the original +/-4px
  2D refinement missed the true shift. The frame failed verification.
- Phase +10/+35/+65 and Mag -65/-30/+10/+35/+65 were not broken.

## Focused fix
- `native_fast_pan_v81.py`: retain the original narrow 2D fast path;
  only if two halves disagree, confidence is weak, or the quick candidate
  is ambiguous, try a wider +/-12px high-confidence common 2D alignment.
- Require >=0.85 per-half native mask score for recovery.
  Green-only overlay movement still cannot prove a Smaart-native pan.
- Preserve the 89px per-frame cap, signed Y transform, epoch/latest-only
  protection, data H(f), and all V8.34/V8.35 Qt cache/crossover drawing.
- Regression tests: `test_v836_signed_pan_fallback.py` (13 cases).

## Measured result, offline only
- Targeted pytest regression including V8.28–V8.36, trace selection and TF:
  **52/52 PASS** (2026-10-30).
- Replayed signed image shifts Phase -65,-30,0,+10,+35,+65 and
  Mag -65,-30,0,+10,+35,+65: 12/12 correct within 1px.
- Synthetic green-only SUM motion rejected.
- Fast native correlation (100 iterations per case):
  Phase +35 P95 3.96ms; Mag -65 P95 3.48ms;
  recovery Phase -65 P95 8.49ms.
  These are offline correlation timings, NOT native GDI capture-to-present.
- Qt offscreen 4096 points / 40 frames:
  Phase paint P95 1.42ms, Mag paint P95 1.68ms.
- Existing V8.34 no-ghost comparison from currently dirty screenshots:
  native red IoU=1.000, SUM green IoU=1.000 (Mag PRE vs PEAK);
  **stationary native input is not a positive pan acceptance**.

## Still HOLD
- Actual Smaart source trace moves with real Phase/Mag Y-axis drag,
  matching SUM pixel movement and reversal under continuous large drags.
- Mouse-to-screen P50/P95, wheel pan and +/-360 wrap under real UI.
- Never equate viewport Y-follow with live complex H(f) streaming.
- Restart and live acceptance must be performed only with Smaart
  visible/foreground and the exact overlay owner revalidated.
