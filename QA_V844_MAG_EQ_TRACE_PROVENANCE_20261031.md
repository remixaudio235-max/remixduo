# RemiX Dou V8.44 — AutoEQ source/native Mag pixel provenance and export guard

Date: 2026-10-31 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Base commit: 324ebd2 (V8.43)
Scope: Auto EQ safety and one-frame native pixel anchoring.
No Smaart or soundcard control, generator, sweep, DSP write, or TRF mutation.

## P0 repairs
1. Native GRID alone DOES NOT prove TRF identity. V8.40 explicitly
   accepted GRID even with color fit None; this is forbidden now.
   native_fit_worker demands a high-confidence, unambiguous native
   pixel curve match from original Smaart PrintWindow against the
   original Smaart TRF Mag supplied for this proposal.
   Color palette now includes cyan, blue, red, magenta, gold.
   Confidence threshold >=0.78, >=55 trusted bins plus the original
   fit-native requirements for distribution and alternative solutions.
2. The actual source-fitted pixel Y transform, including any native
   display dB offset, anchors the entire corrected MagEQ; saved grid
   dB/interval is only an optional cross-check, not an absolute source
   offset. GRID and color read from same PrintWindow snapshot.
3. FitFrame now records source_identity, identity_verified, native
   HWND, window/plot rectangle, creation epoch and optional grid parity.
   The same immutable frame is passed to MagEQ line, original Mag
   geometry, boost/cut gradients and numbered PEQ markers.
4. Old native Mag Y transforms expire after 0.45 seconds (prior 3.2s).
   Worker is checked/requested at 0.25s cadence (prior 1.0s) and works
   off Qt thread. A failed/stale frame hides the overlay and Export
   until fresh verification; no stale extrapolation after detection.
5. Selected Data Bar exact path/mtime/size/generation token, saved Fs,
   source SHA256 bytes, MagSource.source_identity, and native pixel
   verified frame are required together. Native overlay must NOT
   display with wrong/missing token; Export button cannot enable from
   PREVIEW_READY alone, and opening export revalidates current source
   hash and native frame. If the selected file disappears or changes
   during worker completion, fail-closed instead of a Qt callback crash.
6. Test fixtures updated to model P0 (real file token, native fit and
   source-identity binding) instead of treating synthetic GRID as proof.

## Verification
- Full V8.28–V8.44 + AutoEQ regression 122/122 PASS, 7.78s.
- test_v844_mageq_provenance.py 4/4 PASS (same-frame transforms,
  pixel offset drag, frame expiry same HWND, source SHA removal/change).
- Synthetic native positive export gate also PASS in updated
  test_export_eq_v08; no native frame -> Export disabled.
- Compiled all affected modules; git diff --check PASS.
- Qt offscreen 4096-bin / 40 samples: Phase P95=1.54ms,
  Mag P95=1.27ms. NOT full live pointer-to-display latency.

## Read-only evidence on saved Smaart screen
- QA_V840_AUTOEQ_SELECT.png with stored 0 delay-2.trf:
  native red curve score 0.525 (below 0.78) and ambiguous alternative
  0.50. Strong source identity NOT established.
- Legacy QA_V837_LIVE_AFTER_SCREEN.png native red score 0.583
  (below threshold), and is also not proven the same source.
- Therefore both historical image pairs are explicitly HOLD for
  native pixel source verification. Lowering the threshold to force
  display would reintroduce P0 wrong-trace risk.
- Offline color fitting ~77–90 ms for the five candidate masks; this
  excludes live PrintWindow and worker scheduling overhead.

## Remaining (NOT claimed PASS)
- REAL Smaart live pan/zoom/trace selection and pixel match cannot be
  checked while Smaart is closed. Need visible real application with
  exact tick and source; verify zero, one, two, six ticks, source
  filename identity, native Y pan and Zoom, MagEq/gradient/markers
  fixed relative to the original Mag, Export allowed only on proof.
- Native X math uses standard 20 Hz–20 kHz log scale. A different
  Smaart X viewport is not calibrated by live axis labeling and must
  HOLD if pixel match fails. True arbitrary X zoom remains incomplete.
- Pixel signal-shape correlation is independent visual evidence but
  not a cryptographic identity of Smaart's internal Data Bar row.
  The unverified archive_order mapping remains an external provenance
  limitation. If original and another displayed curve are
  indistinguishable, pixel proof alone cannot guarantee file naming.
- Live GUI P95 <33.33ms and flicker-free dragging unverified.
  DO NOT claim absolute real-time MagEq follow performance yet.
