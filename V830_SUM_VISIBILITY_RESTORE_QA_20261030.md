# RemiX Signal V8.30 — Both SUM overlays hidden: actual GUI defect and fix

Date: 2026-10-30, Admin-PC, Smaart Suite, 1920x1040
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Git parent: 343c92e (V8.29 Phase ruler callback)

## Reported failure

Auto Phase panel still recognizes Trace 1 and Trace 2, but SUM Phase, SUM Mag
and LF/HF overlay lines are absent. No evidence that the DSP or complex SUM
equations failed.

## Verified root cause

Smaart UIA has two real chart canvases:
- Upper Phase: (250,82,1696,498), resulting drawable plot (252,84,1442,412)
- Lower Mag:   (250,537,1696,953), resulting drawable plot (252,539,1442,412)

The old plot_geometry_v7.locate_plots incorrectly required the lower panel
to start at >= 52% of the native Smaart window height. Actual lower canvas
starts at 537 px, slightly ABOVE the 540.8 px threshold. As a result
locate_plots returned None; locate_role_plots then also returned None,
and on_plot_layout(None) cleared overlay_positioned and hid both SUMs.
This was a viewport-geometry detection regression, not SUM TF math.

Manual native PrintWindow glyph confirmation on the actual GUI:
RoleScores: upper_phase=1.000, lower_mag=1.000, role=PHASE_TOP.

## Code changed

- plot_geometry_v7.py: detect vertically stacked matching native canvases
  using actual UIA dimensions, non-overlap, plot width, inset x and spacing;
  remove fixed 52% vertical split threshold.
- overlay_v7.py: one transient failed layout snapshot retains the previous
  confirmed plot for <=2.5 seconds ONLY if HWND and entire native window rect
  are unchanged. On minimize, move, resize, stale state, or expiry it
  invalidates overlays as before (fail closed).
- No changes to TRF loading/selection, native Mag axis fitting, complex SUM,
  Phase smoothing, Delay, soundcard, audio Generator, or Smaart files.

## Evidence

- Actual live Smaart UIA: both new plot rectangles verified.
- Actual native PrintWindow title role detection: both plot roles verified.
- 40/40 pytest PASS across layout-recovery, geometry, native-Y, gesture,
  TF, selection, EQ, MagEQ and export regression files.
- Exact source runtime restart PASS with new Pythonw PIDs 11660 / 18160.
- Native Smaart process remains healthy.
- Desktop capture: _qa_v830_sum_overlay_live.png
  clearly shows SUM PHASE MODEL + SUM MAG NATIVE Y | BLUE 95%,
  green SUM paths and LF/HF markers simultaneously visible.
- Selection panel displays the chosen two traces and their delays.

## Acceptance boundary

- Restored visibility of both SUM overlays on live Smaart GUI is PASS.
- Exact pixel tracking under continuous manual Phase Y drag, scroll/zoom,
  and post-release final alignment remains separate parity QA, not claimed.
- This source is an external overlay using saved TRF snapshots; it is not a
  confirmed real-time complex-TF data API.
- Other root repo edits from independent sessions remain untouched.
