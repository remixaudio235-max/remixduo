# RemiX Dou V8.53: MagEQ transient blink / native refresh stabilization

Date 2026-10-31. Canonical source:
D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Base HEAD 46c46ef (V8.52).

## Root causes in source
1. NativeAutoEQMag.tick every 90ms; native FitFrame strict max age
   0.45s. Native worker on EVERY refresh formerly ran UIA plot geometry
   plus a PrintWindow for titles, then another PrintWindow for fitting.
   Slow or failed captures cause frame expiry and graph.set_mageq(None).
2. A single incomplete Data Bar read could transiently remove
   current_single/3-of-3 selection; strict _eq_tick_safe() then
   hid the whole Mag overlay, while refresh_sources sometimes
   invalidated its original solver preview.

## Fix
- New V8.53 bounded display-only 0.44s re-arm while the exact same
  immutable TRF (path,mtime,size) remains native single_candidate
  and NO valid scan explicitly identifies a different/0/2+ tick.
  Verified original source and native pixels are STILL required.
- NativeAutoEQMag._source_binding_ok(presentation=True) is used
  ONLY for MagEQ paint, never for Export/calculate/drag authorization.
  Strict _source_binding_ok() remains unchanged for Export and
  SHA/FS verification. New verified source or changed tick gates OFF
  immediately. No stale native Y outside the prior 0.45s fresh gate.
- Keep in-memory computed EQ during incomplete Data Bar scans:
  display selection becomes "waiting", Export remains prohibited,
  then restore selector on independently reverified SAME trace without
  re-running Auto EQ. Explicit other candidate or 0/2+ ticks still
  invalidate the original preview.
- New same-source native ROLE fast lane: remembered only both
  MAG/PHASE plot rectangles from a previously independently verified
  snapshot. Each new worker capture independently checks BOTH
  native title glyphs, then re-estimates source magnitude, grid,
  Y pan/zoom and coherence on fresh native pixels. Eliminates
  repeated UIA geometry and duplicate screenshots on stable layouts.
  On any geometry/identity/title/window change, re-run full
  UIA+role detection. On failure, HOLD (never reuse stale Y).

## Safety and QA
- No soundcard/Generator/Sweep/DSP writes. Original .trf untouched.
- Manual PEQ dragging, MaxPEQ, Q3-8, 1/4-octave spacing and FIR
  source logic not altered.
- New test_v853_mageq_presentation_gate.py checks bounded same-token
  grace, changed/multiple tick immediate rejection, expired native
  Y frame, strict export source token, Qt UI placeholder/recovery.
- New test_v853_native_cached_role_fastpath.py checks one-fresh-capture,
  skips UIA only if exact source+native titles match, otherwise full
  fallback, and backwards-compatible FitFrame.
- Existing tests test_v848_mageq_no_blink.py and test_v18_graph_rearm.py
  updated fixtures for correct new separation of native presentation
  gate vs strict Export; no test safety checks removed.
- Full selected V8.28-V8.53 regression: 208/208 PASS, 65.05 seconds.
- Python compileall and git diff --check PASS.

## Live acceptance HOLD
These findings are supported by static inspection, read-only prior
Smaart evidence, and synthetic/Qt regression tests. The actual
V8.53 Windows live non-blinking 30-60s run has NOT been recorded:
a physical Smaart non-blink claim needs fresh 1-tick trace,
30-60s soak, change current tick, pan/zoom and Alt-Tab.
Do not claim live PASS from unit/integration QA alone.
