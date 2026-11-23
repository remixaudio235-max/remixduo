# RemiX Dou V8.45 — FIR 1-tick / Smaart Fs / worker / safe offline exports

Date: 2026-10-31, Admin-PC.
Git baseline: 4f262f6, branch qa/remix-signal-v825-checkpoint.
Canonical app: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA.

## Previous code audit
- FIR inherited TFDialog: offered T1/T2/SUM regardless of currently ticked Smaart Data Bar Trace.
- FIR always used default fs=48000 and displayed hardcoded "48 kHz" even if Smaart saved rate changed.
- FIR design ran on Qt main UI thread, potentially blocking GUI.
- Export TXT/WAV was enabled from any non-None FIR result without verifying the source / Fs / taps were still valid.
- FIR's original 512/1024/2048/4096 tap magnitude-inverse, linear-phase solver, latency measurement and float32 output are retained.

## Implementation in signal_tools_gui_v813.FIRDialog
1. Replace legacy FIR source selector with read-only display of EXACTLY
   one stable verified native Data Bar tick, independently of the two
   AutoPhase traces. No SUM input and no manual T1/T2 choice.
2. Use read_saved_smaart_fs (existing V8.41 parser) to show Smaart
   saved sample rate; do not guess from TRF frequency grid, and reject
   computation if saved config is absent or changes before solve.
3. Read the selected TRF with pre/post stat checks and a SHA256 digest.
   A result belongs to the immutable (path,mtime_ns,size,generation),
   SHA256, saved Fs snapshot, number of taps, source name and run serial.
4. Move FIR solver onto one-worker ThreadPoolExecutor and deliver to Qt
   through EQFinished pyqtSignal. Worker result is accepted only when
   ticket, selected Trace, SHA, Fs and taps still match. Discard stale
   completion without claiming success. Source invalidation re-enables
   Compute button and disables both Export buttons.
5. Verify coefficients are finite, symmetric within 1e-9, have exactly
   requested taps and valid spectral response. Stop unexpected actual
   correction boost above +7.5 dB.
6. Export TXT and WAV are disabled until an approved result exists.
   Immediately before writing, recheck exact selected Data Bar token,
   source file timestamp/size and SHA256, Fs and taps; recheck again
   after file selection. Only save OFFLINE coefficients, never apply DSP.
7. Keep FIR panel integrated in the existing compact shared toolbar;
   no second app or GUI, no generator, no Smaart/audio I/O modification.

## QA
- test_v845_fir_one_trace.py 5/5 PASS:
  - zero/two/six ticks rejected; exactly one tick works without an
    AutoPhase two-trace pair.
  - asynchronous design 1024 taps / 48 kHz; symmetric coefficients,
    exact stored response, correct (N-1)/(2Fs) latency.
  - TXT export 1024 coefficients plus header, IEEE float32 WAV mono
    with sample-rate and tap count validated by binary parser.
  - selected Data Bar tick/source SHA changes disable exports.
  - changing saved Fs invalidates result and blocks compute until
    consistent; a source change during computation re-arms Compute.
  - independent 2048-tap scipy.signal.freqz parity on exact FFT bins,
    excluding numerically unstable deep Nyquist null interpolation.
- Full focused V8.28-V8.45 + AutoEQ/AutoPhase regression:
  127/127 PASS (11.26s).
- Python compileall PASS, Git diff --check PASS.
- Original V8.44 Qt Paint benchmark (before FIR change) separate from
  worker cost; no measurable end-to-end live mouse or FIR UI P95 claimed.

## Limitations / next milestones
- Fs is sourced from saved SmaartConfig.xml, not from Smaart audio
  engine live callback. Still HOLD on unsaved rate changes.
- Data Bar archive_order mapping has prior unproven original UI label
  identity risk. This step verifies a fresh single-tick token and
  source hash, not a cryptographic label-to-file Smaart API identity.
- Offline FIR preview remains the built-in compact FIR MiniPlot.
  It is NOT yet a source-registered native Magnitude/Phase overlay.
  Next FIR milestone: native MagFIR preview anchored to Smaart source
  and mode gating, FIR phase & group-delay view, actual-signal parity.
- Real GUI with visible Smaart and audio hardware is NOT tested here;
  live Smaart-dependent acceptance remains HOLD.
