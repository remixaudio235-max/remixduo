# V8.152 Smaart crash/UIA serialization QA — 2026-11-16

## Outcome

- Root cause confirmed from Windows Application events and Python faulthandler:
  concurrent pywinauto UIA tree traversal entered Qt/COM from multiple workers,
  producing `0xc0000409`/Qt6Core access violations. A stale ROI mouse grab also
  generated repeated drag feedback and excessive CPU load.
- All Smaart UIA entry points now share one re-entrant, bounded process lock.
  ROI drag callbacks now require a real left-button press and clear stale grabs.
- No audio-thread, DSP solver, generator, routing or Smaart data was changed.

## Changed source

- `uia_serial_v8152.py` (new bounded process-wide UIA guard)
- `plot_geometry_v7.py`, `dock_geometry_v815.py`, `full_scan_v7.py`
- `live_sync_v7.py`, `smaart_live_smooth_v8115.py`
- `smaart_mag_geometry_readonly.py`, `win_databar_v7.py`
- `roi_markers_v73.py`
- `build_cython_protected_v8154.py`
- `test_v8152_uia_crash_guard.py`

## Verified evidence

- Focused regression: 58 passed, 2 skipped, 0 failed.
- Canonical regression: 114 passed, 4 skipped, 0 failed.
- Full safe regression: 803 passed, 54 skipped, 0 failed.
- Direct source/Smaart soak: over 75 seconds, responsive; no new access
  violation, no fatal event and no `V73_ROI_DRAG` feedback loop. CPU fell from
  about 81 CPU-seconds/60 wall-seconds before the fix to about 16/60.
- Frozen EXE/Smaart soak: 60 seconds, responsive at every 5-second sample;
  3.14 CPU-seconds, 172.8–232.3 MB during the measured interval and stable
  handles after startup. No new RemiXDuo/pythonw/Qt6Core Application Error.
- Active-build verification: GUARD PASS for RemiXDuo PID 9004, source
  `windows_v8_150_RELEASE_RC1`, Smaart HWND 262990.
- Seven frozen self-checks all exit 0.
- Cython bundle contains `uia_serial_v8152.cp311-win_amd64.pyd` and does not
  expose `uia_serial_v8152.py`.

## Artifacts

- EXE SHA-256:
  `436938BB1A47F9E5FF799D1DC9F2AD5686D4FF65CAEDB7534FAFE3E4769DED73`
- Setup SHA-256:
  `F9E93D51C9A8FBCD22D3ABA9795A254548BBA936FC8087DF5CCDE11B7BF686A7`
- Both artifacts are intentionally `NotSigned`; Authenticode remains a
  release HOLD until a certificate with private key is supplied.

## Remaining gates

- Native stability with Smaart Suite: PASS for source and direct frozen EXE.
- Auto Phase/EQ/FIR operator-click visual behavior was not re-exercised in
  this crash-only run; retain the prior feature evidence and do not infer a
  fresh visual PASS.
- Installed clean-VM install/start/uninstall and Authenticode: HOLD.

