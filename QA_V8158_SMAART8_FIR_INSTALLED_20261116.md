# RemiX Duo V8.158 — Smaart 8 FIR native line restore
Date: 2026-11-16. Target: DESKTOP-VNPRJCI.

## Root cause and repair
- V8.157 fir_native_v846.py bound native FIR to FindWindow(None, 'Smaart Suite'), which never finds the real Smaart 8 window titled 'Smaart'.
- V8.157 native FIR also used Suite 9 Mag/Phase title signatures for Smaart 8, despite a separate V8 glyph verification module being available.
- V8.158 uses verified_smaart_host(hub): observer HWND must equal active bound Smaart HWND, and window must be visible and not minimized.
- Smaart 8 native FIR uses Smaart 8-specific detect_v8_profile from freshly captured same-host pixels; retains independent original Mag source match, phase pixel fit, smoothing and source identity gates.
- Never writes to Smaart, generator, audio output, DSP, or TRF files.

## Regression and DSP verification
- Focused FIR/native/production tests PASS (21, 23 and 42 in separate checks).
- Full staged regression: 828 passed, 54 skipped, 1 warning, 0 failed, 119.32 seconds.
- Real original Smaart 8 TUNNINNGGG-13.trf: 806 bins, both Mag and Phase independent native FIR frames valid.
- 4096-tap MAG proof: native mag source fit score 1.0, phase fit 0.9799, raster 2,352,504 bytes.
- 4096-tap PHASE proof: mag source fit 1.0, phase fit 0.9799, raster 2,358,400 bytes.

## Production packaging and installation
- 26 protected Cython modules; frozen main EXE and watcher/setup; production self-checks PASS; Inno compile exit 0.
- Installer: dist/installer/RemiXDuo_Setup_V8.158.exe, 116,963,708 bytes.
- Installer SHA256 71D43BCFF5A70E461412947789A9B48BEC0B7500F8C9FA90870C6963B799C145 (unsigned).
- Installer upgrade exit 0, installed EXE SHA256 D8DE9EBDFBA540F8E5DE6530C973B5723BE12D0ED38FCAC4F1580EED368B5844, matching staged dist.
- Installed: C:/Users/Administrator/AppData/Local/Programs/RemiX Duo/RemiXDuo.exe, HKCU DisplayVersion 8.158, current PID 36356.
- Backup V8.157 before upgrade: D:/REMIX_AUTO_ALIGN_V6_DEV/BACKUP_INSTALLED_DUO_V8157_20261116.

## Real Smaart 8 GUI installed release QA — PASS with caveat
- Smaart 8 PID 44468 running, responsive, same saved TUNNINNGGG-13 marked trace.
- FIR PHA via UI Automation: V8124_FIR_OK phase 512 taps, 500–2500 Hz, Excess RMS 20.6 to 13.5 deg; V8124_FIR_NATIVE PhaseFIR PASS; Export FIR button enabled.
- Screenshot phase: build/qa_v8158_INSTALLED_phase_gui.jpg confirms purple PhaseFIR preview over original Smaart Phase chart.
- FIR MAG via UI Automation: V8124_FIR_OK mag 512 taps, 500–2500 Hz; V8124_FIR_NATIVE MagFIR PASS; Export FIR button enabled.
- Screenshot mag: build/qa_v8158_INSTALLED_mag_gui.jpg confirms cyan MagFIR preview over original Smaart Magnitude chart.
- Both RemiXDuo.exe PID 36356 and Smaart.exe PID 44468 Responding=True, no QA Python app concurrently running.
- Remaining caveat: logs show intermittent native HOLD -> PASS transitions during pixel re-verification, so long-duration flicker-free stability NOT established.
- Actual saving/export of FIR WAV/TXT file was NOT tested, only button enablement.
- Existing Auto EQ display/export HOLD is separate and NOT resolved by this FIR-specific fix.
- Do not distribute as signed/customer release until code signing and follow-up flicker/export verification.

STATUS: V8.158 INSTALLED PASS; FIR MAG LINE PASS; FIR PHASE LINE PASS; GUI EXPORT ENABLED PASS; FLICKER/EXPORT FILE/COMMERCIAL RELEASE HOLD.