# RemiX Dou — V8.33 Compact Invalid Trace UI

Date: 2026-10-30 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Previous rollback checkpoint: checkpoint/remix-dou-v832-20261030 (25a5a93).

## Root cause
When Tick Gate detects 3 active Smaart traces, two Trace name/delay rows
and the Top3 candidate card are hidden, but the 400px Auto Phase page
QVBoxLayout still stretches the remaining Trace card and QLabel warning.
Measured before fix in offscreen Qt: invalid Trace card 174px,
selection_warning 79px, despite only one short message.

## Actual source fix
- overlay_v7.py: trace card uses Fixed height 70px on invalid/pending,
  138px on valid pair. Warning QLabel uses fixed height 36px,
  alignment left-center, subtle amber outline, narrower padding.
  Candidate Top3 card uses content height 167px; remaining vertical
  space allocated to bottom stretch rather than stretching a warning.
- signal_tools_gui_v813.py: only for _selection_quality == 'invalid'
  and phase page selected, limit physical RightToolDock to 148px.
  Valid pair returns to full native dock height and keeps all Top3,
  and pending frames do not repeatedly shrink/expand the dock.
- Existing logic for native DataBar active tick count, 3/3 stable
  detection, selected trace identities, delay, SUM TF, and native I/O
  remains UNMODIFIED.

## QA
- Before: card=174px; warning=79px with 3 Trace message.
- After: card=70px; warning=36px; native dock=148px when count invalid.
- Verified pair: card=138px; full native dock=310px; Top3=167px.
- 43/43 pytest PASS, including V8.33 layout regression plus V8.32
  LF/HF Mag/Phase drag, V8.31 brand, native SUM, selection, AutoEQ
  and export test cases.
- Exact-source application restarted on Admin-PC:
  Pythonw wrapper PID 2056, child PID 18116 (verify current state later).
- Native Smaart GUI screenshot: V833_COMPACT_TRACE_LIVE_QA.png.
  Two real Trace names/results displayed, Top3 still visible, SUM traces
  in Mag and Phase continue drawing, logo RemiX Dou intact.
- Invalid-count screenshot produced in Qt offscreen test:
  V833_INVALID_COMPACT_QA.png; this tests exact Qt widgets/layout,
  NOT an actual live 3-tick Smaart screenshot.
- Smaart was minimized during initial attempted capture, then safely
  restored without changing soundcard, saved TRF or playback.

## Acceptance boundary
Invalid UI geometry/state: automated PASS. Verified two-Trace GUI:
live screenshot PASS. A natural live 3-Trace Smaart screenshot
and manual visual acceptance are not yet claimed.
