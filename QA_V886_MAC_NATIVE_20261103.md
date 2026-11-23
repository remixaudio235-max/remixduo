# V8.86 — native Mac build, installation and activation evidence

Exact development source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_86_MAC_NATIVE_QA`.
Canonical runtime: `src/remix_duo`. V8.84 Windows installation and V8.85 source
are preserved. **The complete Mac parity goal is not yet achieved.** This is a
working licensed offline QA build with native diagnostic services, not a public
release or accepted native Smaart overlay.

## Concrete artifacts on the user's MacBook Air

- Native host: arm64, macOS27.0.1, Python3.11.9; installed Smaart Suite9.6.0.
- Source/build host directory:
  `/Users/dinhtran/RemiX_Duo_Build/V886/source-78cf9019296c`.
- Installed fresh from mounted DMG:
  `/Users/dinhtran/Applications/RemiXDuo_V886_QA.app`.
- Easy-to-find installer:
  `/Users/dinhtran/Desktop/RemiXDuo-8.86-arm64-QA.dmg`.
- DMG73,854,110bytes, SHA256
  `1aa6ae6852074ce84dffafcdf856a75c4e4467707f286a3a5471a7d728107a7d`.
- Runtime source digest (matches Windows canonical source):
  `31e2afc6c0ee809637edf7d877020a3c33320b0da8188f755b9306d1b6768e66`.
- 222 Mach-O binaries audited for arm64; local ad-hoc `codesign --verify
  --deep --strict` passed. This is not Developer ID/notarization evidence.
- Installed app selfcheck from CWD `/`: exit0, all resources present. First
  actual frozen build exposed missing logos; explicit resource bundling fixed
  it, then rebuilt and rechecked. No older binary was substituted.
- Native dependency versions retained in
  `packaging/macos/requirements-arm64-tested.txt`.

## What changed

- Lazy native AppKit/Quartz window discovery validates Smaart bundle ID,
  version, PID/start identity and CGWindow ID; it rejects helpers/tiny windows.
- Read-only AX traversal has a node/time budget and messaging timeout. Real
  Smaart supplied232 generic AXRow elements; neither highlight nor AXEnabled
  is treated as trace visibility. Missing/partial/offscreen/unknown state
  fails closed. No mtime-sorted file mapping was copied from the old Swift app.
- Screen-only ScreenCaptureKit capture (macOS14+ adapter), audio/cursor off,
  explicit source/destination sizing, timeout/late callback protection and
  before/after window/geometry/freshness validation. macOS13 currently supports
  offline workspace; a native SCStream13 adapter remains unimplemented.
- Separate bounded workers for geometry and AX selection. Slow selection
  cannot queue repeated scans or block geometry/Qt. Old-process completions
  are rejected; manual offline results are independent of native diagnostics.
- `probe_mac_native.py` produces read-only AX/capture diagnostics, no scroll,
  clicks, generator, soundcard or DSP writes.
- Default pytest collection now selects portable tests and avoids executing
  legacy Windows GUI scripts. Legacy Windows runner remains explicit.
- Reproducible source-only export with SHA256 manifest excludes caches,
  build/dist, `.env`, private keys and licenses.
- Native Mac builder includes resources, version/minimum-OS metadata,
  architecture audit and signature verification. Release pipeline implements
  Developer ID signing, Keychain-profile notarization and stapling, guarded
  by both-architecture same-source acceptance receipts. No receipt fabricated.

## Test evidence and limits

| Scope | Result |
|---|---|
| Windows portable/shared contracts | 45 PASS,5.74s |
| Mac arm64 default portable suite | 43 PASS,2 Windows-only SKIP |
| Windows legacy source regression | 477 PASS,1 new-Windows-bundle SKIP,81.67s |
| Worker/gateway/actual bundled activation/admin script tests | 16 PASS |
| Mac bundle/222native binaries/resources/install-copy selfcheck | PASS in stated scope |
| Native Smaart identity + permission preflight + AX traversal | PASS read-only scope |
| Native Smaart screenshot | 1440x900,533395bytes,169ms frame age |
| Actual trace tick evidence | HOLD: AX provides generic rows, zero verified tick states |
| SUM/MagEQ/FIR native trace/axis overlays; gestures/Spaces | HOLD |
| Full normal GUI visual acceptance | HOLD: desktop repeatedly entered loginwindow |
| Mac Intel build/live acceptance | HOLD: no Intel host available |
| Developer ID/notarization/public release | HOLD: only Apple Development identities available |

`V886_MAC_EVIDENCE.json` retains the initial native/build/install records.
An AX tree being complete is not complete tick evidence; capture success is
not axis calibration, verified TF frames, or physical DSP acceptance.

## Production MAC licensing

- Worker `remix-duo-license`, correct account and existing D1 binding verified.
  Previous production script downloaded to ignored build storage for rollback;
  previous version `b7d745a7-ffaf-48c0-bc1c-9165cd156b9c`.
- Deployed version `ddee1525-2532-4f00-ad6a-e37b403975fb`; secrets/admin token
  retained, no secret rotation or database schema migration.
- MAC/fpv4/DUOM4 form support and strict registered-hardware checks added.
  Actual Worker tests verify signed MAC tokens, reject wrong platform/hardware
  before device mutation, and preserve WIN/v3.
- Fresh reviewer found mixed WIN/MAC same-phone selection regression. Repro
  observed403 for the older platform; fixed candidate selection by
  platform/profile/registered MAC and retained explicit license-ID precedence.
  Regression tests cover both creation orders and all four client routes.
- Admin JavaScript scope and pending-MAC form fill tested in a browser-like
  VM; no `$` outside its IIFE, MAC requests select fpv4 automatically.
- Actual public `/api/appinfo` and authorized admin health returned200.
- Temporary **one-day** internal license `QA-MAC-V886` issued for the user's
  MacBook Air only. Actual Mac online activation ACTIVE, atomic save succeeded,
  offline pinned-signature verification ACTIVE. Expires epoch1793766971.
  No existing customer license was changed. Server rejects unregistered MAC
  hardware403 `MACHINE_NOT_REGISTERED`.
- No admin credential, issuer seed or signed license token is stored in Git.
  Temporary credential/token response in the task's Node runtime was cleared.

## Runtime state / unresolved work

Windows: no Duo/Smaart launched; ACTIVE_SOURCE remains V8.84. Existing Windows
watchers8012/9056 untouched. Original V8.85 baseline420Python hashes unchanged.

Mac: old Swift overlayV7 PID99595 was not stopped or overwritten. Smaart main
PID18104, QuickLicense helper18110. New installed QA PID21042, CWD `/`, window
title `RemiX Duo 8.86 · TRF Offline Alpha`. This workspace starts no native
observer automatically; do not start diagnostic polling beside the old
observer. A task-owned blocked inspection probe18707 was stopped after exact
command-line verification; no Smaart/legacy overlay process was terminated.

Normal GUI launch created the correct native window, but subsequent capture
attempts found the Mac at `loginwindow`; visual GUI PASS is not claimed.
User was asked to unlock/keep screen on. Native tick/file identity, axes,
rendering/follow latency, permission revocation, fullscreen/Spaces and Intel
acceptance still require implementation/measurement. No automatic trace pair
was guessed. No Mac/public-release completion claim is justified yet.

## Execution decisions

1. Retain native tick/axis HOLD when real AX exposes only generic rows.
   Cost: automatic Smaart modes remain unavailable until trustworthy evidence
   and native rendering are implemented and verified.
2. Build/install a local ad-hoc QA artifact while Intel and Developer ID are
   unavailable. Cost: it is not a public or fully accepted Mac release.

## Next safe commands

Windows source-only checks (no GUI/audio):

```powershell
cd D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_86_MAC_NATIVE_QA
& D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe -m pytest -q
```

Mac app is in `~/Applications`; DMG is on Desktop. Unlock Mac before visual QA;
close the old overlay before native polling. Do not rescan historical folders.
Mac Intel/native release commands: `packaging/macos/README.md`.
