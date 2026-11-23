# RemiX Duo V8.74 — Licensing / Key Active QA and Admin Handoff
Date: 2026-11-02 | Platform: Windows Admin-PC

Source (one existing folder):
D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Git branch: qa/remix-duo-v873-native-tf-reader
Pre-change HEAD: 897716c
Checkpoint: checkpoint/remix-duo-v873-handoff-20261102

## What was checked against RemiX Tune

Reference read (NO edits):
D:\Remix Tune 2026\R23_UI_NATIVE_INTEGRATION_QA\src\
  license_signer_gui_fixed_padding_v3_machinekey_day0v2.py

RemiX Tune's signer issues:
LIC1.<base64url canonical payload JSON>.<base64url Ed25519 signature>
with v=2, fpv=2, platform WIN/MAC/ANY, 1-2 machine_ids,
machine and machine_id aliases, lic_id, edition, name, iat, exp.
exp=0 is perpetual; days>0 sets expiration. Admin ledger TSV/Excel.

Duo uses the exact compatible LIC1 payload shape but a NEW isolated
issuer keypair and hard product edition DUO_PRO, platform WIN, FPV2
machine ID DUO2-<32 hex SHA256 prefix>. A Tune PRO license is not
interchangeable with Duo license (different issuer public key & edition).
Duo fingerprint uses a product-domain-separated hash of Windows
MachineGuid, not an assumed copy of Tune's compiled fingerprint algorithm.
It is a Windows-install identity, not a hardware TPM proof.

## Files added/modified IN SAME SOURCE

remix_duo_license_v874.py
  - Verifies Ed25519 signature on exact payload bytes with release-pinned
    public key. Checks duplicate JSON keys, size, version/fpv, WIN,
    DUO_PRO product scope, 1-2 valid fingerprints, aliases, license id/name,
    iat/exp and current machine; supports perpetual and 1-36500 day keys.
  - Client no signing secret; invalid license cannot overwrite valid file;
    atomic activation to %LOCALAPPDATA%\RemiXAudio\Duo\license.lic.
  - PyQt6 startup activation dialog when missing/invalid/expired: shows
    Machine ID, Copy ID, paste LIC1, Activate/Exit.
remix_duo_license_cli_v874.py
  - machine, status, activate --file [path]; returns valid/code JSON.
remix_duo_issuer_admin_v874.py (ADMIN ONLY, DO NOT SHIP)
  - init/public/issue; generated private seed encrypted with Windows
    CURRENT USER DPAPI in:
    %LOCALAPPDATA%\RemiXAudioIssuer\Duo\duo_signer_ed25519.dpapi
  - Sign with edition DUO_PRO only, ledger:
    %LOCALAPPDATA%\RemiXAudioIssuer\Duo\duo_license_ledger.tsv
  - Private seed is never written unencrypted in repo or client.
remix_duo_license_admin_gui_v874.py (ADMIN ONLY, DO NOT SHIP)
  - Tune-inspired Tkinter signer with machine IDs, customer, order ID,
    days 0/perpetual, output .lic and Copy key; relies on DPAPI signer.
test_v874_duo_license.py
  - Disposable synthetic keypair tests only; no production private key.
overlay_v7.py
  - Minimal startup gate after QApplication, before App(), any observer or
    Smaart integration; no --demo bypass; no algorithm or plot modifications.

## Validation executed directly on Admin-PC

- 29/29 license tests passed separately.
- 91/91 combined license + V8.73 + V8.72 regressions PASS (9.00s).
- Python py_compile for all license modules and overlay passed.
- QT_QPA_PLATFORM=offscreen + QApplication + activation_gate => True
  against the real admin-issued development license; no visible GUI started.
- Admin DPAPI key created successfully. Real QA license issued and
  accepted on Admin-PC for DUO-ADMIN-QA, edition DUO_PRO,
  exp=0 (perpetual), file placed in LOCALAPPDATA OUTSIDE repo.
- No Smaart process was started, no generator/capture, no audio I/O,
  no takeover. Already running overlay (PIDs 31652,29196) not restarted.
- Existing unrelated dirty/untracked files are preserved.

## Operator workflow — same local source

PowerShell from source folder, using known Python env:

$py = 'D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe'
& $py remix_duo_license_cli_v874.py machine
& $py remix_duo_license_cli_v874.py status
& $py remix_duo_license_admin_gui_v874.py

Admin-only script (key is already initialized on Admin-PC):
& $py remix_duo_issuer_admin_v874.py public
& $py remix_duo_issuer_admin_v874.py issue --machine 'DUO2-0123456789ABCDEF0123456789ABCDEF' --license-id ORDER001 --customer 'Khach hang' --days 365 --output 'C:\Somewhere\customer.lic'

Customer:
- Starts Duo, sees Machine ID, copies ID to issuer/admin, receives LIC1.
- Pastes LIC1 into activation dialog; verified signed token persisted
  atomically to the user profile. Subsequent startup skips dialog.
- CLI alternative: python remix_duo_license_cli_v874.py activate
  --file 'C:\path\customer.lic'

## Release gates and limits

PASS: offline signature verification; product/Windows/device binding;
expiry/perpetual; startup gate in source; admin issuance + independent
private key; QA installation on Admin-PC; all 91 tests.
HOLD: packaged Windows EXE/installer QA with PyInstaller (must include
cryptography, verifier, pinned public key, and exclude both admin-only
issuer scripts). No installer or distribution run occurred.
HOLD: remote online activation/revocation, seat counts, lost-device
transfer, trusted clock, periodic verification, real-server ledger sync.
Offline tokens cannot be instantly revoked; Windows clock can be rolled
back without trusted online time. A Python file can be patched: signed
tokens stop trivial edits but do not constitute anti-tamper protection.
HOLD: activation-dialog invalid-license physical GUI walkthrough; do
not claim a physical GUI run merely from offscreen gate proof.

## Important safety/security

- Do not copy, Git add or distribute private .dpapi file or issued keys.
- Do not bundle/admin ship issuer_* or license_admin_gui_* files.
- Never generate/publish a production key with private key in the client.
- Keep GUI source only in existing folder; Git commit targeted changes.
- The live Smaart TF API and Mag/Phase parity remain separate HOLD gates.
