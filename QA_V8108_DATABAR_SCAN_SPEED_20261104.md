# QA V8.108 — Data Bar trace-list read slow / scrollbar moves up and down repeatedly (2026-11-04)

Source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`. UNCOMMITTED, on top of V8.106/V8.107.

## User report
"App đọc trace list của smaart cũng rất chậm, kéo scrolbar lên xuống nhiều lần"

## Root cause (code)
1. **Scroll storm.**
   - `LiveDataBarV7.poll` called `initialize()` (a full scroll scan of the Data Bar plus a restore) whenever the observer was not ready.
   - When the full scan raised `ScanError`, the observer stayed not-ready. Typical causes:
     - an ambiguous tick under the mouse hover;
     - a tick changed mid-scan;
     - a UIA row count ≠ the stored TRF count;
     - "too many pages".
   - So the **next poll 0.16 s later scrolled the whole list again**, endlessly, while Smaart was in the foreground.
2. **Every page and every poll queried the UIA rectangle of ALL rows.** That is 108 cross-process COM calls each time, even though only ~15 rows are visible.
3. `initialize()` walked the UIA tree twice: once in `full_scan`, then again itself.
4. The scan pages overlapped by 32 % (step = 0.68 × viewport).

## Fix
- **`live_sync_v7.LiveDataBarV7._reinitialize`:**
  - After a failed full scan, the same (HWND, size) is retried only after 1.5 / 3 / 6 / 10 s.
  - A different Smaart window or size retries immediately.
  - The returned status is `Data Bar HOLD: …`. It is fail-closed: no pair, so the tick gate stays transient.
  - The counter resets on success.
- **`initialize()`** walks the UIA tree once and passes it to `full_scan(uia=...)`.
- **`full_scan_v7._visible_uia_window`:**
  - Starts from an index estimate and walks outward, using each row's **own** UIA rectangle, until a row leaves the viewport.
  - It checks that the row geometry is monotonic. If not, or on any UIA error or missing index, it falls back to the old all-rows loop.
  - The classification contract is unchanged; nothing is inferred from the row pitch.
- **Page step** = viewport − 2 rows. Full coverage is still proven: every row must be seen, otherwise `ScanError`. The scroll is restored to its start in `finally`.

## Evidence (simulated 108-row Data Bar; no real Smaart)
| | Old | New |
|---|---|---|
| Scroll pages per full scan | 11 | 9 |
| UIA rect calls per full scan | 1191 | 154 |
| UIA rect calls per viewport poll | 108 | 17 |
| UIA tree walks per initialize | 2 | 1 |
| Full scans in 3.2 s while the scan keeps failing | 20 | 2 |
| Rows covered | 108/108 | 108/108 |

Tests:
- `test_v8108_databar_scan_speed.py`: 6 tests, RED 6/6 before the fix, then GREEN.
- Official runner: 555 PASS, 1 SKIP, 1 pre-existing FAIL (`test_native_eq_v06` 'teal').
- `tests/shared` + `tests/contracts`: 78 PASS.

## Not measured / HOLD
- The live timing of a UIA `rectangle()` call on the real Smaart was not measured, because Smaart was not running.
- The real cause of the user's failed scans (ambiguous tick, row-count mismatch, etc.) is not known yet. After this fix the reason is visible in the status / tooltip as `Data Bar HOLD: …` instead of a scroll storm.
- Overlay relaunched as 36604→22128 (V8.108 code).
- LIVE GUI: HOLD.
