# RemiX Duo V8.91 — Smaart window process identity hardening
Date: 2026-11-03
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA

## Fault evidence
- After resolving native teal PhaseFIR and FIR export modal GUI freeze, a diagnostic source run (faulthandler) captured a Windows access violation with the active stack in psutil._pswindows.exe during win_databar_v7.locate_smaart -> process executable lookup.
- The crash happened while polling Smaart window identity; it did not crash Smaart itself (PID 34140 remained responsive).
- An access violation inside the native psutil extension cannot be safely handled by a Python try/except. Do not disable identity checking.

## Safety correction
- win_databar_v7.locate_smaart now queries process name using kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION) and QueryFullProcessImageNameW, validates only smaart.exe or smaart suite.exe, and always closes the process handle.
- No executable path or PID is trusted from a window title alone; an inaccessible process returns an empty name (fail closed).
- Windows Admin-PC real test: PID for Smaart Suite resolves to 'smaart.exe'; Python resolves 'python.exe'; invalid PIDs return empty; actual Smaart window is located.
- test_v891_win_databar_pid_identity.py exercises invalid PIDs, spoofed Smaart title with Chrome PID/name, correct Smaart identity, and native current-process lookup.
- Targeted regression: 9 PASS including FIR GUI and true Qt save dialog.

## Limitations
- Native C access violation root cause beyond the observed psutil exe lookup is not independently proven. Regression must include live long-run window scanning and foreground transitions.
- Physical FIR MAG/PHASE curve drawing and LF/HF dragging were previously verified on actual Smaart and preserved.
- Export TXT live button had hung before the Qt nonnative file picker fix; new dialog passed actual offscreen Qt event loop and saved TXT/WAV, but post-fix live desktop export still requires independent confirmation.
- No Smaart Generator/Sweep/audio device, no hardware DSP writes, no license bypass.
- Preserve unrelated dirty files src/remix_duo/entry.py and src/remix_duo/ui/workspace.py and existing Windows V8.84 install.

## Final full regression
- All 74 test_v8*.py files run in pre-existing Python 3.11 QA venv: 450 passed, 1 skipped in 65.18 seconds; exit 0.
- This result covers the new identity guard, Qt nonnative FIR export dialog, native teal PhaseFIR and existing Windows behavior.
