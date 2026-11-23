# RemiX Duo V8.87+ — FIR direct LF/HF drag on Smaart plots
Date: 2026-11-03

Source root: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Existing Windows overlay entry: overlay_v7.py

## Change
- Auto FIR now has two interactive LF and HF labels and full-height 17px grab strips on the native Smaart plot, using the same ROIMarker/ROILineGrip behavior as Auto Phase.
- With FIR MAG, handles and guide band appear on Magnitude; with FIR PHASE they appear on Phase.
- Control values mirror the FIR sidebar QSpinBox LF/HF and preserve the original one-trace FIR solver, original TRF evidence, output provenance and offline-only DSP behavior.
- FIR controls have their own LF/HF state, not the Auto Phase/Auto EQ state.
- Both drag and direct spin edits enforce LF>=20 Hz, HF<=20kHz and HF>=2*LF (minimum one octave); no frequency swapping.
- Changing the working range invalidates old computed preview and TXT/WAV/DSP export immediately. FIR design must be run again explicitly. No FFT, generator or audio I/O from drag callbacks.
- FIR editing guides appear even before the first computed FIR; this MUST NOT be interpreted as a valid native FIR response. Existing MagFIR/PhaseFIR curves remain strictly gated by accepted native source/frame/axis.
- Handles hide on tab change, HIDE/LIVE, unverified/missing target or lost foreground; they reposition on target plot geometry changes.
- The installed Windows V8.84 and the earlier Mac ARM V8.87 bundle remain unmodified.

## QA
- Windows test selection: 84 passed (v888 FIR UI, v842 EQ drag, v861 FIR range, v862 FIR GUI/math, v845 FIR single trace, v846 native FIR, v863 dock, portable contract/shared).
- Additional manual spin / min-octave test: 4/4 v888 tests PASS.
- Qt test ran offscreen, without sound generation, physical DSP, or Smaart capture.
- Live physical click/drag on Smaart is NOT yet certified by the above tests; inspect manual UI after restart.
- macOS Smaart native overlay/axis tick remains HOLD; this patch targets the existing Windows Smaart overlay integration.
- Git scope: commit only overlay_v7.py, signal_tools_gui_v813.py, fir_roi_v888.py, test_v888_fir_direct_drag.py and this report. Preserve unrelated local edits to src/remix_duo/entry.py and src/remix_duo/ui/workspace.py.

## Manual acceptance
1. Smaart Suite open with harmless/no-generator session, open Auto FIR. Move LF/HF by grabbing their labels and vertical lines on Mag plot.
2. Compare each value against FIR sidebar while dragging, including edges, crossing prohibition, change in window position/size, monitor changes.
3. Switch FIR MAG -> FIR PHASE: guides follow Phase plot; switch back: Mag plot; Auto Phase LF/HF unchanged.
4. Build a FIR from exactly one verified trace; change LF/HF: old FIR curve/export is invalidated; compute a new FIR and check native pixel correlation.
5. HIDE/LIVE hides all FIR grab strips, Smaart plot remains clickable everywhere else.
