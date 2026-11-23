# V8.147 regression guard + full RemiX brand — 2026-11-14

## Change

- Active license badge is now `RemiX Duo · ACTIVE`, not `Duo · ACTIVE`.
- Windows ToolHub brand strip grows from 122 to 250 px toward the left. The
  native Auto Phase/EQ/FIR row keeps its existing position and width.
- Shared macOS overlay bar grows from 336 to 410 px so the full brand and all
  three tool buttons are not compressed.
- Inactive/fail-closed badge remains `RemiX Duo`; license key material is not
  displayed.

## Regression evidence

- Required `VERIFY_ACTIVE_BUILD.py`: **HOLD**, not PASS. The prescribed venv
  points to removed `C:\Users\Admin\...\Python311\python.exe`.
- Provenance mismatch: `ACTIVE_SOURCE.txt` says
  `windows_v8_84_LOGIC_FIX_QA`, while the verified running/development source
  is `windows_v8_87_MAC_OVERLAY_QA`. No active-source file was silently
  rewritten by this task.
- Pre-change default shared/contracts: 114 PASS, 4 SKIP in 14.72 s.
- Pre-change isolated root legacy/Qt sweep: 129 files = 122 PASS files,
  7 no-test probes, 0 FAIL.
- TDD RED: active badge and shared overlay brand tests failed before source
  change (2 expected failures).
- Post-change focused brand/license/overlay/platform: 21 PASS in 2.14 s.
- Post-change default shared/contracts: 114 PASS, 4 SKIP in 13.67 s.

The four skips are missing reference TRF fixtures and were already known.
No Generator/Sweep, audio route, Smaart data, DSP, secret or license server was
changed. Controlled cutover restarted only the Duo overlay and watcher. Native
Smaart-window screenshot then visibly showed `RemiX Duo · ACTIVE`; live brand
acceptance is PASS.

## Runtime at audit

- Running overlay source: `windows_v8_87_MAC_OVERLAY_QA`, PID 35380/13144.
- Autostart watcher: PID 19020/34948.
- Smaart PID 39912 remained running and was not stopped or controlled.

