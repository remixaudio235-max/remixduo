# RemiX Dou Auto Phase V8.34 — fast, native-verified Y pan

Date: 2026-10-30 / Admin-PC / Windows Smaart Suite
Working source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Previous checkpoint: checkpoint/remix-dou-v833-compact-trace-20261030 (55b7dbb).

## Verified root causes

1. SumGraph.paintEvent rebuilt thousands of Python geometry edges and stroked
   4,096 points whenever the Phase or Mag Y axis moved. Baseline Qt-offscreen
   P95: Phase 230.47 ms, Mag 68.34 ms (40 measured frames after warmup).
2. Independent Phase/Mag native GDI/REF capture and PrintWindow fallback
   have variable readback latency, including earlier 60–390ms absolute fits.
3. Mag lacked an equivalent 16ms gesture watcher. Unverified mouse-only
   preview could translate green SUM even when Smaart's native red Mag
   remained stationary; two real 160px drag screenshots reproduced this.
4. Saturated pure-red (#FF0000) Smaart Magnitude pixels were missed by the
   old mask requiring native red pixels to have G>30.

## Implemented

- SumGraph caches the full pre-rendered transparent SUM raster: Phase builds
  a 360-degree wrapped period and tiles it at the correct signed Y offset;
  Mag caches an extended Y canvas and translates it under a fixed clip.
  Cache rebuild only on new data, width/height, frequency range,
  display offset or changed Y span/zoom. Move-only pan no longer rebuilds
  paths or repeats antialiased QPainter stroking.
- App adds a 16ms fast cursor observer, but *never* treats cursor motion
  alone as verified Smaart pan. Native trace pixel deltas drive both SUMs.
- While a native Y gesture is active, capture only that plot, not both.
  One threaded/latest-available native worker and an epoch token reject
  outdated captures after drag begin/end, while absolute anchors wait for
  gesture to settle.
- The magnitude pixel mask now recognizes saturated red as well as blue
  Smaart source pixels while excluding neon green RemiX SUM.
- Underlying complex TF H(f), smoothing, delay and solver untouched.
  No audio, generator, soundcard, saved TRF or DSP changes.

## QA evidence

- 50/50 pytest PASS across V8.28–V8.34 plus baseline selection/TF/EQ tests.
- Qt-offscreen benchmark: 4096 frequency points, 40 post-warmup renders.
  New P95 Phase 1.79ms, Mag 2.08ms; offscreen renderer only, NOT full
  desktop source-to-present latency, nor guaranteed production FPS.
- Canonical make_geometry compared against cached raster:
  full visible trace masks matched F1 1.000 for Phase signed shifts
  (0,+50,+140,-190,+245,+360px), Mag (0,+60,+150,-160px).
  Mag +220px shifted all visible samples outside the plotted viewport;
  both reference and new renderer correctly showed no trace.
- Native synthetic-red 30px translation PASS (<=1px error); stationary
  RemiX green trace completely rejected by source color mask.
- Live Smaart 160px down/back Phase and Mag executed with exact HWND and
  safe release, screenshots saved V834_PHASE_*/V834_MAG_*.
  At one tested Mag ruler coordinate the native red trace was stationary;
  AFTER anti-ghost fix, measured red mask IOU=1.000 and SUM green
  mask IOU=1.000 between Mag PRE/PEAK (640x280 ROI), proving no false
  SUM translation when native trace does not move.
- Exact running app source verified after QA restart. Smaart remained
  running and responsive.

## HOLD — not falsely accepted

- Positive real Smaart magnitude pan with large confirmed native red motion
  was NOT reproduced in the automated ruler interaction at tested x=206.
  The native 30px red-motion QA is synthetic and does not establish real
  source-to-paint latency on the user's actual gesture.
- Phase native axis scroll/zoom and continuously shifting real Mag Y
  require a user-driven UI session with both original native movement and
  SUM measured together before granting full GUI parity.
- Offscreen raster P95 is NOT end-to-end presentation latency.
- Live complex Smaart TF frame streaming is not established; model SUM
  still uses selected stored .trf snapshots.

## Rollback

Keep V8.33 tagged checkpoint untouched. This QA fixes the current
V8.27 source tree in place, and should have its own commit/tag.
Restart only exact RemiX pythonw owners, never the Smaart process.
