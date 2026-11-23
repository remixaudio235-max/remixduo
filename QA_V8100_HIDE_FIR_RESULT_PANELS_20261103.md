# RemiX Duo V8.100 — Hide FIR result message panels

Date: 2026-11-03
Canonical full source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Repository root: D:\REMIX_AUTO_ALIGN_V6_DEV
Previous checkpoint: e71237d

## User screenshot scope
The two red outlined rectangles are the FIR results summary QLabel (coefficient/taps/Phase RMS preview) and the longer details QTextEdit diagnostics. They should no longer appear anywhere on the Smaart Auto FIR right dock, even after generating FIR. The FIR PHASE plot overlay, Taps, separate FIR MAG / FIR PHA buttons, manual Phase+ checkbox (default OFF), TẠO FIR, and single XUẤT FIR button remain.

## Implementation
- remix_layout_v856.py: hide FIR-only summary and details within style_fir() together with already-hidden controls; keep existing widget identity, source/quality diagnostics, export guards, FIR worker and Smaart native trace selection unchanged. This does not hide the Auto EQ panels.
- Reduce FIR content minimum height from 570 to 350 to avoid unnecessary blank lower region after result panels are hidden. Actual layout size remains bounded by minimum size, size hint, totalHeightForWidth.
- test_v898_fir_hide_marked_sidebar.py: assert both red-box panels are hidden initially, after valid saved-TRF FIR compute, and after Phase+ invalidates the old FIR. Ensure both still carry internal diagnostics while export proof and plot remain operational.
- No change to TF engine, FIR solver, coherence gates, taps, Smaart generator/capture, DSP writes or Mac packaging.

## Verification
- Focused Qt GUI / FIR tests: 31 passed, exit 0.
- Full Windows regression in approved QA venv: 81 `test_v8*.py` files plus `tests/contracts` and `tests/shared`: **521 passed, 1 skipped**, 99.52s, exit code 0.
- Physical GUI PASS: stopped only verified RemiX overlay PID 19028; launched source commit 0274e2a as PID 32992. Smaart Suite PID 15728 kept alive and responsive; no generator, capture, DSP or device changes. Real desktop screenshot `C:\Users\Admin\AppData\Local\Temp\remix_v8100_fir_panels_hidden_live.png` confirms two red-box panels absent; FIR MAG/PHA, Taps, TẠO FIR and XUẤT FIR remain. Screenshot taken after verified Qt tab click with owning PID 32992 and Smaart as foreground. This is visual GUI acceptance; actual FIR post-compute absence is backed by the Qt real-TRF regression, not a new physical microphone measurement.
- Existing unrelated edits src/remix_duo/entry.py and src/remix_duo/ui/workspace.py MUST NOT be included in commits.
