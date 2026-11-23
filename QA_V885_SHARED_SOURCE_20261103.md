# V8.85 shared-source migration — 2026-11-03

Exact development source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_85_CROSS_PLATFORM_QA`.
User approved the shared-source design on 2026-11-03. This QA is an intermediate
migration, not a completed Mac release or replacement for installed V8.84.

## Implemented

- Canonical `src/remix_duo/core`: saved TRF parsing, physical complex SUM,
  Auto Phase solver, Auto EQ unified engine/helpers, FIR MAG/Phase design,
  display smoothing, FIR physical preview and DSP-file export. Legacy names
  alias the same Python modules, preserving private names and monkeypatches.
- Shared Qt plot/toast/style used by the existing Windows tool dialogs and
  portable offline workspace. Shared workspace runs calculations on one worker,
  snapshots arrays and drops old results after input changes/close. Fs must be
  explicitly selected; imported TRFs are never represented as live native ticks.
- Platform contracts: process/window identity, complete fresh visible selection
  evidence, logical/physical coordinate transform, app paths, capability status
  and real instance lease. Existing Windows observer keeps its mutex name.
- Windows fingerprint/path bytes preserved. Mac fingerprint is product-scoped,
  fpv4 and CPU-architecture independent. License verifier/client/activation UI
  are shared; MAC tokens must be signed MAC/fpv4, not WIN or ANY. Existing WIN
  v2/v3 remains compatible. No signing/admin secret added to the app.
- `python -m remix_duo` / `run_remix_duo.py`: license-gated offline Qt alpha.
  `--selfcheck` opens no GUI and makes no license mutation/network request.
- Native Mac preflight and alpha .app/.dmg builder for separate x86_64/arm64.
  Rejects Windows cross-compilation, Rosetta, wrong architecture and macOS <13.
  Public `--release` fails closed pending native/signing/notarization acceptance.

## Evidence

- Shared/contract tests: **23 PASS**, including real Windows cross-process
  mutex contention/release, signed MAC/WIN separation, stale async completion,
  GUI heartbeat and independent-CWD resource check. These are Windows-hosted
  unit/offscreen/contract tests; they are not native Mac evidence.
- Windows V8.84 baseline suite on migrated source: **477 PASS, 1 SKIPPED**,
  90.37 seconds. The skipped test is the frozen Windows asset check: V8.85
  has no new EXE bundle. Its initial missing-artifact failure is recorded;
  no V8.84 binary was copied in to manufacture V8.85 packaging evidence.
- V8.84 baseline **378 Python file hashes unchanged**.
- Installed V8.84 EXE unchanged SHA256:
  `83F24E297F4AA194828B9C74F6A23C1E42E2013E74E40EA8FE2C00D35915747B`.
- Shared selfcheck from unrelated CWD: exit0, no missing resources; native HOLD
  explicit. Mac build preflight on Windows rejects as designed.
- Active-source guard still points at V8.84; HOLD NO_ACTIVE_OVERLAY and
  NO_SMAART_WINDOW. No Duo/Smaart process running. Existing watchers8012/9056
  remain untouched, args point to V8.27 `smaart_autostart_v875.py --watch`.
  Their CWD was not re-read in this final process snapshot; no cutover attempted.

## Remaining HOLD / next implementation

1. Existing native Windows overlay is still a legacy integration facade.
   New common logic belongs in `src/remix_duo`; do not edit compatibility aliases
   or clone algorithms into another OS folder. Additional dialog/workflow
   migration should consume platform services rather than importing Win32.
2. macOS native discovery/AX/ScreenCaptureKit/tick verification and native
   overlay renderer are **not implemented/accepted**. `MacServices` reports HOLD
   and refuses selection. Pixel transforms are contracts, not measured Retina
   calibration. Never substitute cached Windows ticks/templates or saved TRFs.
3. Actual Mac Intel and Apple Silicon dependency install/build/clean-launch,
   permission denial, window gestures and Suite9 trace/axis QA remain HOLD.
4. Real license issuer must add MAC/fpv4 issuance/activation. No production
   Cloudflare deployment or admin credential change occurred in this migration.
5. Windows V8.85 frozen build and live regression remain HOLD. No installer,
   app restart, license reset, audio route, generator or DSP write performed.
6. Public Mac release requires Developer ID/hardened runtime, notarization,
   staple, stable production bundle ID and native clean-machine verification.

## Safe commands

Windows read-only/selfcheck (no GUI):

```powershell
cd D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_85_CROSS_PLATFORM_QA
& D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe run_remix_duo.py --selfcheck
& D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe run_shared_tests.py
```

Native Mac setup/build commands and all release gates:
`packaging/macos/README.md`. Keep ACTIVE_SOURCE and installed V8.84 unchanged
until a separately controlled Windows live cutover is accepted.

## Independent review and fixes

Fresh reviewer found two Important P2 bugs in the new offline workspace:
FIR preview used the filter response rather than physical source×filter TF;
unused TRF2 blocked EQ/FIR by validating its Nyquist and polluted provenance.
Both regression tests were observed failing, then passed after fixes. FIR
physical cascade now shares the same core helper with the Windows preview;
non-Phase requests drop reference before validation/snapshot/export.
No Critical or deferred minor findings. Reviewer declined native Mac/signing/
issuer/frozen acceptance; those remain HOLD, never inferred from tests.

## Execution decisions retained from ledger

- Used a new QA copy allowed by AGENTS instead of a worktree over dirty files;
  preserved installed V8.84 and ACTIVE_SOURCE. Cost: select QA path explicitly.
- Used PowerShell/Python durable ledger in place of Bash skill helpers on
  Windows. Cost: no helper-generated task briefs; plan and evidence retained.
- Absent new frozen Windows artifact is explicit skipped HOLD, not validated
  against copied old binaries. Cost: new bundle remains unverified.
- Shared offline alpha is the staged migration; native Windows facade remains.
  Cost: no current Mac native parity; do not replace installed Windows.
- Reviewer's declined native Mac/capture/AX/signing/issuer/frozen judgments stay
  HOLD. Cost: real devices, real issuer and native builds still required.

Deferred minor: inherited Windows installer/title version metadata still says
8.84; before any V8.85 Windows build/cutover, update it and verify bundle identity.
No V8.85 Windows bundle is claimed by this QA.
