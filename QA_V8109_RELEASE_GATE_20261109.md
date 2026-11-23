# RemiX Duo V8.109 — Release Gate Run (2026-11-09, no Smaart)

## Verdict: NOT RELEASABLE — HOLD
Offline gates that can run without Smaart: PASS. Release gates that need
Smaart data, live Smaart, code signing and a correct version label: HOLD/FAIL.
Installed Windows V8.84 remains the production fallback and was not touched.

## Exact source
- D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
- Branch qa/remix-duo-v873-native-tf-reader, HEAD 591854b (V8.109)
- Working tree also carries 2 uncommitted, pre-existing shared-source edits not
  made in this run: src/remix_duo/entry.py (offline-workspace lock name) and
  src/remix_duo/ui/workspace.py (title uses __version__). Gates ran on this tree.
- Preflight: no pythonw / RemiX overlay / Smaart process running; Smaart 9 is
  installed (C:\Program Files\Smaart Suite) but C:\Users\Admin\Documents has
  no "Smaart Suite" data folder. No GUI, Smaart, generator, soundcard, DSP or
  installer was launched. Nothing was installed.

## Gate results (logs in _qa_outputs/v8109_release_gate/)
| Gate | Result | Evidence |
|---|---|---|
| Legacy unit/offscreen runner (run_unit_qa_v884.ps1) | **HOLD** 423 PASS, 74 SKIP, 44 FAIL, 27 ERROR | unit_runner.txt |
| — root cause of all 71 FAIL/ERROR | missing fixture data, not code | 56× "Smaart index.xml missing"; 15× missing `0 delay-1/-2.trf`, `4,8 ms delay-1.trf` under %USERPROFILE%\Documents\Smaart Suite\...\Session Data |
| — fixture search | none found | `*delay-1.trf` searched on C:\Users\Admin, D:, E:, F: |
| Shared + contracts (run_shared_tests.py) | PASS 72, SKIP 6 | shared_contracts.txt; 6 skips = "Reference TRF not on this machine" |
| PyInstaller GUI / watcher / setup helper (--clean) | PASS | build.txt EXIT=0 |
| Packaged --qt-selfcheck / --online-license-selfcheck / --package-selfcheck | PASS 0 / 0 / 0 (license ACTIVE) | build.txt |
| Inno Setup compile | PASS | dist\installer\RemiXDuo_QA_Setup_V8.87.exe, 75,930,416 B, SHA-256 ABC9036E4007EF3C07AD6FB59C59E2859BC6EF8DA2BA7E2BECE9A6FCAD9F890B |
| Packaged RemiXDuoSmaartSetup.exe --scan (read-only) | PASS | detects Smaart 9 install; trace folders absent |
| Packaged RemiXDuoSmaartWatcher.exe --one-shot (no Smaart) | PASS exit 0 | no residual process |
| Authenticode | **FAIL** NotSigned (setup + 3 EXE) | — |
| Version identity | **FAIL** | __init__ 8.87, pyproject 8.87.0, window title "QA V8.87", setup name V8.87, while code is V8.109 |
| Build type | **HOLD** | build_remix_duo_qa_v877.ps1 embeds the QA runtime hook; script states production must NOT use it. No production build script exists in this folder |
| Live Smaart GUI (SUM 2-trace, MagEQ/FIR 1-trace, 3/3 tick re-arm no-blink, PrintWindow) | **HOLD** | Smaart not available |
| V8.27 autostart watcher double-launch risk | **HOLD** | must be neutralized before live QA (see V8.109 report) |

## Addendum 2026-11-09 — MacBook 192.168.1.37 (arm64, macOS 27.0.1, Smaart running)
Access: SSH key ~/.ssh/remix_mac_qa_ed25519 (user-authorized). Mac was only
read; Smaart and the running legacy "RemiX Auto Phase Overlay V7 QA.app"
were not touched. Mac source copy: ~/RemiX_Duo_Build/V8109_GATE_20261109/source.

### A. Mac Smaart data as Windows legacy fixtures
- Copied ~/Documents/Smaart Suite/Data/Transfer Function (190 MB) to
  D:\REMIX_DUO_CHECKPOINTS\V8109_FAKE_HOME_MAC_FIXTURES_20261109 and ran the
  runner with USERPROFILE pointed there (real Documents untouched).
- Removed 207 macOS AppleDouble `._*` tar artifacts from the copy; moved 33
  .trf not referenced by the (2025-09-28) index.xml to UNINDEXED_SET_ASIDE so
  the copy is a self-consistent real index + its 199 files.
