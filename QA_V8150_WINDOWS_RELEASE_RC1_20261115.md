# RemiX Duo V8.150 Windows Release RC1 — 2026-11-15

## Exact source

- Release candidate: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_150_RELEASE_RC1`
- Version: `8.150.0` (`RemiX Duo 8.150`)
- Source baseline copied from `windows_v8_87_MAC_OVERLAY_QA` without prior
  `dist`, `build`, pytest cache, Python cache or bytecode artifacts.
- The accepted/running source was not overwritten and no process was stopped.

## Release gates

| Gate | Result | Evidence / reason |
|---|---|---|
| Version consistency | PASS | `pyproject.toml`, package version and product title agree on V8.150. |
| Clean source checkpoint | PASS | New RC directory; historical QA snapshots remain unchanged. |
| Production recipe without QA override | PASS | `production_runtime_hook_v8150.py`; regression proves `_remix_duo_qa_signed_build` is not set. |
| Source/package/shared/contracts regression | PASS | 124 passed, 5 skipped, 0 failed. |
| Full automated RC regression | PASS | 762 passed, 54 skipped, 0 failed in 137.71 s after the production V3/V4 license migration. Three historical operator probes are deliberately excluded because they mutate/observe live UI at import time. |
| MagEQ render performance regression | PASS | Three consecutive CPU p95 results: 25.00, 20.31 and 25.00 ms. |
| Smaart 8 live matrix | PARTIAL PASS | Prior V8.150 live read-only evidence covers trace detection and Auto EQ/FIR LF/HF. Current PID 26500 is Smaart 8. No RC cutover was performed. |
| Smaart Suite live matrix | HOLD | Smaart Suite is not currently running; it was not launched incidentally. |
| Production online license | PASS (source) | Frozen production now uses the shared V3/V4 gate and pinned endpoint/key. Focused auth/package gate: 157 passed, 4 skipped; final focused check: 14 passed. Build environment verification remains HOLD. |
| GitHub application updater | PASS (source) | Dedicated public repo `remixaudio235-max/remixduo`; strict stable SemVer/URL/repo validation, background check, cache and Vietnamese notify-only prompt. Public probe returned `UP_TO_DATE`. |
| PyInstaller/Inno production build | PASS (unsigned RC) | Dedicated Python 3.11 build venv, PyInstaller 6.22.3 and Inno Setup 6.7.3. Frozen self-checks all exit 0. Branded installer SHA-256 `C3DE46C1F42786EBDE1B6C9B967662DF8994431D2FF22E646B90F930EB6AF120`. |
| Clean-VM install/uninstall | HOLD (reboot required) | Windows Sandbox feature was enabled without reboot. The host must be restarted before the isolated install/uninstall matrix can run. No reboot was performed while Smaart is active. |
| Authenticode signing | HOLD | No code-signing certificate with private key is available in CurrentUser\My. |
| Signed SHA-256 artifact manifest | HOLD | `sign_release_v8150.ps1` produces it only after every release artifact is signed and verified. |

## Runtime identity (read-only)

- Smaart 8: PID 26500, `C:\Program Files (x86)\Smaart 8\Smaart.exe`.
- Overlay process tree: PIDs 32256/18836; process CWD audit reports
  `windows_v8_87_MAC_OVERLAY_QA`.
- Watcher process tree: PIDs 31456/39792.
- `ACTIVE_SOURCE.txt` still names `windows_v8_84_LOGIC_FIX_QA`; this is a
  provenance mismatch and must be resolved during an authorized cutover, not
  silently changed while the accepted runtime is active.

## Release scripts

- `release_preflight_v8150.ps1`: reports toolchain, cloud, certificate and VM gates.
- `build_remix_duo_production_v8150.ps1`: fail-closed production build; no QA hook.
- `sign_release_v8150.ps1`: signs EXE/setup, verifies Authenticode and emits
  `dist\RELEASE_ARTIFACTS_V8.150.sha256`.

## GitHub updater evidence

- Repository: `https://github.com/remixaudio235-max/remixduo` (public and empty
  at verification time).
