# RemiX Signal V8.25 — Compact green Auto Phase button ONLY
Date: 2026-10-30; Admin-PC Windows QA

## Corrected requirement
- User wanted only green AUTO PHASE button/card compact; do NOT reduce overall Auto Phase dialog.
- Restored native Smaart-docked panel height to the original 446 px (panel height from available Smaart side-column geometry, no V8.24 313 px clamp).
- Restored Phase page/stack to 400 px, original Trace 1/2 typography and spacing, Top3 option sizing (configured fixed height 44, Qt actual 48).
- Green AUTO PHASE button fixed height 26 px; its own action card fixed height 36 px; lime #39FF14.
- Selection stable-tick 3/3 gating, snapshot integrity, SUM/Top3 fail-closed, HIDE/LIVE/EQ/FIR behavior preserved from V8.24.

## QA verified
- Native Windows Qt screenshot: V825_FULL_DIALOG_SMALL_BUTTON.png; dialog=446 px, stack=400, action card=36, button=26; all 3 Top3 within viewport; HIDE/LIVE/EQ/FIR PASS.
- 14/14 baseline pytest PASS.
- V8.24 StableTickGate 250-cycle simulated snapshot + 0/1/3/6 trace, transient and recovery PASS on V8.25 code.
- Offline PEQ/FIR numerical QA PASS.
- Smaart Suite is not running on Admin-PC now; live MagEQ and 100 true fresh viewport scans were not re-tested in V8.25 and remain HOLD.
- Named Windows mutex held by running V8.25 logical application (venv pythonw wrapper PID 16340 and CPython child PID 14808). Not two competing scanners.

## Rollback
- Previous V8.24 source preserved at D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA
- Close V8.25 process, then invoke V8.24 launcher to roll back.