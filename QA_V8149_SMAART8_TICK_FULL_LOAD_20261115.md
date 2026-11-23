# V8.149 Smaart 8 tick + UI/full-load QA — 2026-11-15

## Exact source and runtime

- Source: `windows_v8_87_MAC_OVERLAY_QA` (working tree, uncommitted).
- Smaart Suite remained PID 39912. Smaart 8 remained PID 26500.
- New overlay started after QA as PID 42584/34772; watcher remained
  31456/39792. Neither Smaart process was stopped.
- Required active-build guard: HOLD because its prescribed venv resolves a
  missing `C:\Users\Admin\...\python.exe`; `ACTIVE_SOURCE.txt` remains stale.

## Root causes and changes

1. `locate_smaart()` returned the first EnumWindows result when Suite and v8
   were both open. It now selects the foreground Smaart window, binding the
   observer to the correct edition and trace directory.
2. The Smaart 8 pixel reader rejected a real dark/desaturated green trace icon
   (`chroma < 40`), producing 8 rows for 9 files and a fail-closed HOLD. The
   icon-gutter threshold now admits dark colours; short Session Data folder
   glyphs are explicitly excluded.
3. Regression tests cover dual-edition foreground selection, dark trace icons
   and folder exclusion.
4. Current UI batch also contains the content-fit plot Toast, hidden redundant
   EQ/FIR subtitle rows, dynamic RemiX brand width and brighter/thicker yellow
   MagEQ curve with halo.

## Verification evidence

- Direct pre-fix native v8 capture: 9 TRF files, only 8 trace rows detected;
  missing row was the dark-green `full 30 bien.trf` icon.
- Focused v8/dual-edition/UI: **41 PASS, 1 SKIP**.
- Shared/contracts: **114 PASS, 4 SKIP**.
- Aggregate legacy run: **607 PASS, 49 SKIP, 34 FAIL** in 233.36 s. Failures
  are not hidden: most fixtures assume exactly one running Smaart edition and
  therefore receive no saved-Fs path while both v8 and Suite are live; one old
  Toast test expects a panel child although the accepted design moved Toasts
  to a plot-safe top-level tool. This aggregate gate remains HOLD.
- Read-only load: Suite PrintWindow 40 iterations, median 32.99 ms, p95
  34.49 ms, max 49.28 ms. Smaart 8 real-frame pixel parser 1000 iterations,
  median 16.466 ms, p95 34.371 ms, max 49.166 ms, stable row count 3/3.

## Native acceptance

- Suite read-only load: PASS; no Generator, routing, TRF or DSP write.
- Smaart 8 final live screenshot/re-probe: HOLD. During QA its main HWND
  disappeared while PID 26500 stayed alive (only hidden JUCE helper windows
  remained). Duo did not restart or terminate Smaart. Re-open/restore the v8
  main window, keep all trace rows visible, then verify the selected name and
  stable 3/3 status.

