# QA V8.106 — MagEQ / FIR overlay blink during Auto EQ / Auto FIR (2026-11-04)

Source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`
(branch `qa/remix-duo-v873-native-tf-reader`, on top of 6b7a8ba). UNCOMMITTED.

## Symptom
The user reported: "App thường chớp tắt khi auto EQ, Auto FIR?"

## Evidence (read-only, live Smaart PID 26516, HWND 6425940, 1920x1040)
| Step | Median | Max |
|---|---|---|
| `locate_role_plots` (UIA) | 335 ms | 620 ms |
| `capture_native_window` (PrintWindow) | 155 ms | 163 ms |
| `detect_magnitude_rect` | 3 ms | 11 ms |
| `fit_native_mag_grid` | 134 ms | 188 ms |

Design time on a real TRF:
- Auto EQ 324 ms; FIR Phase 199 ms (1024 taps) / 370 ms (4096 taps); FIR Mag 7 ms.
- The worst gap seen by a 20 ms ticker thread during a design was 21–28 ms. So GIL contention / a GUI freeze is **not** the cause.

## Root cause (code)
1. **Every recompute forced a full UIA rescan.**
   - Each Auto EQ / FIR recompute called `clear()` / `accept()`, which discarded the verified geometry and colour seed.
   - The fast lane also required `prior.revision == source.revision`.
   - Result: on every compute the curve disappeared and only came back after a full UIA scan (335–620 ms) plus capture and fit.
2. **Steady-state frame expiry.**
   - A displayed frame is valid for only 0.45 s (`NATIVE_FRAME_MAX_AGE_S`; FIR `MAX_AGE`).
   - A fast-lane verification takes about 0.3–0.4 s, and the tick runs every 90 ms (MagEQ) or 120 ms (FIR).
   - So a frame often expired before its successor landed and the curve blinked. Higher CPU load (for example a design running at the same time) means longer verification and more blinks.
   - Timing model (`scratchpad/sim_blink.py`, tick 90 ms) — curve hidden time before the fix: 0.0 / 0.4 / 3.3 / 9.6 % at D = 310 / 350 / 400 / 450 ms. After the fix: 0 % in all cases.

## Fix
**`native_eq_mag_v06.py`**
- `NATIVE_DISPLAY_GRACE_S = 0.90` and `frame_presentable()`. This applies to **display only**.
  - Export, drag and the PEQ grips keep the strict `frame_is_fresh_for_window` (0.45 s).
  - The last verified frame stays on screen only while a newer verification of the same, unmoved window is in flight and the previous verification did not fail.
  - A window move or resize still drops it immediately.
- Fast lane: an Auto EQ recompute of the **same original measurement identity** (a hash of the original TF, independent of the PEQ revision) reuses its role rectangles and colour as seeds. They are still re-proven by the native title and fit on fresh pixels.
- `clear()` keeps the seeds.
- After 3 consecutive failed verifications (`SEED_DROP_AFTER_FAILURES`) the seeds are dropped, so a trace recoloured in Smaart gets a full independent rescan.
- **Contracts kept:**
  - A different trace never inherits the old cache or colour (V8.53).
  - A seed-colour miss is held and never falls back to another colour (V8.47).

**`fir_native_v846.py`**
- Same identity rule for `cached` (the revision is no longer required).
- `clear()` / `accept()` keep `last_verified` as a seed.
- `_presentable()` adds the in-flight grace in `tick` and `_publish`.
- Seed drop after 3 failures.
- `native_fir_fresh(max_age_s=None)` defaults to the old `MAX_AGE`.

## Tests
- `test_v8106_native_overlay_no_blink.py`: 20 tests. RED before the fix (17 failed), then GREEN.
- Official runner `run_unit_qa_v884.ps1`: 534 PASS, 1 SKIP, 2 FAIL. Both failures are pre-existing at 496371b: `test_export_eq_v08` ('remote') and `test_native_eq_v06` ('teal').
- `tests/shared` + `tests/contracts`: 78 PASS.

**QA incident:** a first ad-hoc `pytest test_*.py` also collected the 4 live-UI scripts that the runner excludes:
- `test_hide_other_window_v7`: opened and closed Notepad.
- `test_live_sync_probe`: `SW_RESTORE` on Smaart, then a read-only Data Bar poll.
- `test_uia_scroll_restore`: Smaart scrollbar +220, then restored.
- `test_v7_gui`: offscreen demo.

That run segfaulted. Checked afterwards:
- Smaart is the same PID 26516, same rect (0,0,1920,1040).
- No Notepad left behind.
- The overlay 36424/11928 is unchanged and is the only one.
- No Generator, routing, TRF or DSP action.

## Status
- UNIT: PASS.
- NATIVE: HOLD.
- LIVE GUI: HOLD. The running overlay PID 36424 still has the pre-V8.105/V8.106 code loaded.
- Next safe step: stop exactly 36424/11928 (with authorisation), relaunch one overlay from this folder, run Auto EQ and FIR on one ticked trace, and watch whether the MagEq/FIR curve stays on.
