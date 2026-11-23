# RemiX Duo V8.101 — FIR PHA first-open default and compact layout

Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Repo: D:\REMIX_AUTO_ALIGN_V6_DEV
Previous Git baseline: 7642aea
Date: 2026-11-03

## User requirement
- Use the screenshot as the UI reference; default to FIR PHA when opening the FIR workspace.
- Preserve the independent Phase+ checkbox, UNCHECKED by default.
- Preserve editable 512/1024/2048/4096 taps, active ROI drag on Smaart, TẠO FIR, single XUẤT FIR, hidden redundant blocks and hidden FIR summary/details.
- Do not automatically enable Phase+, do not force 4096 taps or auto-run a generator / FIR worker.

## Changes
- signal_tools_gui_v813.py: retain the mutually-exclusive FIR MAG / FIR PHA buttons and shared internal mode selector. Set initial mode to Phase at the END of FIRDialog initialization, after all widgets/source handling are present. Keep the user's later manual changes intact. Remember the mode-row layout reference to reorder without destroying signals.
- remix_layout_v856.py: physically reorder the visible FIR controls in one column: Chọn Taps -> taps combobox -> Phase+ -> FIR MAG/FIR PHA button row -> TẠO FIR -> XUẤT FIR. Section headings/source remain before this sequence; hidden LF/HF/Fs/status/source buttons/result panes remain hidden, signals intact.
- Test additions/adjustments: test_v8101_fir_phase_default_layout.py proves default PHASE, disabled Phase+, tappable 1024/2048, mode exclusivity, correct relative control order and export proof invalidation. Legacy tests explicitly switch to MAG when testing magnitude coefficients, rather than relying on the prior implicit MAG default. A real saved TRF is used in the Qt tests.

## Acceptance gates
- Targeted Qt tests: 12 passed, exit 0.
- Full Windows regression in the approved QA venv: 82 `test_v8*.py` files + `tests/contracts` and `tests/shared`: **522 passed, 1 skipped** in 105.51 seconds; `FULL_QA_EXIT=0`. Older tests exercising FIR MAG now select MAG explicitly, rather than relying on the old default.
- Runtime QA: git checkpoint `8202105` loaded into source Overlay PID 23948, process remains responding. Initial launch was blocked by singleton V823_ALREADY_RUNNING because previous V8.27 AutoStart watcher had launched two verified old-overlay pythonw.exe instances (PIDs 30192/36860). Terminated ONLY those obsolete overlay instances; kept watchdog processes 8012/9056 and Smaart untouched. The second launch succeeded (no singleton error). Smaart PID 31820 was running just after old-overlay termination but was absent at the final inspection; consequently real Smaart overlay screenshot / physical mouse verification is HOLD. No Smaart restart, generator or audio device manipulation was attempted. This source default and layout ARE verified in Qt tests, not yet on the live Smaart screen. The old autostart watcher remains configured for V8.27 and should be separately migrated before a production release.
- Do not change audio IO, Smaart generator/sweep, FIR DSP coefficients or license.
- Preserve unrelated preexisting edits in src/remix_duo/entry.py and src/remix_duo/ui/workspace.py.