- Focused updater + production gate: 25 passed, 0 failed.
- Shared/contracts: 114 passed, 4 skipped, 0 failed.
- Full safe RC: 782 passed, 54 skipped, 0 failed in 226.36 s.
- GUI-thread scheduling benchmark with a 300 ms fake worker: 0.692 ms.
- Public API probe: `UP_TO_DATE`, no notification, as expected for an empty repo.
- Final source manifest after adding the release ICO assets: 602
  files; SHA-256
  `F5BA1D79F3D6CBCDB5462C79BD916F2393F96D29E4CBDBA4CA637A0167B317F5`.
- Frozen EXE self-checks PASS. Native Smaart notification appearance remains
  HOLD until the authorized live matrix/cutover gate.

## Windows production build evidence

- Dedicated build environment: `D:\REMIX_AUTO_ALIGN_V6_DEV\.venv-v8150-build`
  (Python 3.11.9, PyInstaller 6.22.3, PyQt6 6.11.0, NumPy 1.26.4,
  SciPy 1.17.1, cryptography 46.0.7 and cffi 2.1.1).
- The first clean-env focused gate exposed a missing `psutil` package
  dependency. `pyproject.toml` and the production-release regression now
  require it; the repaired focused gate is 25 passed, 0 failed.
- Frozen `--qt-selfcheck`, `--online-license-selfcheck`,
  `--updater-selfcheck` and `--package-selfcheck` each exit 0.
- Main EXE: 13,249,390 bytes; SHA-256
  `3295359730A7E44220E794FFC898B901E32F235B42F57835C861DDDF2DCF4499`.
- Watcher EXE: 7,932,801 bytes; SHA-256
  `C578981366ABFBDDBE52E226EC59BEC940C7CC170CE18C4379F7CD60E6F18D39`.
- Setup helper EXE: 7,930,236 bytes; SHA-256
  `958AC2466EC0B023248063454334018C9B72A56945B0557887346579305D0B80`.
- Inno installer: 72,109,288 bytes; SHA-256
  `C3DE46C1F42786EBDE1B6C9B967662DF8994431D2FF22E646B90F930EB6AF120`.
- Supplied `icon.ico` is embedded in all three application executables;
  supplied `logo.ico` is the Inno Setup icon and packaged Qt window icon.
  Windows resource extraction returned a valid 32x32 associated icon for all
  four artifacts. `logo.ico` exists in the frozen package resources.
- Focused release/package regression: 10 passed, 1 skipped, 0 failed.
- Authenticode status for all four artifacts is `NotSigned`. These are internal
  RC artifacts only; release signing remains HOLD until a trusted certificate
  with private key is supplied locally.

## Safe next action

Do not cut over the running overlay yet. Restart the host only in an authorized
maintenance window, then run installer install/start/uninstall in Windows
Sandbox. Run the Smaart 8/Suite read-only matrix before signing. Supply/import a
trusted release certificate locally (never put its password in project files or
chat), then run the fail-closed signing recipe and publish the signed SHA-256
manifest.

## 2026-11-15 installed Auto EQ presentation repair + rebuilt RC

- Installed `RemiXDuo.exe` was confirmed to match the prior RC, while the
  selected trace, LF/HF range and automatic PEQ/gain limits were all present.
  The PEQ solver was not blocked: the delay was in native MagEQ presentation.
- Root cause: the first native fit repeated the slow UIA plot-role discovery
  even though the overlay already held a verified Phase/Magnitude layout. A
  direct read-only probe on `full 30 bien-1.trf` took about 37 seconds.
- `native_eq_mag_v06.py` now accepts the current engine layout only as a
  geometry hint, then re-proves Phase/Magnitude roles against a fresh native
  Smaart `PrintWindow` frame before using it. Existing source, colour, Y-axis
  and identity gates remain fail-closed.
- Live read-only benchmark after the repair: 1,768.6 ms; cyan trace score
  0.952; 228 accepted bins. Focused/native regression: 68 passed, 1
  environment-dependent Fs fixture deselected, 0 failed. The new fast-path
  regression first failed before the patch and passes afterward.
