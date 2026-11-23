# RemiX Dou V8.55 - AutoEQ shelf-selection crash fix

Date: 2026-10-31; Windows Admin-PC.
Canonical repo: D:\REMIX_AUTO_ALIGN_V6_DEV
Source tree: windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline HEAD: 61f72b5 (V8.53 present).

## Reported bug
Auto EQ for Smaart TUNNINNGGG-7.trf at 48kHz, Flat,
LF 60Hz, HF 8kHz, Max PEQ 8, Cut -9dB, Boost +2dB
failed with error: "Original RemiX solver returned unsupported/out-of-bounds PEQ".

## Root cause proven with original read-only TRF
Unified AutoEQ yielded PREVIEW_READY with 6 filters:
P at 87.45Hz, -5.92dB/Q3;
LS (LOW SHELF) at 100.62Hz, -1.78dB/Q3;
P at 282.85Hz, 487.92Hz, 1612.99Hz and 77.76Hz.
RemiX Dou AutoEQ adapter is PEQ-only, so it correctly rejected LS.
The unified AutoEQProfile contained max_low_shelf and max_high_shelf,
but detect_broad_shelf_candidate ignored these two controls.
The failure depended on target/ROI/cut: with Cut -12dB the solver
did not select a shelf and the user saw an EQ preview.

## Narrow source fix
engines/remix_autoeq_unified.py:
  detect_broad_shelf_candidate now respects max_low_shelf > 0
  and max_high_shelf > 0.
remix_autoeq_v05_adapter.py:
  Explicitly sets both max_low_shelf=0 and max_high_shelf=0
  for RemiX Dou AutoEQ only.
The unified engine's defaults remain 1 / 1, preserving external
features that deliberately want low/high shelves.
All original fail-closed PEQ type/Q/gain checks remain intact.
No silent LS -> PEQ conversion, no dropping a shelf from an
unmodified response, no weakening source/mag/export verification.

## Read-only verified outcomes
TUNNINNGGG-7.trf, Flat, LF60/HF8000, Cut -9dB, Boost +2dB:
PREVIEW_READY, 6 PEQ, WRMS 5.954 -> 5.067dB.
Bands:
- 85Hz -8.98dB Q3
- 283Hz -5.19dB Q8
- 488Hz -4.34dB Q8
- 1613Hz -4.76dB Q6.5
- 105Hz -4.5dB Q8
- 190Hz -5.5dB Q8
No PEQ centers within 1/4 octave, no gain outside Cut/Boost.
Exact 48kHz cascade vs reported MagEQ error <2e-15dB.
TUNNINNGGG-8.trf also PREVIEW_READY, 5 PEQ, WRMS 5.086 -> 3.770dB.
TUNNINNGGG-9.trf also PREVIEW_READY, 6 PEQ, WRMS 5.082 -> 3.979dB.
All tests read original user TRFs only, never modify Smaart.

## QA boundaries
test_v855_peq_only_shelf_rejection.py guards real 7/8/9 TRFs,
explicit shelf budgets and exact MagEQ/PEQ frequency/Q/gain parity.
64/64 focused regression PASS including V8.53 transient source gates.
Full regression outcome appended after execution.
No audio, DSP, soundcard, generator, sweep, saved Smaart config or
original TRF changes.

## Live acceptance
Recompute Auto EQ on the same single tick after companion restart
to replace old in-memory failure state. This proves the solver
computation; continuous no-flicker native MagEq still requires
separate live mouse/viewport acceptance.

## Final QA closure
- Full selected V8.28–V8.55 + V8.53 regression: **213/213 PASS**, 93.82 seconds, process exit 0.
- Qt marker drag fixture is isolated against real concurrent Smaart scanning. Dedicated V8.53 tests retain actual transient-tick protection.
- compileall 0, git diff --check 0.
