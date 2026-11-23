# RemiX Duo macOS — offline alpha build gate

One canonical source: `src/remix_duo`. Windows legacy overlay imports the same
DSP modules through compatibility aliases. The portable workspace is explicitly
offline. AppKit/Quartz discovery, bounded read-only AX traversal and ScreenCaptureKit
screenshots are implemented and probed on arm64. Verified native tick identity,
axis calibration and Smaart overlay workflow remain HOLD. The screenshot adapter
requires macOS14+; macOS13 currently runs the offline workspace only.

On a **native Intel Mac**, macOS 13+, Python 3.11:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install '.[macos,test,build]'
.venv/bin/python run_shared_tests.py
.venv/bin/python packaging/macos/build.py --arch x86_64 --check
.venv/bin/python packaging/macos/build.py --arch x86_64
```

On an **Apple Silicon Mac**, use native arm64 Python and replace `x86_64`
with `arm64`. Rosetta and cross-compilation are rejected. Separate native
DMGs are intentional; do not lipo-merge frozen Python executables.

Local alpha artifacts are not a public release. This script does not bypass
Gatekeeper or grant Screen Recording/Accessibility permissions. `--release`
refuses until the remaining gates are implemented and evidenced:

- Real Intel and Apple Silicon clean install/launch, Qt/plugin/resource checks.
- Issuer support and signed MAC/fpv4 token activation on the real server;
  existing WIN licenses remain unchanged. MAC/fpv4 support is deployed and actual
  one-day QA activation/offline verification passed; public lifecycle acceptance
  on both architectures is still separate.
- macOS window discovery, process identity, AX visible tick states and complete
  scan proof; ScreenCaptureKit screen-only frames with timestamps and consent.
- Retina/mixed-DPI/multimonitor geometry, move/resize/minimize/background,
  native axis roles and each EQ/FIR overlay tested against actual Suite 9.
- No stale/offscreen selected trace accepted; permission denial fails closed.
- Native architecture dependency audit, stable production bundle identifier,
  Developer ID hardened-runtime signing, notarization and stapling; verify on
  a fresh user account. Credentials belong in build environment, never source.

Windows entry remains `overlay_v7.py`; portable alpha entry is
`run_remix_duo.py` or installed package `python -m remix_duo`. Both gate usage
through signed licenses. `--selfcheck` is read-only and opens no GUI.


V8.86 actual arm64 artifact: `~/Desktop/RemiXDuo-8.86-arm64-QA.dmg` on the user's
Mac. Installed QA: `~/Applications/RemiXDuo_V886_QA.app`. Source/work directory:
`~/RemiX_Duo_Build/V886/source-78cf9019296c`. See QA_V886_MAC_NATIVE_20261103.md.
Tested dependency versions are in requirements-arm64-tested.txt; they are native
arm64 evidence, not an Intel test result. Default `python -m pytest` now collects
only portable suites; use the explicit Windows runner for legacy regression.

When actual native acceptance is complete on both CPUs, public release uses:

```sh
.venv/bin/python packaging/macos/build.py --arch arm64 --release \
  --receipt acceptance-arm64.json --receipt acceptance-x86_64.json \
  --identity 'Developer ID Application: YOUR TEAM' --notary-profile YOUR_KEYCHAIN_PROFILE
```

Receipts must refer to the same current runtime source digest and record actual
shared-test/frozen-selfcheck/native-Smaart/clean-install acceptance. Generated QA
build evidence deliberately records native_smaart=false and clean_install=false;
do not change these to bypass testing. Signing credentials belong in Keychain.
The builder signs dependencies through PyInstaller, seals/verifies the app, signs
the DMG, submits with notarytool and staples/validates only after Accepted status.
No notarization or Intel success is claimed for the current QA.
