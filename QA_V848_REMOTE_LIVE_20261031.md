# RemiX Dou V8.48 — Remote Desktop live MagEQ QA (31 October 2026)

Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Git HEAD at QA: bb5a2c1
Host: Admin-PC via Remote Desktop Commander.

## Direct actions performed
- Verified source and process ownership, launched the canonical companion.
- Inspected native Smaart and companion Qt windows, plus real desktop screenshots.
- Verified Smaart UIA had 111 Data Bar rows; when saved index.xml was present,
  archive_order resolved all 111 .trf entries in the proper indexed order.
- One read-only full Data Bar scan (temporary scroll restored automatically)
  found one tick, TUNNINNGGG-9.trf.
- Switched the actual RemiX Dou UI from Auto Phase to Auto EQ.
- Auto EQ showed TUNNINNGGG-9 / PREVIEW_READY / 9 PEQ and
  WRMS 4.94 to 3.74 dB, verified visually on the desktop.
- Matched that TRF against desktop pixels from the same screen:
  blue color fit 0.21, red fit 0.33, below 0.78 required for display.
- In a later PrintWindow sample, blue/red native mask counts were zero
  although the saved desktop screenshot contained their color curves.
  This suggests a foreground/GPU capture reliability issue, but does
  not authorize an unverified desktop capture fallback.
- Smaart process and saved index.xml were observed present in some
  checks but unavailable in others; session state did not stay stable.
- No soundcard/ASIO, generator, sweep, original TRF, Smaart DSP,
  EQ export, hardware, or saved Smaart configuration was modified.

## Objective QA
- Full selected regression after index recovery: 149/149 PASS, exit 0.
- Qt offscreen 40 samples: Phase P95 1.92ms, Mag P95 1.67ms.
- No source-code changes; original V8.48 Git HEAD bb5a2c1 retained.
- Started one debug-capable companion with stdout/stderr at
  QA_V848_STARTUP_DEBUG.log and QA_V848_STARTUP_DEBUG_ERROR.log.

## HOLD
MagEQ non-blinking live rendering is NOT yet verified.
Pixel/source binding fails on this selected TRF. Do not lower the score
threshold or treat PREVIEW_READY as renderer verified. Additional work
requires trustworthy per-frame native capture and Magnitude X/Y viewport
calibration, including source identity, and a stable Smaart session.
Do not invent an index mapping or forcibly restart Smaart.
