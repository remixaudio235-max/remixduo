# RemiX Duo V8.99 — FIR mode buttons and tap label

Date: 2026-11-03
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Repo root: D:\REMIX_AUTO_ALIGN_V6_DEV
Baseline commit: 748e589

## Requested GUI layout (Windows Smaart overlay)
- Add explicit visual label 'Chọn Taps' before the existing 512/1024/2048/4096 taps dropdown.
- Replace the single visible FIR MAG/PHASE combobox with two separate, mutually exclusive buttons 'FIR MAG' and 'FIR PHA'. Active selection has cyan highlight and checked border; switching buttons uses the unchanged internal fir_mode combo state to preserve worker, PhaseFIR/MagFIR preview, source proof and export behavior.
- Rename visible 'THIẾT KẾ FIR' button to 'TẠO FIR' without altering its compute signal.
- Keep manual Phase+ checkbox OFF by default; show it only when FIR PHA selected, with freely selectable taps. Do not change the FIR solver coefficients, coherence gate, DSP limits, Smaart session state, or GUI's single 'XUẤT FIR' action.
- Existing three red-marked sidebar regions remain hidden per V8.98, with draggable LF/HF lines intact.
- Existing FIR mode combobox is kept invisible and synced bi-directionally so legacy tests and modules that set fir_mode.currentIndex() still work.

## Modified files
- signal_tools_gui_v813.py: visual mode buttons + QButtonGroup, taps_label, TẠO FIR; sync existing state.
- remix_layout_v856.py: section heading placed above taps label, selected/unselected button QSS, accessibility labels.
- test_v898_fir_hide_marked_sidebar.py: old visible-dropdown assertion updated to two visible buttons and an internal hidden dropdown.
- test_v899_fir_separate_mode_buttons.py: independent Qt regression for button selection, Phase+ and taps, compute/export invalidation.

## Acceptance evidence
- Focused Qt regressions: 41 passed, exit 0.
- Source syntax and git diff --check: passed.
- Full regression (approved QA venv): 81 test_v8*.py files plus tests/contracts and tests/shared: **521 passed, 1 skipped**, 104.41 s, exit code 0.
- Physical GUI QA PASS on real Smaart Suite, PID 15728, preserved and responsive. Old verified Overlay PID 28924 was stopped; new source commit 3200167 launched as PID 19028. Source overlay shown on target Smaart by foreground activation. Desktop evidence: C:\Users\Admin\AppData\Local\Temp\remix_v899_fir_mode_buttons_live.png shows Chọn Taps label above dropdown, two mode buttons, TẠO FIR and existing XUẤT FIR; C:\Users\Admin\AppData\Local\Temp\remix_v899_fir_pha_selected_live.png shows actual mouse click FIR PHA, exclusive active highlight and Phase+ visible but unchecked. Qt click hit owner PID 19028; no Smaart generator/sweep or DSP writes. Physical coefficient remeasurement is not part of UI acceptance.
- Prior unrelated dirty source entry.py and ui/workspace.py preserved and excluded from this work.
