# RemiX Dou V8.59 — EQ5 frequency/Q residual-shoulder fit

Date: 2026-11-01, Windows Admin-PC.
Canonical repository: D:\REMIX_AUTO_ALIGN_V6_DEV
Source: windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline: V8.58 Git HEAD 88ba1a7.

## User report / evidence
Smaart screenshot of TUNNINNGGG-9 shows an EQ5 marker at the
broad ~100–110 Hz response hump but the yellow post-EQ trace has
an uncorrected shoulder left of the selected EQ center.
Current preview was PREVIEW_READY 5 PEQ and WRMS 5.11 -> 4.21 dB.

Exact read-only solver reproduction from original TUNNINNGGG-9.trf:
Fs48000, Flat, LF60Hz, HF7900Hz, MaxPEQ8, Boost+2dB, Cut-9dB.
- EQ5 = 108.95Hz / -5.50dB / Q8
- Original measured/predicted source peak at 110.61Hz.
- Post-EQ peak at 96.78Hz remains +2.531dB above target.
- EQ5 center itself is -0.813dB vs target.
- Weighted RMS 5.10768 -> 4.20723dB.
Thus the issue is too-narrow cut/left shoulder, NOT an EQ
marker that was mapped to the wrong source or viewport.

## V8.59 code
- New autoeq_peak_shape_v859.py refines only a NEW high-coherence
  cut PEQ from the V8.52 residual cleanup, after the core solver,
  V8.49 rescue and V8.50 spacing validation.
- Jointly search Frequency/Gain/Q while protecting high-coherence
  existing dips, P90/worst error, weighted RMS, Q3–8, Cut/Boost,
  original ROI, and 1/4-oct center spacing.
- Minimize local peak + excessive cuts across the *positive-residual
  island* — not simply fit the frequency of its highest point.
- Baseline must have meaningful >2dB residual shoulder and final
  choice must improve it >=0.70dB; otherwise leave PEQ untouched.
- New algorithm does not alter the original trace, other filters,
  native MagEQ renderer, Fs, source identity, export controls,
  Smaart, soundcard, DSP or generator.
- autoeq_q_policy_v852.py wires in the shape refinement without
  changing the PEQ count. Warning bookkeeping uses actual number
  of added filters, not number of warning strings.

## Exact real measured A/B results
OLD: EQ5 108.95Hz / -5.50dB / Q8.0.
NEW: EQ5 105.68Hz / -5.50dB / Q6.0.
Residual max 92–119Hz: +2.531dB -> +1.222dB.
Residual local min after: -1.089dB (no deep new dip).
WRMS: 4.20723 -> 4.23100dB; delta +0.024dB, within guard.
All 5 PEQs retain Q3–8, Gain within -9 to +2, spacing >=0.25 octave.
Exact MagEQ response versus cascade error 1.78e-15dB.
Original TRF SHA unchanged. Preview and DSP writes are separate.

## QA
- New test_v859_peak_shoulder_flatten.py: real TRF EQ5, exact
  frequency/Q/response/spacing/immutable source; unreliable
  coherence fail-closed; related TUNNINNGGG-7/8 parity.
- Focused V8.49–V8.59 set: 48/48 PASS (54.30s);
  Python compileall 0.
- Full regression and live GUI outcome recorded separately.

## Full regression closure
- Selected V8.16–V8.59 full regression: 248/248 PASS (55.57 seconds), process exit 0.
- Python compileall PASS and Git diff --check PASS.
- Live Smaart marker/viewport acceptance is separate from this read-only calculation regression.
