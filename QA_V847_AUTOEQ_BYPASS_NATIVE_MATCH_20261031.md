# RemiX Dou V8.47 — AutoEQ consistent MagEq BYPASS and native matching
Date: 2026-10-31 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting Git HEAD: 45b56c0

## Reproduced
The user's screenshot shows original Smaart trace "4,8 ms delay-1";
AutoEQ solver status NO_EQ_NEEDED, zero PEQ, WRMS 2.25 -> 2.25 dB.
Old GUI intentionally called native_clear unless PREVIEW_READY AND
one or more PEQ. Native MagEq also rejected zero PEQ. Thus no line.

Read-only independent live Smaart inspection:
- Smaart.exe was running at first. Magnitude native pixel chart detected.
- Blue selected 4,8 ms delay-1 native curve score=1.000, second
  distant Y-model score=0.86425, legacy margin missed by 0.004.
- Independent Smaart native 0 dB/grid confidence=1.000 and slope
  11.5 pixels/dB. Original blue source slope=11.027 pixels/dB.
- Post-patch SAME live image/Trace: verified blue source identity and
  grid agreement, fit score=1.000. No Smaart data or hardware modified.
- Smaart later closed before warm-color duration or GUI pan/zoom QA.

## Fix
1. NO_EQ_NEEDED with exactly zero PEQ now explicitly permits read-only
   BYPASS. MagEq=original stored Magnitude, no filters or correction.
   Draw AMBER DASHED BYPASS trace and the unambiguous 0 PEQ caption,
   with no correction gradient and zero EQ markers.
2. Only NO_EQ_NEEDED is approved for this bypass, not arbitrary
   solver errors. For all other cases without valid PEQ, fail closed.
3. Source token/path/mtime/size/SHA, saved Fs, one tick, native pixel
   binding and fresh native viewport gates remain in place.
   EQ Export remains locked for 0 PEQ.
4. A high-confidence source/color fit can be corroborated by the
   independent same-frame native Y-grid: color score >= .95,
   alternative <= .87, margin >= .10, 100+ bins, grid confidence
   >= .95, source-vs-grid slope difference <= 8%, unique passing
   color. Native GRID alone can NEVER authorize a source.
5. Once that exact source and color are proved, subsequent workers
   try only the previously verified color; every subsequent frame
   still requires pixel matching and native Y-grid corroboration
   when the strong-fit fallback is used. New source clears this hint.
   No stale Y transform; native frame TTL remains 0.45 s.

## Tests
- test_v847_autoeq_bypass_grid.py: 9/9 PASS.
- Full V8.28–V8.47 Auto Phase / Auto EQ / FIR: 144/144 PASS.
- Offscreen Qt paint: Phase P95 2.22ms, Mag P95 2.38ms (40 frames).
- Python compileall and git diff --check PASS.
- No changes to Smaart, ASIO, soundcard, hardware, TRF, DSP or generator.

## HOLD
Real Smaart Y pan and zoom without flicker is NOT accepted yet.
Read-only observation showed strong source+grid evidence, but actual
overlay pointer-to-present timing was not measured after Smaart closed.
The saved sample rate is not a verified live audio-engine rate.
Data Bar internal identity is not a cryptographically verified API.
