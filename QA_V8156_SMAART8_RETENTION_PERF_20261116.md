# RemiX Duo QA V8.156 — Smaart 8 trace retention / EQ-FIR worker isolation
Date: 2026-11-16, device: DESKTOP-VNPRJCI
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_150_RELEASE_RC1
STATUS: SOURCE REGRESSION PASS / INTERACTIVE GUI HOLD / RELEASE HOLD

## Verified source changes
- signal_tools_gui_v813.py ToolHub.tick: on non-active Smaart, suspend tick verification rather than destroying the immutable candidate when bound HWND still exists. Different foreground Smaart HWND or missing bound HWND hard-invalidates.
- signal_tools_gui_v813.py EQDialog._finish: worker result acceptance now depends on source TRF token, file SHA, saved Fs and current source selector; not transient SUM/overlay Python object IDs. EQ solver already runs in ThreadPoolExecutor (unchanged).
- signal_tools_gui_v813.py ToolHub.tick: avoid redundant FIR.refresh_sources call when overlay pair/object IDs change; once each 175ms slow tick.
- mageq_presentation_gate_v853.py: a complete measured tick count of 0/2+ must never preserve a previous EQ preview, even if a stale candidate still exists.
- overlay_v7.py: if bounded safe Auto Phase/SUM display bridge rejects a transient/pending state, discard old candidates instead of preserving invisible stale results.
- Tests added: test_v8156_smaart8_trace_retention.py (10 PASS), including source rearm, changed file, count mismatch, background HWND, fake-SUM refresh and EQ worker completion.
- Test fixture corrected: test_v8107_tick_rearm_no_blink.py uses actual Candidate object to exercise real Top-3 rendering rather than a string placeholder.
- NO DSP math changes, NO changes to Smaart 8, generator, routing, TRF bytes or Smaart Suite.

## Verified regression
- Existing default suite: 114 passed, 4 skipped.
- Smaart 8 / tick / safety focused: 26 passed, then additional 33 passed after SUM fix.
- Full suite first identified 6 SUM/provenance regressions; after source fix and corrected mock: 817 passed, 54 skipped, 1 flaky busy-toast timing fail.
- Busy-toast standalone: test_v8145_manual_limits_busy_toast.py = 3 passed in each of three consecutive reruns.
- Full final run: 818 passed, 54 skipped, 1 warning, 0 failed, 107.48s.
- New isolated post-full tests: test_v8156_smaart8_trace_retention.py = 10 passed.

## Live runtime evidence
- Stopped ONLY old RemiX Duo source PID 50772, restarted updated source as PID 32012 (2026-11-16 15:56:02). Smaart 8 PID 44468 and HWND 525128 survived, Responding=True.
- New source process Responding=True, no new observed crash in test window.
- Actual Smaart 8 tick probe: 35 polls, 10 verified; last verified source TUNNINNGGG-13.trf, generation 1.
- During probe, another desktop session foregrounded UltraViewer and Smaart 8 became minimized (bounds -32000). As a result, 25 failed reads returned bad Smaart bounds.
- The raw 35-poll median 3.21ms, P95 110.79ms and max 114.48ms MIX successes/failures and MUST NOT be used as a valid-scans-only P95 or as live GUI FPS.
- GUI mouse/drag, actual export EQ/FIR and full 1->2->1 trace cycle: HOLD due to competing foreground/minimized host. No unsafe clicks, audio commands or generator start sent.

## Read-only worker latency on Smaart 8 TUNNINNGGG-13
- TRF parse 4.72ms for 806 frequency points.
- Auto EQ (AUTO PEQ, +2/-6dB, 60-8000Hz), 5 runs: median 674.3ms, observed max 1234.5ms, 4 PEQ.
- FIR Phase 4096 taps (500-2929Hz), 5 runs: median 351.9ms, observed max 432.6ms.
- Qt QTimer nominal 16ms, per-run P95 observed: EQ 16.6-17.3ms, FIR 16.8-21.0ms; synthetic worker loop, not live overlay rendering.
- GUI work was reduced by removing one duplicate FIR refresh for pair/object changes. No solver change or numerical risk introduced.

## Evidence, rollback and release gate
- Regression logs: build\QA_V8156_FULL_PYTEST_20261116.log (6 failures, prior),
  build\QA_V8156_FULL_RETEST_20261116.log (1 timing flake, prior),
  build\QA_V8156_FINAL_FULL_20261116.log (all pass).
- Current source checkpoint: build\QA_V8156_PATCHED_SOURCE_CHECKPOINT\ (source and regression tests).
- Prepatch production EXE + installer were not rebuilt or overwritten by V8.156. Restore previous production by using the prior release; current source candidate can be restored from checkpoint if later modified.
- RELEASE HOLD until interactive Smaart 8 1-trace Auto EQ/FIR preview/export, 2-trace Auto Phase Top-3, repeated ROI drag and mixed foreground/minimize cycles are signed off, followed by new Cython/PyInstaller build and clean-machine installer QA.
