# RemiX Dou Auto Phase V8.32 — LF/HF dragging in Magnitude

Date: 2026-10-30 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA

## Reproduced cause
Previously two ROILineGrip windows existed only for plot_layout.phase.
Phase LF/HF dashed vertical lines had a 17 px draggable transparent
Qt input surface. Magnitude displayed the same LF/HF line positions but
had no mouse-target window, so horizontal dragging from Mag could not
update LF/HF. Screenshot red annotations identify the two vertical LF/HF
positions in Mag.

## Fix
- Add independent mag_roi_line_grips LF/HF (same Qt ROILineGrip class)
  with source_plot='mag' callbacks.
- Use actual source plot x/width for x_to_hz, never assume Mag/Phase
  have identical geometry.
- Each Mag grip spans full Mag canvas height (zero top-label margin).
  Phase grips retain their previous 29 px top-label margin.
- The existing LF/HF QDoubleSpinBox remains the only truth: both plot
  guides/handle sets update together through on_roi_changed.
- Preserve normal LF/HF ordering, invalidating stale Top3 result after
  ROI changes, and no alteration of SUM complex TF / DSP / ASIO.
- All 4 grips hide in AutoEQ/FIR/LIVE/HIDE, and are closed on App shutdown.

## Results
- Source py_compile and pytest 42/42 PASS, including new Mag and Phase
  press/move/release events, vertical strip geometry, changed plot widths,
  LF/HF crossing guard, ROI synchronization, and overlay mode hiding.
- Exact source application restarted: wrapper PID 19112 and child PID
  14784 (verify if revisiting, as Windows PIDs may change).
- Live Win32 WindowFromPoint hit-test was attempted; process failed
  closed at the focus preflight: HOLD_FOCUS_NOT_SMAART.
- Separate inspection: Smaart HWND 5113162 is present/non-minimized at
  (0,0,1920,1080), but interactive foreground HWND was 0. No real
  mouse drag performed, so **native mouse hit acceptance remains HOLD**.
- Audio generator, soundcard and Smaart contents unchanged.

## Follow-up acceptance
When Windows foreground/Smaart GUI is available, run QA script
qa_v832_mag_native_hit.py (READ ONLY). It must return RemiX Pythonw
window owner at both LF/HF coordinates in both Phase and Magnitude.
Then physically drag Mag LF from e.g. 60 to 90 Hz and Mag HF from
200 to 400 Hz, confirm changes in both graphs, and test overlap guard.
Keep V8.25 baseline unchanged.
