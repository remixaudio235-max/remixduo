# V8.145 full-app Reflexion — 2026-11-14

## Verified changes

- Auto FIR defaults are LF 500 Hz / HF 2500 Hz in both the dialog state and
  native overlay state; manual drag/spin behavior remains available.
- Auto Phase, Auto EQ and Auto FIR schedule one busy Toast only if the same
  worker request is still active after 50 ms: `Đang Auto, vui lòng đợi...`.
- Auto EQ Boost/Cut controls are enabled. `0/-12` selects AUTO; any other pair
  is passed unchanged to the solver, including while PEQ count remains AUTO.
- Async Fs cache now returns HOLD/None safely when no config path is resolved.
- Standalone EQ/FIR close paths use bounded worker shutdown.

## Evidence

- Shared/contracts: 114 passed, 4 skipped (missing reference TRFs only).
- New/manual/toast/Fs focused set: 18 passed.
- Previously failing legacy/Qt set after async-test correction: 31 passed.
- Full isolated legacy sweep before corrections: 129 files; 116 passed files,
  7 no-test probes, 6 failing files. All six failing files were rerun after the
  corrections and passed; the entire 129-file sweep was not repeated a third
  time, so do not claim a fresh 129/129 PASS.
- Runtime idle 10 s: 0.156 CPU s (~1.6% one core), 247.1 MB working set,
  +0.4 MB, 36 threads with delta 0, 1690 handles. This is a short sample, not a
  soak/leak proof.

## Reflexion findings

### P0

- Release/source guard remains broken: its venv points to removed
  `C:\Users\Admin\...\Python311\python.exe`. Build identity is therefore HOLD.

### P1

- `pyproject.toml` collects shared/contracts only; 129 root legacy/Qt files are
  outside the default command. CI can report green without exercising the GUI.
- Native live acceptance remains incomplete for current Toast placement,
  manual Boost/Cut solve and the exact 500–2500 FIR markers after restart.
- Mac Intel/arm64 live Smaart acceptance remains separate HOLD.

### P2

- The primary modules contain about 50 broad `except Exception` sites. Most are
  fail-closed worker/UI boundaries, but several silently suppress diagnostics;
  structured rate-limited error codes would improve crash forensics.
- Five concurrent UI timers (16/33/90/120/175 ms) remain. Current idle CPU is
  low, but a long foreground trace/geometry soak is still needed to prove no
  capture contention or flicker under load.

## Safety

No Generator/Sweep, soundcard route, Smaart trace write or DSP write was used.

