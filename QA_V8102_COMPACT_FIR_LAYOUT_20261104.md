# RemiX Duo V8.102 — Compact Auto FIR layout QA
Date: 2026-11-04
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA (full tree)
Repository root: D:\REMIX_AUTO_ALIGN_V6_DEV
Baseline: latest merged V8.87, includes V8.101 default PHA and Remote R1.

## User complaint and diagnosis
The screen after V8.101 still had excessive vertical gaps between 'Chọn Taps', the taps combobox and Phase+; 'TẠO FIR' and 'XUẤT FIR' were stacked vertically, unlike the user reference. The panel label was stretched to ~73px because fit_fir_content() forced a minimum of 350px, allowing a flexible QLabel to absorb surplus height. Existing Qt tests checked layout item order only, not real widget geometry.

## Changes
- remix_layout_v856.py ONLY for the production GUI:
  - Set the 'Chọn Taps' QLabel fixed height 16px; note label 18px.
  - Use visible content's size hint with a compact minimum height 260px rather than a forced 350px, eliminating large gaps.
  - Move the existing TẠO FIR QPushButton into the existing XUẤT FIR action row, keeping identical callbacks, labels, FIR computation and export proof. The two actions are now horizontally adjacent.
  - Keep existing source trace selector, optional Phase+ checkbox, mutually exclusive FIR MAG/FIR PHA buttons, frequency drag overlay, all existing widget identities and source/quality gates.
  - Internal result/diagnostic fields remain hidden, but warnings and safety HOLD guards stay operative. No audio or DSP hardware action.
- test_v8101_fir_phase_default_layout.py: verify exact adjacent action row, tap label 16px, total content height <=280px, adjacent geometry gaps <=12px and two buttons sharing y-coordinate.
- test_v884_logic_fixes.py: update scrolling acceptance for a compact pane (310px viewport has no unnecessary scroll; shorter viewport still scrolls and Export remains reachable).

## Verified scope
- Targeted Qt tests: 32 passed, exit code 0, including FIR PHASE default/Phase+ off, MAG and PHASE mode parity, export gating, actual saved TRF filter computation and scroll.
- Full Windows regression in approved QA venv: **522 passed, 1 skipped**, 95.73s, exit code 0. Legacy toolbar tests were adjusted for the already-merged Remote R1 fourth LAN tab; no production Remote changes.
- Qt offscreen screenshot PASS: C:\Users\Admin\AppData\Local\Temp\remix_v8102_compact_fir_qa.png, captured at 190x260px. Visual geometry shows compact label/taps/checkbox/mode rows and equal-y horizontal action buttons at y=219. Initial FIR PHA, Phase+ OFF, taps=1024.
- Physical Smaart GUI after source restart: **HOLD**. Smaart Suite PID 33432 was present during initial diagnosis but absent when attempting a controlled overlay restart. The identity gate correctly aborted the restart, so existing pre-change overlay PID 19492 was not stopped or replaced. No Smaart/Generator launch attempted. Latest source is committed, but the live overlay still requires a restart after Smaart is running.
- The preexisting V8.75 AutoStart watcher is still pointed at the legacy V8.27 source; production migration remains a separate task.
- Keep Smaart session, generator, capture, native trace processing and audio I/O untouched.
- Existing unrelated uncommitted edits in src/remix_duo/entry.py, src/remix_duo/ui/workspace.py and QA Remote helper must remain untouched/uncommitted.
