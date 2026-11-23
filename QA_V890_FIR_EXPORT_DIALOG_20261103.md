# RemiX Duo V8.90 — FIR export dialog Windows hang QA
2026-11-03
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA

## Physical UI finding
- Smaart Suite pid 34140 was running normally. Source overlay pid 17828 successfully showed purple PhaseFIR from one selected TRF at 368/3350 Hz.
- Clicking actual live "Xuất TXT" caused "python (Not Responding)" (Windows ghost window), while Smaart stayed responsive.
- Existing QtTest export tests monkeypatched getSaveFileName and did not exercise its true picker. Do not confuse simulated export PASS with the live modal picker.
- The suspected Windows native shell picker entered an unresponsive modal state from Qt floating Tool dialog; the root cause within the shell integration was not independently proven.

## Repair
- Use explicit QFileDialog.Option.DontUseNativeDialog for both FIR TXT/WAV and FIR DSP/Crossover picker calls; retain one-source proof checks before/after selection.
- Real Qt nonnative QFileDialog tested in offscreen modal event loop, automatically accepted via QTimer (not monkeypatched), wrote valid TXT and WAV in test folder; additional mocked entry asserts DontUseNativeDialog.
- Targeted suite test_v890_fir_qt_export_dialog, test_v889_fir_full_gui, test_v845_fir_one_trace: 8 passed in 2.85 seconds.
- Real source overlay process 17828 with exact verified cmdline was terminated (not Smaart) and new source process started. On-screen live picker needs separate acceptance on the restarted process.
- The previous FIR color-identity fix 56e90a7 and on-screen proof 869b3be remain intact.
- Unrelated changes src/remix_duo/entry.py and src/remix_duo/ui/workspace.py are left unchanged/uncommitted.

## Final regression and live startup limitation
- 73 Windows test_v8*.py files: 444 passed, 1 skipped in 42.81 s using existing Python 3.11 QA venv.
- Real non-native Qt save dialog was exercised in the test event loop with true TXT/WAV writes; full popup integration on a live Smaart desktop remains unverified.
- Source overlay pid 17784 relaunched after patch, Smaart pid 34140 remains running/responsive. As of latest inspection, overlay process is alive but no visible top-level GUI window; this prevents claiming fixed live Windows picker or full FIR GUI acceptance for this new process.
- Source checkpoint limited to FIR export fix; do not touch the installed V8.84 Windows binary.
