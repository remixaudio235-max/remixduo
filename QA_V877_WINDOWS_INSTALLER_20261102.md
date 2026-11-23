# RemiX Duo V8.77 QA — Windows EXE + Inno Installer Acceptance

Latest V8.81 stability package: 76,884,038 bytes SHA256
674F9DC8E99CF4CB92D1B959ED5C3D5998509FB64075EB16CA4A4E4582FA7E07.
Install exit 0; installed Qt/online/package 0/0/22 (intentionally unlicensed).
EXE hash matches dist; license state preserved. Includes lock splitting, async
activation, tick-cache ambiguity protection and readable notices. Native HOLD.

Latest repaired artifact (missing GUI assets): 76,612,299 bytes, SHA256
AC39DF5C569A53C116F53B2F1C035F3AF5998B8D5E4463A0D38D20373CDFD4C3.
Installed exit 0; Qt/online/package probes 0/0/0; license unchanged.
Toolbar logo and both role PNG templates now ship in _internal and are decoded
by the frozen Qt gate. Existing artifact hashes below are historical.
Date: 2026-11-02 | Admin-PC | Windows 10 x64 | Python 3.11.9
Source (unchanged single working tree):
D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Branch: qa/remix-duo-v873-native-tf-reader
Pre-build HEAD: 34fc09d

## 2026-11-02 Codex audit erratum and source fix

- The original `--package-selfcheck` result with exit code 21 did **not**
  execute the self-check body; the live overlay mutex rejected it first.
- Source now dispatches `--package-selfcheck` before acquiring the singleton
  and regression QA proves it does not create QApplication or contend with
  the running overlay.
- The build script no longer supports packaging stale output via `-SkipBuild`;
  all three PyInstaller invocations use `--clean`, and the newly built main
  EXE must pass `--package-selfcheck` before Inno Setup runs.
- A clean PyInstaller/Inno rebuild completed after these fixes. Packaged
  self-check returned 0 while the source overlay remained active; no GUI was
  created. Inno recompilation is warning-free after adding `RunOnceId` to the
  uninstall hook.
- No GUI, Smaart, audio device or installer was launched for this source fix.

## Concrete generated artifacts on Admin-PC

MAIN (QA-only V8.74 offline signed test license):
  dist\RemiXDuo_QA\RemiXDuo_QA.exe
  17,008,091 bytes, PyInstaller onedir (includes _internal dependencies).
WATCHER (no Smaart generator or audio I/O):
  dist\RemiXDuoSmaartWatcher.exe
  8,024,076 bytes, PyInstaller onefile windowed.
POSTINSTALL helper:
  dist\RemiXDuoSmaartSetup.exe
  8,020,894 bytes, PyInstaller onefile console.
INSTALLER (single-file Inno Setup package):
  dist\installer\RemiXDuo_QA_Setup_V8.77.exe
  76,610,826 bytes
  SHA-256: C9B0C6D4FD5AA17DB0A4E9457E424A4F0A94AAE2035363DF547B03F53210C57F
  Windows signature status: NotSigned
  Inno Setup: 6.7.3 successful warning-free compile.

Shortcut created on Admin-PC Desktop:
  C:\Users\Admin\Desktop\CAI DAT RemiX Duo QA V8.77.lnk
  Points to the exact installer. Shortcut is not an installation.

## QA identity and entitlement policy

- QA exe named RemiXDuo_QA.exe, QA runtime hook
  qa_runtime_hook_remix_duo_v877.py sets in-process sys flag.
- overlay_v7.py frozen commercial EXE without QA hook ALWAYS uses
  remix_duo_cloud_license_v876.activation_gate.
- The QA-only frozen installer uses RemiX Duo V8.74 local signed DUO_PRO
  activation to allow real UI evaluation while Cloudflare service URL
  is still not configured. This must NOT be sold or shipped to clients
  as the commercial licensing channel.
- QA builds never embed signer private key. Admin issuer files stay out
  of the PyInstaller import graph and Inno [Files] source.