- The supplied artwork was present in the old PE but too small at Explorer
  sizes. `remixduo_app.ico` is an optimized derivative of that same artwork;
  it is embedded in all three application EXEs, the Inno installer and the Qt
  package. Associated-icon extraction from the rebuilt main EXE returned a
  valid 32x32 icon.
- Rebuilt main EXE: 13,237,317 bytes; SHA-256
  `93B15F1C374571B5636D90F81E74BC652287B6615FF64AD218A497624781491B`.
- Rebuilt watcher: 7,991,051 bytes; SHA-256
  `9C0EFD4D33E7578BC0E1D7E35E1251E9F29F01E815F99B980D8340E9A712153E`.
- Rebuilt setup helper: 7,985,855 bytes; SHA-256
  `5D2A9F12894BB45ED588B9F0EA9DF2D1ECA4DC364F67B745D698D8638250ABF8`.
- Rebuilt installer: 72,202,552 bytes; SHA-256
  `F2E4F4BBEC858D09A12ACB76A6F6AF312C9E0DEDD71350180239C09E7BBF4EBC`.
- Frozen `--qt-selfcheck`, `--online-license-selfcheck`,
  `--updater-selfcheck` and `--package-selfcheck` each exit 0. All four EXE
  artifacts remain `NotSigned`; this is still an internal RC.
- Source manifest: 604 entries, validation clean; SHA-256
  `2276F69B979E2E141DA3D59FFEDDC1D14AE2989FAD272D75300EF862BDA6D571`.
- The currently installed/running application has not been replaced during
  this QA. Live installed Auto EQ rendering remains HOLD until an authorized
  exact-process cutover; Smaart itself must remain running and untouched.

## 2026-11-15 frozen DSP build gate

- Source operation alone was not accepted as proof for the installed build.
  The production recipe previously checked Qt, licensing, updater and package
  integrity but did not execute either DSP generator inside the frozen EXE.
- Added fail-closed `--autoeq-selfcheck` and `--autofir-selfcheck` gates before
  Inno compilation. The Auto EQ gate runs the packaged unified solver and must
  produce `PREVIEW_READY` plus at least one PEQ. The Auto FIR gate uses low
  coherence (0.20) and must still return 1024 finite taps in relaxed mode.
- Red/green evidence: the production test failed before the gates existed;
  after implementation the focused DSP/release collection is 25 passed,
  0 failed. Source-hook Auto EQ/FIR exits are 0/0.
- Rebuilt frozen EXE independently passed all six gates: Qt, online license,
  updater, Auto EQ, Auto FIR and package, each exit 0. Therefore low coherence
  remains informational and cannot block the frozen FIR smoke path.
- Final main EXE: 13,238,776 bytes; SHA-256
  `4B006E049DE3A953A6BA2EEF275B15E4ABE8D76A6BA54F03FB374F1E33C1DC62`.
- Final installer: 72,199,981 bytes; SHA-256
  `5DF02B17EA900B326849861C713CCCD81237EE02E7E5EA9BB208DDBC29BFB476`.
- Both artifacts remain `NotSigned`. Native installed interaction with the
  user's selected Smaart trace remains HOLD until the old app is closed and
  this exact installer is installed; no Smaart process was stopped.

## 2026-11-15 direct frozen Auto FIR reproduction

- Safely stopped only the exact V8.87 watcher/overlay tree, kept Smaart 8 PID
  26500 and Smaart Suite PID 15384 running, and launched the production EXE
  directly. The log proved the FIR solver repeatedly succeeded (`FIR_OK`,
  512/2048/4096 taps with improved Excess RMS), then the GUI immediately
  cleared the approved result through `refresh_sources` or a range callback.
- Root cause: a transient observer tick plus a temporarily unavailable saved
  Fs snapshot was treated as a confirmed source change. Coherence warnings and
  the taps generator were not the blocker. Unsupported native Mag smoothing
  can still hide the overlay, but must not delete computed coefficients.
