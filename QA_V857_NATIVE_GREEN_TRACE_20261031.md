# RemiX Dou V8.57 - Native green Smaart MAG registration

Date: 2026-10-31, Windows Admin-PC.
Canonical Git source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Baseline: fc5f86a (V8.56 UX).

## Bug reproduction
User's Smaart screenshot shows selected green TUNNINNGGG-12 TF.
Auto EQ returns PREVIEW_READY (5 PEQ), while MagEQ shows
"Native pixel / Y khong khop hoac het han".
The source registry covered cyan, blue, red, magenta and gold only.
New green TF pixels could not pass the original native color fit.

## Implementation
- smaart_native_mag_fit.py adds "green" to native trace_color_mask.
  Channel dominance thresholds separate original olive-green TF
  from red, gold and dark grid.
- smaart_eq_color_select.py includes green in unbiased original
  source-color matching. Competing valid colors remain fail-closed.
- native_eq_mag_v06.py includes green in fast-refit and preferred-color
  paths, maintaining NEW native pixel and grid proof each frame.
- Existing source/viewport/TTL/export gates are NOT loosened.
- Existing TF, Auto EQ and all devices are read-only.

## Testing
- test_v857_native_green_trace.py checks native green image samples,
  color separation, eligible color fit and rejection of ambiguity.
- Focused native regression: 23/23 PASS.
- Python compileall and git diff --check PASS.
- Broad regression completed in a separate process (see stdout record).

## Live acceptance
At code-check time Smaart window was MINIMIZED:
HWND 88082526, rect (-32000,-32000,-31840,-31972).
The read-only PrintWindow capture returned "Smaart size invalid".
No attempt to restore, change UI layout or generate audio was made.
Real green TF native pixel parity, sustained MagEQ, Y pan and zoom
require live QA when Smaart is restored and TUNNINNGGG-12 ticked.
Do not claim live PASS from the synthetic-color regression.

## Broad regression closure
- Full selected V8.16-V8.57: 234/234 PASS, 38.71 seconds; exit 0.
- Safe regression remains PASS with the green source-color candidate.
