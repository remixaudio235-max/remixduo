# V8.153 Auto Phase Qt/COM STA crash repair — 2026-11-16

## Exact source and runtime

- Source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_150_RELEASE_RC1`
- Frozen EXE: `dist\RemiXDuo\RemiXDuo.exe`
- Verified runtime after self-check restart: PID 30852
- Smaart Suite: PID 6912, HWND 2229598; not stopped or modified

## Reproduction and root cause

V8.152 still crashed after an Auto Phase interaction. Windows Application
Error recorded Qt6Core fast-fail `0xc0000409`, offset `0x1c8d8`. Running the
same source with a console exposed `OleInitialize` failure `0x80010106`:
pywinauto/pythoncom had initialized the GUI/main thread as MTA before Qt could
initialize Windows OLE as STA.

## Changes

- Set `sys.coinit_flags = 2` before any project/UIA import.
- Deliver Auto Phase `Future` completion through a GUI-thread `QTimer` rather
  than invoking Qt/SIP objects from the executor callback.
- Added ordering and worker-callback regression guards.

## Verified evidence

- Source console: prior `OleInitialize 0x80010106` warning is absent.
- Direct frozen EXE: three consecutive Auto Phase button activations;
  process remained responsive, handles stable, no new Qt6Core/WER event.
- Full safe regression: **805 passed, 54 skipped, 0 failed**.
- Frozen self-checks: Cython, Qt, online license, updater, Auto EQ, Auto FIR,
  and package checks all exit 0.
- `VERIFY_ACTIVE_BUILD.py`: **GUARD PASS** for PID 30852.
- EXE SHA-256:
  `3984ED0C5AAC12B10596138D4CE14C8FABDFFDEBB26A7A2AD5EFAB57EA362DD4`
- Setup SHA-256:
  `188A6D94CBB5E93B3AA36D98EA6290D6AC60782FCF6AF43421394CB3E7FED123`

## Remaining HOLD

- Visual/native proof that the newly computed Auto Phase result line completed
  correctly was obstructed by unrelated foreground-window stealing; crash
  prevention is PASS, result-render acceptance remains HOLD.
- Clean-VM installation/uninstallation is not rerun.
- EXE/setup are NotSigned because this host has no usable signing private key.

## Safe next command

Run the final setup from `dist\installer\RemiXDuo_Setup_V8.150.exe`, then
repeat one operator Auto Phase action and capture native Smaart/overlay proof.