- This is a DEVELOPMENT / QA installer. Windows SmartScreen can warn
  because no code-signing certificate has been applied.
- The existing running source GUI was NOT closed/restarted. The one
  shared instance mutex intentionally prevents a second overlay.
  Close existing RemiX Duo before launching installed QA EXE.
- Install is per-user at %LOCALAPPDATA%\Programs\RemiX Duo QA,
  no administrator/UAC elevation required.
- Installer provides Start Menu icon, optional Desktop icon, an opt-in
  checkbox for Smaart 8/9 watcher, and uninstaller entry.
- If the existing source watcher is already registered in HKCU Run,
  postinstall refuses to overwrite that other path; the standalone
  launcher still works. To switch explicitly, disable source watcher
  before enabling installed watcher. Do not silently replace it.

## QA checks actually completed

PASS: PyInstaller onedir GUI build, clean interpreter user-site disabled.
PASS: PyInstaller onefile watcher build.
PASS: PyInstaller onefile postinstall helper build.
PASS: Inno Setup 6.7.3 single-file compile, no source modification.
PASS: packaged RemiXDuoSmaartSetup.exe --scan:
      recognized Smaart 8/9 and 113 Smaart Suite V9 TRF files.
PASS: packaged RemiXDuoSmaartWatcher.exe --one-shot exit code 0
      while no Smaart process exists.
PASS: packaged RemiXDuo_QA.exe --package-selfcheck exit code 0
      with the original source GUI running. The QA runtime hook performs the
      headless license/module check before overlay imports or singleton lock.
      This is NOT a complete independent GUI startup acceptance test.
PASS: setup SHA-256 and Authenticode status explicitly verified.
PASS: desktop installer shortcut points at actual EXE.
PASS: original GUI and audio session untouched.

QTCORE STARTUP FIX (2026-11-02):
- Reproduced the installed error `DLL load failed while importing QtCore`
  before any activation UI could run. Installed and original dist Qt files
  were byte-identical, ruling out installer copy corruption.
- Root cause: the Codex host PATH exposed Poppler's incompatible ICU 78
  `icuuc.dll`; PyInstaller collected that foreign DLL beside the application,
  where it shadowed the Windows ICU expected by Qt 6 and caused WinError 127.
- `build_remix_duo_qa_v877.ps1` now replaces PATH with only the selected
  Python, System32, Windows and Inno directories before the first PyInstaller
  analysis. The package no longer contains the foreign `icuuc.dll`.
- The runtime hook exposes `--qt-selfcheck`, which imports QtCore/QtGui/
  QtWidgets without starting QApplication. The build fails closed before Inno
  if it does not exit 0. Rebuilt EXE Qt self-check and package self-check both
  exit 0; direct QtCore.pyd dependency load PASS; 134 non-GUI regressions PASS.
- The repaired installer remains unsigned. It was installed on Admin-PC after
  closing the exact failed EXE that held the destination file open. Installed
  EXE/QtCore.pyd/Qt6Core.dll hashes match dist, and both installed headless
  self-checks exit 0. Clean-VM and Live GUI verification remain HOLD.

NATIVE TF CONTRACT FOLLOW-UP (2026-11-02):
- Reproduced malformed SDK values being accepted because Python bool is an
  int subclass, and unhashable source IDs raising TypeError.
- `smaart_live_tf_reader_v873.py` now rejects boolean numeric fields,
  mutable array containers, invalid SDK identity/rate/trust metadata and
  non-packet SDK values before they enter the frame cache.
- 24 new strict-boundary regression cases PASS; 67 Native reader/API tests
  PASS; V8.73-V8.78 non-GUI regression total 140 PASS after adding the Qt
  bundle/build and Pro-style online activation cases.
- This validates the fail-closed source contract only. Native SDK stream and
  Auto Phase/Auto EQ/Auto FIR solver wiring remain HOLD.

