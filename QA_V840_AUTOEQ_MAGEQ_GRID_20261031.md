# RemiX Dou V8.40 — restore Auto EQ MagEQ / marker / gradient

Date: 2026-10-31 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting Git HEAD: 9bb0170

## Reproduced on actual Smaart
- User screenshot: Auto EQ House, one trace "0 delay-2" (or "0 delay" label),
  status PREVIEW_READY / 4 PEQ / WRMS 3.54 -> 2.69 dB.
  But NO corrected MagEQ, PEQ markers or boost/cut gradient on Magnitude.
- Source generator/solver is operational; the failure is presentation.
- Direct read-only Smaart HWND probe:
  smaart_mag_geometry_readonly.locate_plots(hwnd) -> None.
  The shared Auto Phase plot_role_v812.locate_role_plots(hwnd) ->
  Phase (252,84,1442,412); Magnitude (252,539,1442,412).
  Magnitude header signature detector -> (same Mag rect, score=1.0).
- Old Auto EQ choose_color_fit(original mag source) -> None.
  Direct native-grid measurement -> accepted=True with zero_px=171,
  px_per_db=11.5, independent pixel-grid confidence=1.0.

## Surgical integration (no second GUI)
- native_eq_mag_v06.native_fit_worker uses the original shared
  role-aware plot locator used by Auto Phase, rather than independent
  legacy EQ-only geometry that fails on this real Smaart layout.
- Confirm the Magnitude title still matches the role-aware rectangle;
  mismatched title/role fails closed.
- Primary Y registration now uses the native 0 dB line and horizontal
  grid, same as SUM Mag V8.39; create accepted NativeMagFit with
  source_median_db=0, center_px=zero line, px_per_db=measured pitch/step.
  This maps actual user-approved MagEQ points directly to Magnitude Y.
- Retain old high-confidence curve-color matching only as fallback if
  the grid is unavailable. No guessing, color-based shift, or DSP SET.
- Source remains gated by independently verified ONE Smaart tick,
  source revision, view HWND/rect/age and foreground protections.
- Existing Qt SumGraph._paint_mageq draws corrected amber line,
  PEQ markers and boost/cut gradient on EXACTLY one native Mag widget.
- Leave LF-HF, SUM Phase/Mag, Auto Phase two-tick gate,
  DSP/AUTOEQ optimization, untouched.

## QA evidence
- Direct live read-only native_fit_worker with source 0 delay-2:
  accepted Frame, plot (252,539,1442,412), color GRID,
  native zero=171, scale=11.5 px/dB, score=1.0, 302ms worker.
- Added test_v840_autoeq_native_grid.py (4 tests):
  real saved Smaart screenshot + legacy color-fit forcibly None
  still creates correct frame and computes 4 PEQ geometry;
  Qt offscreen SumGraph draws corrected line, 4 markers, nonempty
  gradient; no grid and no source fit fail closed; mismatched
  native plot header rejected.
- Full V8.28–V8.40 + AutoEQ V0.19 focused regression: 97/97 PASS.
- Qt offscreen 4096-bin / 40-frame P95:
  Phase 2.09ms, Mag 2.88ms (not live mouse-to-display).
- Audio IO, generator, Smaart saved config, original .trf, and all
  other sessions' dirty files are not modified.

## Live GUI gate
- Runtime process restart required to load source change.
- After restart AutoEQ calculation is no longer in memory. Verify
  one selected Smaart trace, then press Auto EQ again with House/48k
  or user-chosen parameters, confirm amber MagEQ, marker #1..#4 and
  colored boost/cut gradients on the original Magnitude pane.
- Do not mark live GUI PASS based only on offscreen Qt tests.

## Live GUI acceptance evidence — 2026-10-31 00:14 local
- After controlled restart of exact RemiX Dou companion:
  wrapper PID 21128, child 21056; Smaart PID 18904 untouched.
- Opened Auto EQ via correct RemiX-owned toolbar button on Smaart.
- Captured QA_V840_AUTOEQ_SELECT.png (1920x1080).
- Original native red Mag remained unchanged.
- Corrected amber MagEQ, gradient and numbered PEQ #01 marker/chip
  visibly appeared in the original native Magnitude pane.
- Visible Auto EQ result: 0 delay-2, PREVIEW_READY / 1 PEQ,
  WRMS 2.72 -> 2.35 dB, preset Flat after restart.
  LIVE GUI PASS: MagEQ line, 1 marker, boost/cut gradient.
- Existing Qt offscreen four-PEQ rendering tests pass, but House /
  4 PEQ setup was lost on restart: House/4 PEQ live still HOLD.
- Saved Smaart screen with overlay verified native GRID:
  zero=171px, grid pitch=34.5px, 11.5px/dB,
  confidence=0.90909 (91%). Previous "native REF 91%"
  caption was mislabeled; a source correction now displays
  "0 dB GRID" for grid-grounded frames.
- Smaart became minimized afterward; further live UI operations
  were halted to avoid interacting with another window state.
- No Smaart trace, Generator, soundcard or DSP change.
