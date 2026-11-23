# V8.25 — SUM Phase/Mag restoration on real Smaart (2026-10-30)

## Incident
- User screenshot: Auto Phase panel had Trace 1/2 + Top3; SUM Mag, SUM Phase
  and LF/HF guide lines were absent from live Smaart.
- Confirmed actual source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_25_BUTTON_ONLY_COMPACT_QA.
- Root cause 1: missing V812_MAG_TITLE_TEMPLATE.png and V812_PHASE_TITLE_TEMPLATE.png.
  Restored from V8.24 with SHA256 identical.
- Root cause 2: plot_role_v812.py used ImageGrab.grab(all_screens=False)
  (desktop screenshot). Any other foreground window could obscure Smaart
  chart headers, making role UNKNOWN, overlay_positioned=False; all SUM hidden.
- Fix: plot_role_v812.py uses read-only PrintWindow for the exact Smaart
  HWND. Convert UIA plot screen coordinates to HWND-relative for role
  detection; preserve screen-coordinate plot rectangles for Qt overlay.
- Previous source backed up as plot_role_v812.before_printwindow_fix_20261030.py.bak.

## Verified
- Native PrintWindow chart title matches: Phase 1.000; Mag 1.000.
- Live locate_role_plots => Phase (252,112,1442,398);
  Magnitude (252,553,1442,398), both valid.
- py_compile of plot_role_v812.py and overlay_v7.py PASS.
- 14/14 baseline tests PASS.
- Restarted exactly V8.25 overlay; Smaart remained active (PID 12796).
- Native EnumWindows: Phase Qt overlay 1442x398 visible and Mag Qt overlay
  1442x398 visible; ROI markers also visible.
- Actual desktop screenshot: V825_AFTER_ROLE_REPAIR_SCREEN.png:
  green SUM Phase, green SUM Mag, LF/HF, Phase Match, Trace 1/2 and Top3 visible.
- Button only remains compact 26px; panel unchanged.
- No audio/Generator/DSP action and no modifications to .trf.

## Remaining independent issues (NOT accepted here)
- Mag reads DISPLAY +30.8 dB provisional offset. This is not a measured
  acoustic or true native Smaart dB gain; Y calibration parity remains HOLD.
- SUM computed from stored TRF pair (snapshot), not a verified live complex
  Smaart TF frame stream. Real-time shape changes will not refresh via Smaart
  API until such a source adapter exists and is validated.
- Do not undo this role-capture fix when merging V8.26/AutoEQ branches.
