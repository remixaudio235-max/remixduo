# RemiX Duo V8.103 — Chọn Taps and dropdown in one row

Date: 2026-11-04
Canonical whole source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Git root: D:\REMIX_AUTO_ALIGN_V6_DEV
Prior checkpoint: 749bbfa / 58b841a

## User request
Put the 'Chọn Taps' label and 512/1024/2048/4096 taps dropdown in one horizontal row, two columns, with the label on the left and the combobox on the right. All other FIR controls stay as approved in V8.102: FIR PHA default, Phase+ opt-in and unchecked, MAG/PHA buttons independent, TẠO FIR/XUẤT FIR horizontally paired.

## Source change
- remix_layout_v856.py: after creating the '02 THIẾT LẬP FIR' section heading, move the existing taps_label and taps QComboBox (not clones) into a new QHBoxLayout at the previous vertical position. Set 67px label width and 5px spacing, center the label vertically. Existing tap count, FIR worker connection, FIR selection invalidation and export gate untouched.
- test_v8101_fir_phase_default_layout.py: updated to assert the actual nested 1-row/2-column layout; verify both widgets share the same vertical center and the dropdown follows the label horizontally.
- test_v861_fir_sidebar_offscreen.py: enforce nested row ordering and retain LF/HF hidden numeric input bindings.

## Verification
- Targeted FIR GUI tests: 30 passed, exit 0.
- Offscreen Qt screenshot: C:\Users\Admin\AppData\Local\Temp\remix_v8103_fir_taps_two_columns_qa.png, at 190x260 px.
- Exact Qt geometry: taps label (6,123,67,16); taps dropdown (78,117,106,29). First-open mode phase, Phase+ unchecked, taps=1024.
- Full Windows regression: **522 passed, 1 skipped**, 75.31 seconds, exit code 0. Legacy test_v856 was updated to check the new horizontal nested row rather than expecting taps as a child of the vertical layout.
- Physical Smaart overlay restart: not yet performed; Smaart was absent in prior session. Never restart or generate audio unless target process and safety are confirmed.
- Existing unrelated dirty source entry.py, ui/workspace.py and _qa_show_remote_gui_r1.py are preserved, unstaged.
