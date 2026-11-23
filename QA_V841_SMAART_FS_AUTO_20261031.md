# RemiX Dou V8.41 — Auto EQ Fs automatically from saved Smaart settings

Date: 2026-10-31 / Admin-PC.
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA.
Starting Git HEAD: 9e95e4b.

## Request and observed facts
- User requested automatic Auto EQ sample rate, not a manually chosen rate
  every time an EQ is calculated.
- Actual read-only SmaartConfig.xml: Global/SampleRate=48000 Hz.
  All saved Sources/SourceN/SampleRate and Dests/DestN/SampleRate fields
  currently agree on 48000 Hz.
- The .trf reader uses frequency bins; do not infer the acquisition rate
  from a 20k frequency limit, spectral spacing or another application.

## Implementation
- smaart_fs_sync_v841.py: parse Smaart saved XML read-only; accept ONLY
  supported 44.1,48,88.2,96,192 kHz and only when Global and every saved
  source/dest rate agree. File stat must remain unchanged during read.
  Never edit Smaart, open an ASIO device or change a soundcard setting.
- signal_tools_gui_v813.EQDialog: Fs control is locked/read-only. It
  automatically displays "Fs 48 kHz • Smaart" from verified saved data;
  if source unknown/conflicted it shows a warning and refuses Auto EQ.
- Refresh from saved config every >=1 second during hub polling,
  and force-check at calculation time. Changing saved config invalidates
  old Auto EQ MagEQ/export and prevents stale worker result acceptance
  if Fs changes or the config is modified in flight.
- Keep Auto EQ ONE tick independently verified and Auto Phase TWO ticks;
  preserve native MagEQ, numbered PEQ markers, gradient, SUM Phase/Mag
  and crossover LF–HF highlights. No complex H(f), DSP, generator change.
- Adapted historical GUI tests so they no longer manually set Fs.

## Tests and performance
- Fresh targeted Fs XML tests: 44.1,48,88.2,96,192 kHz, unsupported Fs,
  missing/corrupt config, device/global disagreement, locked GUI,
  saved-config change invalidation and fail-closed path.
- Full V8.28–V8.41 + AutoEQ V0.19 regression: 111/111 PASS.
- 4096-bin / 40 frame Qt offscreen P95:
  Phase 1.68ms, Mag 1.83ms.
- Python compileall and git diff --check: PASS.
- No Smaart TRF, XML, DSP, generator, soundcard changes.

## Explicit limitation
- This is automatic synchronization to Smaart's last SAVED configuration.
  Smaart may have a different active DSP/audio rate if changed without
  saving. No live Smaart engine callback or read-only API is available
  in the current integration, so don't claim instantaneous true-live
  Fs parity. On saved conflict/absence, fail closed.
- After exact companion restart the read-only Fs UI should show 48k.
  Existing transient EQ proposal in RAM will need re-run; do not
  automatically recompute or change the user's target/trace.
