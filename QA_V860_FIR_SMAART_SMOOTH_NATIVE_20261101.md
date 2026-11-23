# RemiX Dou V8.60 - native FIR plots with Smaart smoothing parity

Date: 2026-11-01. Admin-PC Windows.
Canonical repo: D:\REMIX_AUTO_ALIGN_V6_DEV
Source: windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline HEAD: 32e09d2.

## User incident
FIR panel shows a ready 1024-tap linear-phase design, Fs 48kHz and
latency 10.66ms, but both MagFIR and PhaseFIR show HOLD and no
predicted FIR traces are visible on the original Smaart plots.
The FIR design/complex response is intact; native plot registration
was failing. No audio output or DSP writing was involved.

## Root cause proven with real native pixels
Smaart's saved visible magnitude/phase smoothing is 1/6 octave.
The FIR native color-registration matched UNSMOOTHED original TRF
magnitude against the SMOOTHED Smaart display.
Original blue magnitude fit score: 0.527, ambiguous, rejected.
Same source after 1/12 octave smoothing: score 0.746.
Same source after 1/6 octave smoothing: 1.000, accepted.
Native Smaart MAG role/title and 0dB/grid were independently
detected; phase pixel-registration score 0.970.

## Production code fix
fir_native_v846.py only:
- Read the saved visible Smaart smoothing snapshot; fail-closed on
  unsupported/ambiguous MAG smoothing.
- Use smoothing of original MAG only for original-source pixel
  registration, and smoothing of FIR predicted MAG only for the
  visible preview raster. FIR coefficients, H complex, source
  magnitude and phase processing remain mathematically unchanged.
- Confirm unchanged smoothing snapshot during registration.
- If phase smoothing differs from the verified 1/6-octave
  phase model, MAG remains available but PhaseFIR stays HOLD.
- Add verified blue/green/etc source-color fast path; reuse only
  last validated geometry + color, on NEW PrintWindow pixels.
  Previous Y/phase fit/overlay raster is NEVER reused as proof.
- Any change in window size, plot heading, original-source token,
  visible smoothing, or color forces full fresh registration or HOLD.
- The coordinator may retain a past validated frame strictly as
  a candidate for native role geometry; it is never painted when
  the 0.45-second fresh-frame gate expires.

## Real Smaart read-only acceptance, TUNNINNGGG-9
- Smaart HWND 88082526, 1920x1040, visible and not iconic.
- FIR 1024 taps, native Smaart 48kHz.
- Three full native frame captures: 0.69-0.95s each; accepted
  original MAG blue 100%, original Phase 97%, both rasters created.
- Eight repeated full/fast captures:
  full 0.922s, fast 0.422-0.687s.
  All frame validity, original source hash and MAG/Phase pixel
  registration accepted when returned.
- Each 1442x412 raster = 2,376,416 bytes; no UI painting
  from the FIR worker.
- The worker can still exceed 0.45s occasionally; HOLD when
  native evidence expires remains a safety requirement. Continuous
  non-flickering 30-60s GUI acceptance is not yet proven.

## QA
- New test_v860_fir_native_smaart_smoothing.py: new smoothing,
  fast path, source/geometry mismatch, unreliable settings,
  independent Phase HOLD and displayed MAG domain.
- Focused FIR group: 20/20 PASS.
- Selected V8.16-V8.60 full regression: 255/255 PASS, 71.22s.
- Python compileall PASS. git diff --check PASS.
- No soundcard, Smaart audio, Generator, Sweep, DSP or TRF mutation.
