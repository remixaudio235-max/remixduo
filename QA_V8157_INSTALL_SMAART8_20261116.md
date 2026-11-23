# RemiX Duo V8.157 — Installation and Smaart 8 QA
Date: 2026-11-16. Device: DESKTOP-VNPRJCI.

## Installed binary — PASS
- Installer: dist/installer/RemiXDuo_Setup_V8.157.exe, 116960104 bytes, SHA256 96DC05707324DCFFDBA25FF11E734EEBB4BB0ABFC8F9D2604A549D6C48A1A01C.
- Inno Setup exit 0, 26 protected Cython modules, PyInstaller and frozen self-checks successful.
- Silent installer (/VERYSILENT /NORESTART /TASKS=desktopicon) exit code 0, log build/QA_V8157_INSTALL_20261116.log confirms installation succeeded.
- Registry HKCU DisplayName RemiX Duo V8.157, DisplayVersion 8.157.
- Installed path C:/Users/Administrator/AppData/Local/Programs/RemiX Duo/RemiXDuo.exe
- Installed EXE SHA256 4F6FA67A08A6D743F9B3E00C97C9E4B4D47146DA8B7D3E322B98E2FD42EE90F9, matches staged dist EXE.
- Installed EXE process PID 25252 running, Smaart 8 process PID 44468 responding. Old Python source QA processes shut down.
- Rollback backup: D:/REMIX_AUTO_ALIGN_V6_DEV/BACKUP_INSTALLED_DUO_V8150_20261116.

## Auto EQ Smaart 8 TUNNINNGGG-13 — GUI HOLD
- Installed UIA AUTO EQ clicked (~12ms Invoke); log V8152_AUTOEQ_PREVIEW_READY TUNNINNGGG-13 4 PREVIEW_READY.
- Installed log V8152_MAGEQ_NATIVE_READY cyan 0.783 240.
- Smaart 8 native role + source pixel probe returned valid frame, confidence 0.9292, Mag plot rect (215,563,1474,418).
- BUT installed app screenshot after clicking Auto EQ shows no MagEQ line, Export EQ remains disabled.
- 20 consecutive screenshots while Smaart foreground showed 0 bright lime line pixels at central Mag area; later UltraViewer stole foreground.
- Possible timing issue: cold native registration ~2065ms, strict frame TTL 0.45s and display grace 1.50s, plus recurrent competing foreground. Not yet proven as sole cause.
- Another UI Automation attempt failed SetForegroundWindow Access denied, NO_TOOLBAR. Stop unsafe mouse actions.
- Native EQ source binding is fixed to observer HWND; V8 title glyph verification now uses Smaart 8-specific profile. No Smaart/Generator/audio changes.

## Verification and release status
- V8.157 focused native MagEQ/Smaart 8 tests: 54 PASS, staged smoke: 45 PASS.
- Full suite ran before corresponding test fixture update and reported 13 failures; not yet rerun end-to-end after fixes. No clean full regression claim.
- Installed Auto FIR live visual/export and Auto Phase Top-3/ROI drag not yet signed off.
- Installer is unsigned. Customer release HOLD.
- Next: instrument fresh frame/painter/z-order and improve native verification throughput without weakening strict export proof; then run exclusive desktop GUI and full regression.
STATUS: INSTALL PASS; NUMERIC EQ PASS; NATIVE FIT PASS; MAG EQ VISUAL HOLD; EXPORT EQ HOLD; RELEASE HOLD.