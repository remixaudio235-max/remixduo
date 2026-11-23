# RemiX Duo V8.98 — Remove marked FIR sidebar UI areas

Date: 2026-11-03
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Git root: D:\REMIX_AUTO_ALIGN_V6_DEV
Previous checkpoint: 64c7f39

## UI-only request
Remove the three red-box regions in the supplied Smaart screenshot:
1) 'Chọn TRF V8' / 'Bỏ TRF' manual offline buttons;
2) FIR LF/HF numeric spinboxes and their range label, MagFIR/PhaseFIR status, saved Fs label;
3) '03 KẾT QUẢ / XUẤT HỆ SỐ' section heading.

Keep source dropdown, tappable 512/1024/2048/4096 FIR tap selector, FIR MAG/PHASE mode, manual default-off Phase+ checkbox, THIẾT KẾ FIR and one XUẤT FIR menu visible.

## Implementation
- remix_layout_v856.py: style_fir() uses hide() on exactly the user-marked widgets after creating the existing three section objects; no destructive removal of widgets or signal connections.
- The hidden FIR LF/HF QSpinBox values still back the two draggable plot markers on original Smaart Mag/Phase plots. FIR drag_roi_to() and the worker still read their numeric values. Hiding the Fs text label does NOT change saved Fs, source identity or integrity checks.
- Offline TRF handlers are retained for compatibility with older tests but deliberately have no visible buttons in the dock. No offline fallback introduced or selection authorization bypassed.
- The 03 section label remains internally addressable for old references while not drawn.
- test_v898_fir_hide_marked_sidebar.py: regression against actual FIR Qt controller proving all marked elements hidden, source/taps/mode/Phase+/design/export visible, 114-379Hz drag, real saved trace FIR compute and export gating.
- Adjust two older tests (test_v861_fir_sidebar_offscreen.py and test_v884_logic_fixes.py) so they do not compare geometry of deliberately hidden/previously detached vendor controls. Actual visible Xuất FIR remains in scroll reach.

## Acceptance status
- Focused Qt GUI/algorithm regression: 41 passed, exit 0.
- Full Windows QA suite: 80 test_v8*.py files plus tests/contracts and tests/shared in approved QA venv: **520 passed, 1 skipped**, 107.56 s, exit 0.
- Physical Smaart GUI: PASS. Stopped only identified old RemiX PID 31384; launched source commit ba348ee as PID 28924. Smaart Suite PID 15728 stayed running and responsive. After setting Smaart foreground, Auto FIR dock visibly had NO TRF buttons, LF/HF spin rows, MagFIR/PhaseFIR Fs labels, or 03 section heading. Source dropdown, taps/mode, THIẾT KẾ FIR, one XUẤT FIR button, summary and draggable LF/HF plot markers remained. Desktop evidence: C:\Users\Admin\AppData\Local\Temp\remix_v898_fir_clean_sidebar_live2.png (1920x1080). This is GUI visibility acceptance, not a new acoustic FIR measurement.
- Preserve dirty unrelated files src/remix_duo/entry.py and src/remix_duo/ui/workspace.py; no changes to audio engine, FIR coefficients, ASIO, Smaart session, hardware DSP, license or Mac bundle.
