# RemiX Dou V8.52 — Practical Auto EQ Q 3 to 8
Date: 2026-10-31, Admin-PC.
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline: V8.51 HEAD f28483a.

## User problem
A real Smaart overlay on TUNNINNGGG-9, Flat, 48kHz,
7 PEQ showed Q values 12, 11.43, 9.53 and 16.
User requests a practical 3–8 Q policy instead of ultra-narrow EQ.

## Production implementation
- Apply min_q=3, max_q=8 and max_resonance_q=8 to the
  RemiX Dou adapter's AutoEQProfile BEFORE solver optimization.
  Original shared engine defaults and other DSP products unchanged.
- Original V8.49 cut-only peak rescue and V8.50 quarter-octave
  spacing/merge are evaluated using the same constrained profile.
- Final Q hard validation applies to every generated PEQ.
  No post-hoc display/export-only clamping of Q.
- New autoeq_q_policy_v852.py optionally fills up to two spare PEQ
  slots to address coherent residual peaks left by the stricter Q cap.
  No extra slot beyond Max PEQ; candidates Q4–8, cut-only, 1/4-oct
  distance, source/quality gate, protect nearby dips; validate
  WRMS, P90, max error, and exact biquad-response parity.
  Do not force a narrow null or overcut to hide a residual peak.
- MagEq, F/G/Q labels, manual marker drag and export all
  use the final actual recomputed PEQ list. No DSP write.

## Read-only real Smaart TRF evidence
Source: TUNNINNGGG-9.trf, Fs 48000, Flat, Max 8 PEQ,
Cut -9dB, Boost +2dB, sampled three ROI windows.
- LF60 / HF10730: 6 PEQ, WRMS 5.082 -> 3.979 dB.
  Residual at 110Hz about -0.09dB, 190Hz about -0.78dB.
- LF83 / HF6870: 5 PEQ, WRMS 4.844 -> 4.063 dB.
  Residual at 110Hz about +1.66dB, 190Hz about -0.48dB.
- LF75 / HF2440: 5 PEQ, WRMS 3.949 -> 3.312 dB.
  Residual at 110Hz about +2.74dB, 190Hz about +0.44dB.
- All final filters have 3 <= Q <= 8, within user Cut/Boost,
  no centers closer than 1/4 octave, max PEQ budget preserved.
- Original TF source SHA untouched by read-only regression.

## QA
- V8.52 new focused tests check real three ROI, House/Tilt,
  Max PEQ 1–8, bounded Q, exact biquad MagEQ, exported EQ table,
  unmodified shared engine and source SHA.
- Full selected V8.28–V8.52 regression: 193/193 PASS (44.32s).
- Python compileall and git diff --check: PASS.
- Updated old tests that pinned obsolete exact 4/7/8 PEQ
  counts; replaced with dynamic count, safety invariants and
  actual response parity. Tests for 110/190Hz retain numerical
  peak acceptance checks.
- No Smaart generator, sweep, ASIO, DSP/preset, original TRF or
  audio routing altered.

## Live status
Calculation/regression PASS. UI changes in running companion
require restart/recalculation to replace old preview Q12/Q16.
Real physical Smaart dragging/pixel registration must be independently
verified. Do not claim live GUI acceptance from offscreen tests.
