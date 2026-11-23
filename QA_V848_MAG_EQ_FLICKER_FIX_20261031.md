# RemiX Dou V8.48 — Native MagEQ flicker audit and focused remediation

Date: 2026-10-31 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Base HEAD: 33ddfb9, branch qa/remix-signal-v825-checkpoint

## Reproduced from user screenshot and source
The user selected "4,8 ms delay-1" with Auto EQ PREVIEW_READY,
five PEQ and WRMS 2.43 -> 1.72 dB. Native MagEQ intermittently
disappeared even though the solver still had a valid proposal.

Independent root-cause pathways:
- Native verified frame max age 0.45s; worker poll every 150ms,
  submission gated to >0.25s and multicolor native fitting may
  exceed 450ms. Rendering cleared frame between valid updates.
- One-tick identity freshness 1.5s. A transient failed Data Bar scan
  cleared generation and GUI invalidated all PEQ results, rather than
  suspending the display until the same trace was reverified.
- Warm near-pixel fit can have score plateaus due to 3px expanded
  color mask, allowing accumulated Y-center drift across static frames.

## Changes
1. Warm pixel re-registration on the SAME source identity and
   previously verified trace color from NEW original-Smaart PrintWindow
   pixel captures, same HWND/window/plot and independent native Y-grid.
   Uses color mask and 2D Y-center/scale search, tests over 3 regions.
   Rejects wrong source/color, stale viewport, absent native pixel,
   weak confidence, inconsistent Y-scale. A prior fit is only a seed,
   NEVER a published new frame without new pixel verification.
2. Candidate center/scale continuity preference plus direct color-hit
   weighting resolves native stroke dilation ambiguity. It does not
   freeze a genuine Y pan. Tested moving Y by 26px.
3. Warm native timer adjusted 150ms -> 90ms, request cadence
   250ms -> 100ms. Existing 450ms strict stale-frame lifetime kept.
   This is a latency reduction, NOT permission to paint stale MagEQ.
4. Native scan transient/scroll failures SUSPEND one-tick lock,
   require fresh 3 scans, but preserve immutable candidate ID and
   generation. EQ GUI preserves approved result for same unverified
   candidate while the rendering/export gates remain CLOSED.
   An explicit proven Trace change still invalidates the old proposal.
5. New separate MagEQ HOLD/LIVE line in the right EQ panel.
   PREVIEW_READY means the solver finished, while MagEQ LIVE requires
   native drawn geometry from the same approved source; HOLD
   explicitly identifies missing pixel/Y evidence or tick verification.
6. Auto Phase/TF, Smaart original traces, generator, DSP, and FIR
   solver are not modified.

## QA evidence
- test_v848_mageq_no_blink.py: 5/5 PASS after final pixel weighting
  and continuity fix. 12 identical frames: zero center drift;
  genuine 26px Y pan: within 2px. New snapshot timestamp verified.
  Transient scan retains source generation but never grants an
  unverified current token; source change fails closed.
- 25-frame synthetic native matcher benchmark before direct-color
  weighting: P50 59.83ms, P95 69.67ms, 0.0px drift.
  Not the physical full PrintWindow+worker+Qt presented latency.
- Final focused V8.37–V8.48 Mag/TF regression: 43/43 PASS.
- Python compileall and git diff --check PASS.
- A broader 149-test run before final continuity fix gave
  134 PASS, 15 FAIL. Two new pixel-pan assertions caused 2 failures,
  corrected later and revalidated in 43/43 focused tests. The other
  13 failures were in Data Bar-dependent tests because real Smaart
  Session Data currently contains one or more .trf files not mapped
  consistently by index.xml, specifically
  "Unindexed .trf older than Smaart index; ambiguous order".
  User's Smaart files/index were NOT modified. This full test suite
  has NOT been represented as all-pass.
- Read-only real Smaart on this session: on the current displayed
  viewport, grid confidence 1.00, but stored
  4,8 ms delay-1.trf scored only blue 0.303 / red 0.516. Native match
  correctly HOLDS; this is not evidence of a passed live overlay.
  Earlier screenshot source-match was reported blue score 1.0 but
  the Smaart display/source subsequently changed.

## Live acceptance explicitly HOLD
- Need Smaart visible with exactly one selected trace whose pixels
  match the saved TRF. Check live MagEq 5 PEQ, color, axis drag,
  no-flicker 30-60 seconds, native Y follow and 0/2-tick reset.
- Failure of the current Data Bar/index.xml mapping requires
  authoritative recovery after Smaart saves/reindexes the session;
  do not silently guess row order or rewrite native Smaart files.
- MagEQ Export remains protected by one tick + Fs + TRF SHA +
  verified native pixels; no DSP writes.
