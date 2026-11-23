# RemiX Dou V8.51 — direct PEQ-marker XY drag on Smaart Magnitude

Date: 2026-10-31 / Admin-PC.
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline V8.50 HEAD 4fcf5f7.

## Feature
- Each MagEQ marker has a tiny 30 x 22px transparent no-focus
  interactive grip. All other graph pixels stay click-through.
- Drag LEFT/RIGHT changes Frequency via log 20–20000Hz X; drag
  UP/DOWN adjusts Gain using fresh native Mag Y px-per-dB.
- Q is unchanged. Frequency cannot cross the current EQ LF/HF range,
  or come closer than 1/4 octave to any other center.
- Gain is clamped to current user Boost/Cut.
- Every mouse move regenerates exact PEQ biquad cascade prediction,
  updating MagEQ while preserving source identity and source revision.
- No original Smaart TF, Transfer Function, Fs or hardware mutated.
- Start requires unexpired pixel-verified source and original TRF SHA.
  Move/end require fresh verified source binding and viewport.
- Export EQ is disabled during drag and its snapshot regenerated
  on release; source/native gates still apply to actual export.
- Auto Phase/FIR switch, HIDE and loss of native registration
  remove the grips. No graph-wide mouse interception.

## QA
- test_v851_peq_drag_native.py: 8/8 PASS, including:
  Hz/Gain from mouse movement, unchanged Q, 1/4-oct clamp,
  LF/HF and Boost/Cut bounds, exact biquad parity, small Qt
  mouse press/move/release, no focus, native graph positioning,
  tool-mode hide and one Trace/native/export gating.
- Full V8.28–V8.51 selected regression: 177/177 PASS, 35.37s.
- Python compileall PASS, Git diff --check PASS.
- No DSP, Generator, sweep, original .trf, audio device or Smaart
  configuration writes.

## Live acceptance HOLD
Qt/offscreen simulated marker and frame tests PASS. Real Smaart
physical pointer drag / Y pan-zoom still require interactive live
verification with one tick, approved MagEQ and stable source pixels.
No false claim of real physical Smaart GUI acceptance.