- `FIRDialog.refresh_sources` now retains immutable computed taps when both
  tick and Fs scans are temporarily unavailable. Preview/export remain
  fail-closed until the same trace/Fs proof returns; a real trace, file, Fs,
  mode, range or tap change still invalidates the result.
- Red/green regression reproduced `V8129_FIR_DISCARD` before the patch and
  preserves the result afterward. Focused FIR/re-arm/coherence gate:
  24 passed, 0 failed.
- Rebuilt frozen Auto EQ, Auto FIR and package self-checks each exit 0. The
  patched EXE is now running directly as PID 25796.
- Final EXE: 13,238,793 bytes; SHA-256
  `363A778D000C11793F485FC82A28F0495763EE2DD013586C4757C1BAD148867A`.
- Final installer: 72,201,637 bytes; SHA-256
  `3925A71FFCC2C5474F3C089A3BF3CDA92ED7AB22094B948F659C1A5E4C7DDDF2`.
  It remains unsigned. Final operator click/render confirmation is still HOLD.

## 2026-11-15 FIR native smoothing-ID repair

- The live frozen log proves the FIR solver generated valid 512/2048-tap
  results (`V8124_FIR_OK`), but native rendering remained `PhaseFIR HOLD`.
- Read-only Smaart evidence reports visible Magnitude smoothing `1/12 Oct`
  with saved `smoothingId=4`. The native gate mapped ID 4 to 1/12 but did not
  include it in the verified-ID set, so a valid preview was hidden.
- `smaart_smooth_sync_v811.py` now treats ID 4 as verified. The direct probe
  returns `mag_oct=1/12`, `phase_oct=1/6`, both verified. Focused mapping,
  native-frame, no-blink, retention and coherence tests: 40 passed, 0 failed.
- Production rebuild completed and all six frozen self-checks passed before
  Inno compilation. Main EXE: 13,238,799 bytes; SHA-256
  `CF6BE33F18FCDD57CFF3F34BEA35D48264E153EAED51E753CA0131704AF51F2D`.
  Installer SHA-256:
  `5F1C2E586BF83E3B1F63F43348601F8E3AD6866B73A5698533A71A2C89977EAF`.
- The rebuilt EXE is running directly as PID 24324. No post-rebuild `TẠO FIR`
  event is present in the log yet, so final native line confirmation is HOLD.

## 2026-11-15 FIR first-frame UIA timeout repair

- Post-build live click generated 512 valid taps and improved Excess RMS from
  10.2° to 7.8°, but `PhaseFIR` remained HOLD. Thread evidence showed the
  first native frame blocked in UIA plot discovery beyond the bounded display
  proof lifetime.
- FIR native registration now uses the engine's already verified Phase/Mag
  rectangles only as a geometry hint, then re-proves the Mag title on a fresh
  native PrintWindow image. Trace colour, source fit, dB axis and phase fit
  remain mandatory; the full UIA scan remains the fallback.
- New fast-path regression proves zero UIA calls with fresh title/source/phase
  verification. Focused affected gate: 34 passed, 0 failed. Production build
  and six frozen self-checks completed successfully.
- New EXE is running as PID 33636; SHA-256
  `1DAE8450CE2703AABE5000BBA47B1A8EE716F5CBABFB35B9FB1184DC373B97DD`.
  Installer SHA-256:
  `6FAA9F7667894E6F8B587B6E3AB684201FA755069461B8260199FFB60F7DF756`.
  Final post-build click/line evidence remains HOLD.

## 2026-11-15 packaged FIR native asset repair — LIVE PASS

- Direct UI Automation clicked `Auto FIR` and `Tạo bộ lọc FIR` on the running
  production EXE while Smaart Suite HWND 277613638 remained running.
- The packaged worker traceback isolated the blocker: PyInstaller omitted
  `smaart_title_signatures_v03.npz`; `detect_magnitude_rect()` therefore raised
  `FileNotFoundError` after valid taps had already been designed.