- Result: **476 PASS, 72 SKIP, 14 FAIL, 6 ERROR** (was 423/44/27).
  Remaining 20, none attributable to V8.109 code:
  - 15 need Admin-PC-only files `0 delay-1/-2.trf`, `4,8 ms delay-1.trf`.
  - 4 FIR GUI tests pick the first indexed trace; on Mac data it lacks
    coherent bins and the solver correctly fails closed ("insufficient
    reliable coherent bins").
  - 1 latent test bug: test_trf_v7.py used `struct` without importing it
    (hidden while the test always skipped). Fixed (1-line import); now PASS,
    real-data parse 185/199 OK, 14 rejected fail-closed.
- Log: _qa_outputs/v8109_release_gate/unit_runner_macfixtures_indexed.txt

### B. Shared + contracts on native Mac arm64 (V886 .venv, Python 3.11.9, numpy 1.26.4)
3 runs: 69 PASS / 8 SKIP / 1 FAIL, 68/8/2, 69/8/1.
- **PRODUCT DEFECT (reproducible 3/3, Mac only):**
  filters.design_phase_only_fir V8.105 never-worse gate uses strict
  `acted_after > acted_before` with no tolerance. Pure-delay trace:
  Windows before 8.64e-12° after 4.87e-12° → PASS; Mac before 1.68e-12°
  after 2.30e-12° (+6e-13°) → "FIR Phase HOLD: Excess Phase tệ hơn
  (0.0° → 0.0°)". A perfect trace is refused on Mac. Needs an absolute
  tolerance. NOT fixed in this run.
- Flaky 1/3: test_auto_align_is_bit_identical…[0] — same decision
  (3.70 ms, no invert) but score_db differs in last ULP on Mac. Test
  strictness vs Mac FP non-determinism; not user-visible.
- Mac live Smaart overlay acceptance: HOLD (needs unlocked screen +
  Accessibility/Screen Recording grants; not possible over SSH).

### C. V8.110 FIR never-worse tolerance fix (2026-11-09, UNCOMMITTED)
- src/remix_duo/core/filters.py: new FIR_PHASE_WORSE_TOL_DEG=.05; gate is now
  `acted_after > acted_before + FIR_PHASE_WORSE_TOL_DEG`. Real worsening
  still HOLDs (5->8, 0->0.2, 10->10.1 deg tested).
- tests/shared/test_fir_phase_range.py: +4 deterministic tests (monkeypatched
  excess RMS, platform-independent); RED before fix (float-noise case), GREEN
  after. Real-TRF assertion uses the same tolerance.
- Windows shared+contracts: 76 PASS 6 SKIP. Mac arm64 shared (3 runs): 74/74,
  74/74, 73/74 — pure-delay FIR now PASS 3/3; only remaining Mac failure is
  the known 1/3 ULP flake in test_auto_align_is_bit_identical…[0].
- Legacy runner with Mac fixtures, A/B same data: with fix 477 PASS 13 FAIL
  6 ERR; without fix 477/13/6 — identical; no regression. (One earlier full run
  showed test_v16 GUI AutoEQ 15 s wait timeout under load; passes 3/3 alone
  and in both A/B full runs → timing flake, not this change.)
- Logs: _qa_outputs/v8109_release_gate/ab_with_fix.txt, ab_without_fix.txt

### D. Mac GUI is a different frontend from Windows (by design, not parity)
- Windows runs legacy overlay_v7.py + signal_tools_gui_v813.py (~4,600 lines:
  docked ToolHub, AutoPhase/AutoEQ/FIR panels, native SUM/MagEQ/FIR curves).
- Mac runs src/remix_duo/ui/overlay.py (184 lines, V8.87): small toolbar
  (Auto Phase/Auto EQ/Auto FIR) + compact card with Trace 1/2 and status; no
  curve drawn without verified native trace/axis evidence, which is HOLD on
  Mac. Full Mac UI parity is NOT implemented.

## What must happen before release
1. Restore Smaart Session Data fixtures (index.xml + named .trf) — or point a
   throwaway USERPROFILE at a copy — and get the legacy runner to 0 FAIL/ERROR
   (V8.84 reference: 478/478).
2. Decide the release version number and update __init__/pyproject/title/.iss.
3. Production build without the QA runtime hook; sign setup + EXEs.
4. Live Smaart acceptance per QA_V8109_TICK_CONTINUITY_PROVENANCE_20261106.md.
5. Only then replace installed V8.84.

## Safe next command (offline, read-only to Smaart)
D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA\run_shared_tests.py
