# RemiX Signal Auto Phase V8.29 — Native Phase Y gesture fix

Date: 2026-10-30 — Admin-PC / real Smaart Suite
Active QA source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA

## Root cause

In `overlay_v7.py`, `_check_phase_axis_drag(target)` existed but was never called by the 33 ms Qt tick. Consequently SUM Phase was dependent on deferred relative native pixel correlation and 850 ms absolute REF calibration. Real ruler drags could leave the SUM Phase visually stationary until a later successful native fit.

## Changes

- Wire Phase ruler gesture check into live Qt tick before pan jobs.
- Non-blocking press/move/release tracking: display-only signed pixel Y shift for SUM Phase.
- Do not double-count native relative Phase pan while an explicit ruler drag is active.
- On release invalidate previous absolute and relative callback generations, then allow a fresh Smaart-native REF fit to reconcile the true viewport.
- Maximum acceptable absolute frame latency 550 ms, protected by generation checks.
- Idle absolute Phase fit interval 850 -> 450 ms.
- No modifications to source H(f), SUM math, coherence, delay, DSP, Smaart stored .trf, Generator or soundcard.
- SUM Mag unchanged in logic.

## Evidence

- 31/31 pytest PASS after changes, including real gesture callback unit tests and previous SUM/Y tests.
- Actual Smaart application, 1920 x 1040 desktop, ruler drag 36 px then return.
- Two GUI desktop screenshots:
  `_qa_phase_gui_drag_down.png` and `_qa_phase_gui_restored.png`.
- Independent pixel mask cross-correlation on cropped Phase area:
  SUM green drag-to-return shift = -36 px, normalized overlap 0.928488.
  Native blue over same frames shift = 0 px, overlap 0.911144.
  These frames prove *immediate SUM preview follows pointer*; Smaart itself
  had not displaced its original blue trace between those particular captures.
- After a separate pre-patch real interaction, Smaart Phase native axis changed
  while SUM Phase remained in old position in immediate screenshots.
- `V829_PHASE_GESTURE_BEGIN` and `V829_PHASE_GESTURE_RELEASE` code paths
  wired; GUI preview pixel test supports that the callback now executes.
- Smaart UI became minimized while another session was using Admin-PC; UIA
  then reported `(-32000,-32000,...)`. Plot discovery returned None and
  correctly failed closed. Do not treat it as a new permanent plot role defect.

## Remaining HOLD

- Exact final native Phase-axis parity after Smaart commits its viewport
  repaint needs a controlled uninterrupted GUI session. No proof of final
  phase Y alignment after wheel, zoom, ruler drag and full 360-degree wrap.
- The green preview is not native TF data and does not prove live H(f) stream.
- Do not mark full Phase/Mag SUM parity as commercial/production PASS.

## Process and rollback

Production/stable V8.25 remains preserved. V8.27 source is the live QA source.
Restart ONLY its exact pythonw wrapper/child, never Smaart or other apps.
Use `restart_exact_v828.py` in this directory and verify PID/CWD anew.
Previous Git checkpoint: 33b596b. Keep unrelated root work uncommitted.
