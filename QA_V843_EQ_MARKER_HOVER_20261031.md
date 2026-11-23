# RemiX Dou V8.43 — compact Auto EQ markers / F-G-Q on hover only

Date: 2026-10-31 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting HEAD: f3ca37b, main branch qa/remix-signal-v825-checkpoint

## User problem
The previous renderer drew an F/G/Q rectangle for EVERY PEQ every paint,
obscuring MagEq and the original Smaart Magnitude curves.

## Focused implementation
- mageq_visual_v13.draw_markers now renders only a compact EQ1, EQ2,
  etc badge, anchored to the exact existing MagEq marker location.
  Markers still show reliability and use original colors.
- By default zero full-detail labels are painted. Only the nearest hovered
  visible marker draws a single F (Hz/kHz), G (dB) and Q popup.
- Added pure nearest-marker pixel hit test. Dense or adjacent markers
  deterministically choose the closest center; no stacked detail labels.
- Magnitude overlay stays click-through with existing
  WA_TransparentForMouseEvents, WindowTransparentForInput, and Win32
  WS_EX_TRANSPARENT | WS_EX_NOACTIVATE. No window grabs Smaart mouse input.
- SumGraph samples only the OS cursor position using QCursor every 75ms
  when an active MagEq source is registered. It checks native local
  coordinates and refreshes ONLY on a hover transition, not every poll.
  Hiding Auto EQ, changing trace/source or clearing MagEq clears hover.
  Hover interval sampling does not alter DSP, TRF or data synchronization.
- Gradient, MagEq curve, EQ ROI, single tick and max-PEQ semantics unchanged.

## QA
- test_v843_eq_marker_hover.py: 3/3 tests:
  nearest-only hover with dense adjacent PEQs; one tooltip only when
  hovered, disappears when cursor leaves; default no details;
  no redundant repaint while stationary; source clear stops timer;
  no details in other tool; asserts native click-through flags.
- Whole focused regression V8.28-V8.43 + AutoEQ: 117/117 PASS.
- Compileall and git diff --check: PASS.
- Three independent Qt offscreen paint runs (4096 bins / 40 frames):
  Mag P95: 1.44, 1.57, 1.45 ms.
  Phase P95: 1.40, 1.44, 1.76 ms.
  These are NOT measured physical mouse-to-display latency.
- No Smaart, soundcard, generator, DSP or TRF mutation.
- Existing unrelated dirty files preserved.

## Remaining live gate
Smaart.exe was not active at the first process check of this session.
After a controlled companion reload and when Smaart is visibly active,
hover EQ1/EQ2 with a real mouse to confirm popup follows the nearest
marker and does not intercept Smaart plot drags. Check dense 8-12 PEQs.
Do not call this gate PASS based solely on Qt offscreen tests.

## Known separate safety HOLD
Earlier audit P0 about Data Bar row-to-TRF identity proof and export
authorization is NOT repaired by a marker layout change. Keep this
distinct from the approved V8.43 presentation work.