LICENSE VISIBILITY FOLLOW-UP (2026-11-02):
- Admin-PC already contains a valid perpetual V8.74 QA token created at
  02:44:38: ID `DUO-ADMIN-QA`, customer `RemiX Audio QA`. Reinstall correctly
  preserves it, so the key-entry dialog is not shown again.
- A clean LOCALAPPDATA packaged self-check exits 22; the installed profile
  exits 0. The installer does not bundle or silently create a license token.
- Valid state is now passed into ToolHub as `Duo · ACTIVE`; the context menu
  and tooltip expose only license ID/customer/expiry, never the key.
- Three regression tests PASS. Visual GUI verification remains HOLD because
  this audit did not launch QApplication or Smaart.

PRO-STYLE ONLINE ACTIVATION FOLLOW-UP (2026-11-02):
- Audited the active `RemiXaudiopro.pyx` online-first flow from APPRMcodex.
  RemiX Duo now presents SĐT/License ID and Machine Hash by default; raw LIC1
  entry is retained only in the `Offline nâng cao` tab.
- `remix_duo_online_license_v878.py` uses the deployed RemiX Audio license API
  contract and pinned public verifier. It never stores a server response until
  signature, v3/fpv3, WIN/PRO, expiration and current-machine checks all pass.
- Missing/not-yet-active IDs use the request-activation endpoint, matching the
  RemiX Audio Pro customer workflow. No admin or signing secret is packaged.
- The first operator attempt found that `urllib` HTTP 4xx exceptions discarded
  the server JSON before the missing/not-active fallback could inspect it. The
  client now preserves the bounded JSON body and HTTP status; a regression test
  proves an HTTP 404 `LICENSE_NOT_FOUND` reaches request-activation.
- Frozen Qt, online-module and package checks return 0/0/22 respectively on the
  intentionally unlicensed Admin profile. Installed EXE hash matches dist.
- The operator submitted an ID and captured the activation dialog; Codex did
  not replay or transmit that value. Successful server issuance and main-window
  entry remain HOLD for operator acceptance with the corrected build.

NOT YET VERIFIED:
- No installer execution on Windows Sandbox / fresh Windows VM.
- No actual Smaart startup → installed Duo GUI end-to-end test.
- No GUI first-activation flow on unlicensed machine.
- Product-scoped Cloudflare Worker routing is deployed and live validation
  probes pass; successful real customer issuance remains HOLD.
- No commercial Authenticode signing, Windows SmartScreen reputation.
- No audio I/O or Generator/sweep was started (safety requirement).

## How to install/test on Admin-PC

1. Save current work and CLOSE the existing RemiX Duo source GUI
   before opening a second one. Do not close Smaart on our behalf.
2. Double-click Desktop shortcut
   "CAI DAT RemiX Duo QA V8.77"
   or navigate to installer full path above.
3. Review install location and the optional watcher checkbox.
   If HKCU Run is still assigned to the older source watcher,
   the installer will preserve it rather than overwrite.
4. Install. Then open Start Menu > RemiX Duo QA.
5. On Admin-PC the V8.74 QA license is already installed; on any
   other PC, use its new Machine ID to issue a DUO_PRO test key from
   the admin-only issuer. Do not distribute private signer material.
6. For uninstallation use Windows Settings > Apps > Installed Apps >
   RemiX Duo QA > Uninstall. Only the installed watchdog Run entry
   is removed if it belongs to that installation; saved .trf files,
   Smaart, and original project repo remain untouched.
7. On a clean Windows VM check installation, boot, Smaart 8/9
   detection, saved TF import, uninstallation and reinstallation.

## Rebuild

Run build_remix_duo_qa_v877.ps1 from the existing source. It sets
PYTHONNOUSERSITE=1 to avoid the obsolete pathlib user-site backport
breaking PyInstaller, and excludes unnecessary AI packages. PyInstaller
and Inno Setup must already be installed on the build machine.

Build output is deliberately NOT Git-tracked: the release EXE and
installer are binary artifacts under the ignored dist directory.
