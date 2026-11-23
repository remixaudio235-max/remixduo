# RemiX Dou V8.49 — AutoEQ rescue residual peaks with full PEQ budget

Date: 2026-10-31, Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline Git HEAD: 72bca32, branch qa/remix-signal-v825-checkpoint

## User reproduction
Screenshot: Flat, Fs 48 kHz saved Smaart, LF 75 Hz, HF 2.44 kHz,
Max PEQ 8, Boost +2 dB, Cut -9 dB, active TUNNINNGGG-9.trf.
AEQ original PREVIEW_READY, 8 PEQ, weighted RMS 3.949 -> 3.381 dB.
Strong residual near 189 Hz remains >+5.9 dB despite coherence ~0.97.
There was already a narrow ~107.69 Hz, -3.09 dB, Q16 PEQ, resulting
in approximately +0.62 dB remaining at 110 Hz. Do not overcut there.

## Root cause
The unified engine exhausted all eight slots on peaks around 107,
285, 339, 418, 481, 1417, 1527, 1921 Hz. The strong 189-Hz local
residual had NO PEQ. Expanding all filters or blindly increasing cuts
would worsen deep adjacent dips around 130-160 and 230-250 Hz.

## V8.49 change
New standalone deterministic adapter postpass in autoeq_peak_rescue_v849.py.
Does NOT modify original engines/remix_autoeq_unified.py or hardware.
Only accepts Flat, PREVIEW_READY and a fully occupied user-selected
PEQ budget. Finds remaining large high-coherence (>0.80), high-
reliability (>0.70) peaks not already assigned a nearby PEQ.
Tries one-for-one PEQ replacement across candidate centers,
Q=6-16 and cut limits, never raises number of filters and never
adds any boost. Each candidate must:
- Reduce weighted RMS by at least 0.04 dB.
- Reduce center peak error by >=3 dB and local neighborhood top by
  >=1.5 dB, center remaining within +/-1.6 dB.
- Preserve current P90 within +0.20 dB and worst error within +0.16 dB.
- Not worsen any trustworthy existing negative trough by more than
  0.75 dB (conservative tradeoff to flatten a +5.9 dB peak).
- Stay inside ROI, cut and max resonance Q, same original source.
Selected EQ response is exactly re-evaluated with the real complex
biquad cascade, ensuring native MagEQ, PEQ markers and Export use the
same final eight bands. Adapter recalculates final weighted RMS.

## Verified measured result on the user TRF
- PREVIEW_READY, 8 PEQ, same 48k and Flat target.
- PEQ8 changed from ~1416.79 Hz / -1.27 dB / Q16
  to **189.01 Hz / -6.00 dB / Q12**.
- WRMS 3.949 (before) -> 3.264 dB (after),
  versus baseline AEQ 3.381 dB (after).
- 189 Hz residual +5.92 dB -> -0.08 dB.
- 190 Hz residual approx 0.01 dB.
- Residual around 175-205 Hz remains <=~1.8 dB (not perfectly flat);
  at 110 Hz remains +0.67 dB (already near target).
- Original source .trf unchanged (SHA256 read-only test).
- Final EQ response parity with exact cascade: max difference <1e-7 dB.
- Candidate guard metrics and source identity tests PASS.

## QA
- test_v849_autoeq_residual_peak.py: 5/5 PASS.
- Full selected V8.28-V8.49 regression: 154/154 PASS in 14.23s.
- Python compileall and git diff --check PASS.
- No Smaart Generator, soundcard, original TRF, DSP, real-time
  audio, PEQ output device or preset was changed.

## Still HOLD
This is a code and offline real-TRF QA acceptance, not yet proof of
pixel-correct nonblinking live MagEQ in the user's current Smaart
viewport. Native source/viewport verification gates from V8.48 remain
mandatory. Restarting companion clears its in-memory AutoEQ preview;
user may need to click AUTO EQ again after selecting exactly one trace.
Physical/production DSP response remains unmeasured.
