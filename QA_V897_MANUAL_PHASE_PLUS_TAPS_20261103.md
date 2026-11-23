# RemiX Duo V8.97 — Manual Phase+ checkbox and independently selectable FIR taps

Date: 2026-11-03
Canonical source (entire tree): D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Repo root: D:\REMIX_AUTO_ALIGN_V6_DEV
Prior checkpoint: bb58a89

## Requested behavior / implemented

- FIR PHASE mode no longer automatically checks Phase+. The checkbox is an independent visible, unchecked control when in FIR PHASE; it is hidden in FIR MAG.
- FIR mode selector reads 'FIR PHASE | Pha' (not 'FIR PHASE+ | Pha') because Phase+ is a separate user choice.
- FIR tap selector stays enabled: 512, 1024, 2048, 4096. Changing mode or checking Phase+ does not force 4096, lock the selector, or silently substitute coefficients.
- Unchecked Phase+: default conservative phase-only solver (phase_plus=False), with user's tap setting.
- Checked Phase+: advanced solver (phase_plus=True) with user's selected taps. It may fail closed for short FIR if full-band magnitude, coherence, early energy or actual phase improvement does not pass; a HOLD is never silently replaced by 4096 taps.
- Selecting/clearing Phase+, taps, LF/HF or mode invalidates prior prediction, SHA/trace proof and TXT/vendor export eligibility. The single XUẤT FIR menu and manufacturer profile tap limits remain unchanged.
- No Smaart generator, sweep, capture, or DSP hardware writing.

## Source scope
- signal_tools_gui_v813.py: visible opt-in checkbox, default false, show only in PHASE, no tap forcing or locking, result/provenance binds actual checkbox value.
- src/remix_duo/core/filters.py: remove 4096-only Phase+ refusal; preserve all safety gates for 512/1024/2048/4096 taps.
- test_v895_fir_phase_plus.py, test_v896_fir_single_export_menu.py, test_v889_fir_full_gui.py: update forced-4096 and auto-checked assumptions.
- test_v897_phase_toggle_manual.py: new regression proving default unchecked, all tap values selectable, manual toggles invalidate FIR/export, and regular 1024-tap Phase mode works.

## Verification
- Full Windows regression: 78 test_v8*.py files, tests/contracts and tests/shared from approved QA venv: **518 passed, 1 skipped**, exit 0.
- New test_v897_phase_toggle_manual.py plus related Phase+/export tests: **6 passed**, exit 0.
- Physical Smaart GUI restart and visual confirmation pending after this QA report.
- macOS QA app remains unmodified. Shared solver change still requires Mac test/build before cross-platform production release.
- Existing unrelated modifications to src/remix_duo/entry.py and src/remix_duo/ui/workspace.py are preserved, not staged or committed.