- The production build now bundles the 693-byte native title signature and the
  frozen Qt self-check requires it. Regression: 33 passed, 0 failed.
- Final clean EXE PID 2656 live evidence: `V8124_FIR_OK phase 512 500 2500`,
  Excess RMS 10.2°→7.8°, then `PhaseFIR PASS`. Coherence 4% remains warning-only.
- Final EXE: 13,239,935 bytes; SHA-256
  `CCB83B61A22C4F88AD807CBDF503B804AEB774B3A7E26B4C0246113317B4E3AA`.
- Final unsigned installer: 72,205,932 bytes; SHA-256
  `F3EC388EEE4C1EE7576CD0B34C11C41DBB5A2C311BD7F82D17E0536AD88E2545`.

## 2026-11-15 final FIR stability and all-smoothing matrix

- A fresh PID 28372 log reproduced the remaining transition: five valid FIR
  designs reached PASS, but `hub_hidden` still forced PASS to HOLD. The native
  state machine now treats panel/tool/workspace/minimize/foreground loss as a
  presentation-proof pause and retains the last independently verified frame.
- Smaart smoothing 1/3, 1/6, 1/12, 1/24 and 1/48 Oct is supported across Auto
  Phase, Auto EQ and Auto FIR. Changing smoothing rerasterizes result lines;
  it never changes Auto Phase raw inputs, PEQ coefficients or FIR taps.
- Focused renderer/smoothing gate passed 50 tests. Final explicit full suite:
  799 passed, 54 skipped, 0 failed in 142.66 s.
- Production build completed; all six frozen self-checks exited 0. Active-build
  guard PASS for production EXE PID 33356. Source manifest validation:
  `MANIFEST_BAD_COUNT=0`.
- Final EXE: 13,241,910 bytes; SHA-256
  `FAEF3E05592AF101CC3D78F98A96A39DC91A47AA589C586E3D5A4CAAF0E5E798`.
- Final installer: 72,203,811 bytes; SHA-256
  `C375C40D20665D132B7261E2DC0E25EF73D3F323E4CFB8A89C4874CC6414BFB4`.
- Live Auto EQ/Auto Phase evidence on this final PID is HOLD because the Smaart
  HWND was minimized and the frameless RemiX overlay exposes no separate
  automation HWND. No duplicate Smaart was launched. Clean-VM is HOLD pending
  reboot; EXE/setup are NotSigned and the certificate stores contain no usable
  code-signing private key.

## 2026-11-15 Cython protected production build

- Added minimal `main.py`. Production does not statically import or package
  `overlay_v7`; it verifies `CYTHON_PROTECTED_MANIFEST.json`, loads protected
  extensions, then calls `_remixduo_native.main()`.
- Cython 3.1.5 compiled 25 modules covering the main application, Auto EQ/FIR
  core, filter/trace logic, online licensing and GitHub updater.
- Integrity/native-load failure is fail-closed and displays the exact requested
  message `Fuckyou`. Self-check uses exit 29 instead of a blocking modal.
- Cython, Qt, online licensing, updater, Auto EQ, Auto FIR and package frozen
  self-checks all exited 0.
- Archive result: `ARCHIVE_OVERLAY_V7_HITS=0`; loose source/bytecode result:
  `LOOSE_OVERLAY_SOURCE_COUNT=0`; native entry count: 1. Full regression:
  799 passed, 54 skipped, 0 failed in 161.55 s.
- EXE SHA-256: `07046B557EA027504F43C04D60CA369929BF588BAA0F3178545095C91CA6651C`.
  Setup SHA-256: `B4E572538A2278E21858FA6F04D1A877E4FC3CA931569438B4143A215F59B1B3`.
- Both artifacts are `NotSigned`. Clean-VM and fresh live Smaart interaction are
  HOLD. The mandatory verifier virtualenv is broken; valid Python reaches
  `GUARD HOLD:NO_ACTIVE_OVERLAY`, consistent with no running overlay.
- The bootstrap and some dependencies remain Python bytecode by design. Cython
  materially raises RE cost; no client executable guarantees absolute anti-RE.
