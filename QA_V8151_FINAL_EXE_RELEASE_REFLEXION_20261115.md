# V8.151 Final Windows EXE release Reflexion — 2026-11-15

## Verdict

**BLOCKED — do not ship the current EXE/installer.** Product logic and the
focused release subset are healthy, but provenance, production packaging,
version identity, signing and full regression gates are not release-grade.
No build, install, signing, publishing or production mutation was performed.

## Verified PASS

- Exact audited source: `windows_v8_87_MAC_OVERLAY_QA`, branch
  `qa/remix-duo-v873-native-tf-reader`, dirty working tree.
- Release/security/package/lifecycle/tick/shared/contracts subset:
  **164 PASS, 5 SKIP** in 284.23 s.
- Smaart 8 live V8.150: Auto EQ LF/HF and Auto FIR LF/HF visible.
- Existing current-source focused v8/geometry/UI: **41 PASS, 1 SKIP** and
  **21 PASS, 1 SKIP** from V8.149/V8.150.
- Read-only load evidence remains Suite PrintWindow 40x p95 34.49 ms and v8
  parser 1000x p95 34.371 ms. No audio/DSP path was modified by V8.149/150.

## P0 blockers

1. **Active source identity broken.** `ACTIVE_SOURCE.txt` still names
   `windows_v8_84_LOGIC_FIX_QA`, while audited/runtime source is V8.87 with
   V8.150 changes. Required `VERIFY_ACTIVE_BUILD.py` cannot start because its
   prescribed venv points to missing `C:\Users\Admin\...\python.exe`.
2. **No production build recipe.** `build_remix_duo_qa_v877.ps1` builds
   `RemiXDuo_QA` and deliberately injects `qa_runtime_hook_remix_duo_v877.py`.
   That hook sets `_remix_duo_qa_signed_build=True`, selects the local QA
   license branch, and explicitly states it must never ship commercially.
3. **Version identity stale.** `pyproject.toml=8.87.0`, package
   `__version__=8.87`, installer/product/output names all say QA V8.87, while
   accepted working behavior is V8.150/V8.151.
4. **Unsigned artifacts.** Existing setup and all three EXEs are NotSigned.
   They are old V8.87 QA artifacts, not builds of the current working tree.
5. **Full regression not green.** Latest aggregate legacy run is
   **607 PASS, 49 SKIP, 34 FAIL**. Most failures are dual-edition saved-Fs
   fixture assumptions plus one obsolete Toast ownership test, but a release
   gate cannot convert them to PASS without isolating/fixing the harness.
6. **Unreviewable provenance set.** The branch contains many modified and
   untracked files spanning historical QA families. There is no clean tagged
   release checkpoint or manifest proving which exact files enter the EXE.

## P1 blockers / acceptance debt

- Two Smaart 8 processes currently exist (PIDs 26500 and 28452). Duo correctly
  binds the visible foreground window, but release soak must begin from one
  controlled Smaart instance without stopping user software incidentally.
- Live Suite acceptance after the V8.149/150 changes is not repeated in this
  final reflection. Auto Phase 2-trace, EQ 1-trace, FIR 1-trace, HIDE/LIVE,
  crash recovery and 3/3 re-arm require one scripted, recorded matrix.
- Installer upgrade/uninstall/clean-machine tests and autostart single-instance
  behavior are not verified for a current production artifact.
- Authenticode certificate/timestamp chain, malware scan and clean Windows VM
  install evidence are absent.
- Windows EXE release does not prove the separate macOS Intel/arm64 gates.

## Existing artifact ledger (not releasable)

- Setup: 75,930,416 bytes, NotSigned,
  SHA256 `ABC9036E4007EF3C07AD6FB59C59E2859BC6EF8DA2BA7E2BECE9A6FCAD9F890B`.
- Main QA EXE: NotSigned,
  SHA256 `BD419AFC93CEAE6D1648B03C3D0CBB2B41EF455202C33F0BB0511458D4181FBC`.
- Watcher: NotSigned,
  SHA256 `700FBDF40709B8A762DA8CD434FC682812A994E1C2A68EDD3743FA49B4343958`.
- Setup helper: NotSigned,
  SHA256 `F742CD1639277A6DDE1755A91B9A27DF415C8861CB3FE8478BDF8F8A81C8AC26`.

## Required release sequence

1. Choose the public Windows version and establish a clean release checkpoint
   from the exact V8.150 source; update active-source provenance and repair the
   verifier environment.
2. Create a separate production build recipe/name/installer with **no QA
   runtime hook**, retaining Cloudflare commercial license fail-closed logic.
3. Make version identity single-source and assert it across Python metadata,
   UI, EXE resources, installer and artifact filename.
4. Repair/isolate the dual-edition legacy test harness and reach zero
   FAIL/ERROR; rerun focused, shared/contracts, package and full legacy gates.
5. Run the live Smaart 8 + Suite matrix and bounded soak from one instance of
   each edition, with no Generator/DSP writes.
6. Build from the clean checkpoint; run frozen selfchecks, clean VM
   install/upgrade/uninstall/autostart tests; sign EXEs and setup with trusted
   timestamp; verify signature and publish SHA256 manifest.

