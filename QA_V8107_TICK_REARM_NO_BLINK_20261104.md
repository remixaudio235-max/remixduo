# QA V8.107 — remove "Điều khiển" + SUM / MagEQ / FIR tick re-arm no-blink (2026-11-04)

Source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`
(branch `qa/remix-duo-v873-native-tf-reader`, on top of 6b7a8ba + uncommitted V8.106). UNCOMMITTED.

## User request
"bỏ nút Điều khiển sau Auto FIR đi. test lại toàn bộ app để chạy ổn định, không chớp tắt SUM trace, EQ Mag, FIR"

## 1. "Điều khiển" removed
- `signal_tools_gui_v813.py`:
  - The toolbar buttons, the responsive menu and the compact/mini labels now list only Auto Phase / Auto EQ / Auto FIR.
  - The dock no longer builds a `RemoteControlPage`, so no LAN server can be constructed.
  - `closeEvent` no longer stops a remote page.
- `remix_remote_control_r1.py` is kept as a file and is not imported by the GUI.
- Tests updated:
  - Toolbar tests: `test_v863`, `test_v870`, `test_v831`.
  - `test_remote_ui_integration_r1` now asserts the button and page are absent.
  - `test_remote_gui_lifecycle_r1` now asserts no LAN page exists.
  - `test_remote_control_r1` (standalone module test) is unchanged.
- The old pre-existing failure `test_export_eq_v08` ('remote') now passes.

## 2. Blink root cause (code evidence)
All three displays depend on the Data Bar 3/3 tick lock.

**How one bad scan breaks the lock (`live_sync_v7.poll`).** Any one incomplete scan calls `suspend_single_transient()` / resets `StableTickGate`. Incomplete means one of:
- scroll changed during capture;
- no unambiguous rows;
- an ambiguous visible tick;
- a PrintWindow read error.

**How long the re-arm takes.** Re-arming needs 1 failed poll + 3 fresh polls. Each poll costs at least the 0.16 s throttle plus PrintWindow (~155 ms), so the re-arm takes about 0.8–1.2 s.

**Display grace before this fix, per display:**
| Display | Gate | Grace |
|---|---|---|
| SUM | `overlay_v7.found()` → `_set_tick_presentation(False)` on a transient or pending scan | 0 s; it also wiped `last_solve` |
| MagEQ | `presentation_tick_ok` | 0.44 s |
| FIR | `NativeFIROverlay._allowed()` → strict `_proof_current()` | 0 s |

So any single bad scan hid the curve for about 0.5–1.2 s.

## 3. Fix (display-only, bounded)
The bridge lasts at most **1.5 s**, the same as the observer's own row-freshness proof (`_pair`, `current_single`).
- **`mageq_presentation_gate_v853.TRANSIENT_DISPLAY_GRACE_S`:** 0.44 → 1.5.
- **`overlay_v7.App._hold_selection_display`:**
  - Keeps the committed pair drawn only when *all* of these hold:
    - The previous state was verified.
    - `controller.last_pair == tick_gate.committed`.
    - The decision is either `transient` (not PAIR_PATH_MISMATCH or INVALID_COUNT_HAS_PAIR), or `pending` for the same committed pair.
    - It is no more than 1.5 s since the last valid decision.
  - Solve is disabled during the hold, and the warning reads "Đang xác minh lại tick…".
  - `last_solve` and the candidates are kept.
- **`FIRDialog._proof_current(display=True)`:**
  - May bridge only while the observer has no verified single, the candidate equals the approved token, the tick count was not explicitly changed, and the grace has not expired.
  - All other provenance checks still apply: Fs, taps, LF/HF, mode, file stat and SHA.
  - Only `NativeFIROverlay._allowed()` uses it. Export, menus and DSP still use the strict proof.
- **Hard stops still apply immediately:**
  - A complete scan with a different pair.
  - Count ≠ 2 (SUM) or ≠ 1 (EQ/FIR).
  - Zero ticks.
  - A different verified source.
  - Scanner pair/path mismatch.
  - Grace expiry.

**Contract note.** AGENTS.md says "scan incomplete → HIDE SUM". V8.107 delays that hide by at most 1.5 s, and only while no complete scan contradicts the committed pair. It never fakes a new pair and never authorizes a computation.

## 4. Evidence
- `test_v8107_tick_rearm_no_blink.py`: 14 PASS. Before the fix they would fail: the `display` kwarg and `_hold_selection_display` did not exist, and a grace of 0.44 is below the required 1.2.
- Official runner `run_unit_qa_v884.ps1`: **549 PASS, 1 SKIP, 1 FAIL**. The failure is pre-existing: `test_native_eq_v06` 'teal' also failed at HEAD.
- `tests/shared` + `tests/contracts`: 78 PASS.
- Offscreen toolbar `QA_V8107_TOOLBAR_NO_REMOTE.png`: 3 buttons. Menu: Auto Phase / Auto EQ / Auto FIR.
- Direct trace of the SUM gate (synthetic): transient → pending 1/3 → pending 2/3 → valid. `_selection_verified` stayed True throughout and `last_solve` was kept.

## 5. Runtime state
- The old QA overlay tree 32956→13924 was stopped after a cmdline/parent preflight.
- Relaunched as **27144→22364**: `python.exe -X faulthandler overlay_v7.py`, with CWD set to this folder.
- Smaart was **not running** at relaunch. PID 26516 had exited, and there is no Application-log crash event.
- **Hazard:** the logon watcher `smaart_autostart_v875.py --watch` (PIDs 8012/9056, from `windows_v8_27_MAG_NATIVE_SYNC_QA`) only treats Duo as running when the overlay argv equals the V8.27 script path. When Smaart next starts, it will launch a second (V8.27) overlay next to the QA one. Resolve this before live QA, either by stopping the watcher for the session or by not running the QA overlay.

## 6. Status
- UNIT: PASS.
- NATIVE: HOLD.
- LIVE GUI: HOLD. This needs Smaart with ticked TRFs (2 for AUTO PHASE, 1 for EQ/FIR). Run `qa_v8107_blink_monitor.py --seconds 180` (read-only; it sees window-level hides only).
