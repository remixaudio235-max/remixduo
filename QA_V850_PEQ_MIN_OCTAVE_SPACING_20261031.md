# RemiX Dou V8.50 — safe minimum PEQ center spacing (1/4 octave)

Date: 2026-10-31. Admin-PC, Windows.
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Base HEAD: 3ba719f (V8.49).

## User reproduction and requirement
Two live Smaart screenshots of TUNNINNGGG-9 show multiple Auto EQ
markers and PEQ filters near 100 Hz, visually obscuring one another and
producing overlapping corrections. User requested real safe frequency
separation, not marker-only reformatting.

Reproduced with ORIGINAL Smaart TRF at 48 kHz, Flat, max 8 PEQ,
Boost +2 dB and Cut -9 dB:
- ROI 60–10730 Hz: 98.7/110.4 Hz gap 0.1609 octave (< 0.25).
- ROI 83–6870 Hz: 96.7/106.0/112.9 Hz gaps 0.1330 and 0.0909 octave.
- ROI 75–2440 Hz: 417.9/481.3 Hz gap 0.2036 octave.
- Band center frequency ratio must be >=2^(1/4)=1.189207.
  Example after a PEQ at 100 Hz, next must be >=118.92 Hz.

## Implementation
- New autoeq_spacing_v850.py, separate from original unified solver.
- Runs AFTER V8.49 residual peak rescue, so every final plan meets the
  same hard spacing gate, including proposals from peak rescue.
- Group adjacent close centers on log2 Hz, merge each overlapping
  cluster into ONE PEQ. Evaluate real 48-kHz biquad response and
  weighted error on the immutable canonical analysis grid.
- Search center restricted to cluster, various bounded Q and gain;
  same-sign cut clusters cannot become boosts. Protect neighboring
  dips, guard P90/worst error and avoid unbounded global degradation.
- Fail closed on no safe separated solution. Never publish a silently
  overlapping EQ plan; after passing gates, exact complex cascade
  regenerates MagEQ, visible PEQ markers and Export EQ consistently.
- User's Max PEQ 8 is an upper bound, not a mandate to fill all 8.
- No new UI controls or changes to Smaart measurement, TF or DSP.

## Verified on the ORIGINAL TRF, no device writes
ROI 60–10730 Hz:
- 8 -> 7 PEQ; 98.7/110.4 Hz merge to 106.33 Hz, -5.9 dB, Q10.
- Weighted RMS old 3.952 -> new 3.947 dB; no remaining close pair.
ROI 83–6870 Hz:
- 8 -> 6 PEQ; triple 96.7/106/112.9 Hz -> 106.02 Hz,
  -4.71 dB, Q10.
- Weighted RMS old 3.992 -> new 3.997 dB (delta +0.005);
  no remaining close pair.
ROI 75–2440 Hz:
- 8 -> 7 PEQ; merge 417.9/481.3 Hz to 481.3 Hz, -4.39 dB, Q12.
- Preserve the V8.49 rescue 189.01 Hz, -6 dB, Q12.
- Weighted RMS old 3.264 -> new 3.276 dB (delta +0.012).
- Exact parity predicted Mag = source Mag + 20*log10(abs(cascade)).
- All outputs within Fs, LF/HF, Cut, Boost, and max PEQ limits.

## QA
- test_v850_peq_octave_spacing.py 15 cases:
  the two user screenshots, the old 190-Hz rescue,
  House target, 1–8 max PEQ, ratio-boundary and source SHA.
- Updated V8.49 tests to accept max PEQ as an upper bound.
- Full V8.28–V8.50 selected regression: 169/169 PASS, exit 0.
- compileall and git diff --check: PASS.
- Original TRF SHA unchanged; no ASIO, sweep, generator, physical DSP
  or Smaart configuration modified.

## Remaining live acceptance
Source code/regression and original TRF parity are PASS. Stable live
native Smaart MagEQ marker layout / 30–60s no-flicker / Y pan are
separate checks and must not be inferred from offline validation.
Restarting the companion resets its in-memory preview; calculate Auto EQ
again for current one verified tick before checking.
