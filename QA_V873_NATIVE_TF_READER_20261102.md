# RemiX Duo V8.73 — Native Smaart TF Reader — QA 2026-11-02

Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Git branch: qa/remix-duo-v873-native-tf-reader
Start: f9cfe30 / checkpoint/remix-duo-v873-handoff-20261102
Preserved baseline: V8.72 GUI, Auto Phase, Auto EQ, Auto FIR, exports.
No new source directory, worktree, audio I/O, Generator/Sweep/Capture, DSP write or Smaart restart.

## Documentary evidence (official Rational Acoustics)

- https://www.rationalacoustics.com/pages/integration-with-3rd-party-products
  Official API description: JSON commands over WebSocket, measurement data accessible.
  Official integration list says FIR Designer can stream live Spectrum + Transfer Function
  from Smaart 8 and 9; SDK is available free **upon request**.
- https://support.rationalacoustics.com/support/solutions/articles/150000183495-how-to-use-the-smaart-client-window
  Server-side stream supports Spectrum/TF; default max Spec/TF Stream FPS = 23.
  Display smoothing/banding are client-side post-processing; do not infer their
  values from raw packets or GUI pixel coordinates.
- Local third-party Companion example:
  D:\SMAART_API_RESEARCH\companion-module-rationalacoustics-smaart3\src\index.js
  Confirms V3 JSON GET/status at ws://host:port/api/v3/. Explicitly says V9 does not
  work with its V3 module. This is **not** documentation of TF subscription/encoding.
- Official SDK V3/V4 message/frame schemas were not present in
  D:\SMAART_API_RESEARCH at QA time. No subscription request or V4 URL has been guessed.

## Runtime inventory (read-only)

- Admin-PC: RemiX Duo overlay_v7.py wrapper PID 31652 (pythonw.exe,
  D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\pythonw.exe);
  child PID 29196 (Python311\pythonw.exe), both on CURRENT active source.
- Get-CimInstance Win32_Process | Where-Object Name -match 'Smaart'
  returned no process at QA time.
- No live Smaart 8 or Smaart 9 stream was recorded, replayed or invented.

## Implementation in original source

smaart_live_tf_reader_v873.py (new):
- Distinct exact (Smaart 8,V3) vs (Smaart 9,V4) API identity checks.
- SDKBinding for engine, trace, Fs, generation and documentary trust.
- TFPacket carries frequency bins, Mag dB, Phase rad, optional coherence/delay,
  source timestamp, sequence and monotonic receive time; optional data stay None.
- Rejects GET/status, offline .trf, wrong source, mismatched Fs/generation,
  nonfinite or misaligned bins, Nyquist violations, bad coherence, reordered
  sequence/source timestamps and unexpected frequency grid changes.
- Thread-safe latest-frame-wins store, at most 4 identities; TTL=1000 ms,
  invalidation on rebind and disconnect; no UI or audio threads touched.
- NativeSDKStream abstract official-SDK callback boundary; NativeSDKWorker has
  explicit start/stop, read-only contract, reconnect/backoff and new-generation
  requirement. No guessed TF socket command, endpoint, binary format or authentication.
- mark_parity always rejects and solver_ready always False until independent
  real-Smaart A/B parity is implemented and accepted.
- NOT yet wired into overlay_v7.py or Auto Phase/EQ/FIR.

test_v873_native_tf_reader.py (new): synthetic *contract* unit fixtures ONLY,
not proof of real streaming. Fail-closed gate, V8/V9 isolation, stale/foreign
data, coherence, Fs, length, worker safety and GUI/audio isolation.

## Gate ledger — strict PASS vs HOLD

| Gate | Status | Evidence / blocker |
| --- | --- | --- |
| G0a streaming capability | PASS (documentation) | Rational Acoustics confirms live TF over API |
| G0b V3/V4 subscription and TF binary/JSON schema | HOLD | Official SDK not yet available |
| G1a safe native TF inbox + worker / contract unit QA | PASS | test_v873_native_tf_reader.py |
| G1b actual subscribed V8/V9 live TF frames | HOLD | Missing SDK schema + no Smaart running |
| G2a engine/trace/Fs/seq/timestamp validation tests | PASS | Negative-path unit QA |
| G2b real engine and trace provenance | HOLD | No genuine stream/frame capture |
| G3 Smaart 8 same-trace parity | HOLD | No running Smaart 8 and no authenticated V3 stream |
| G3 Smaart 9 same-trace parity | HOLD | No running Smaart 9 and no authenticated V4 stream |
| G4 Auto Phase/EQ/FIR production stream wiring | HOLD | Must follow G1b+G2b+G3 |
| V8.72 targeted baseline regression | PASS | 19 legacy tests green |

## QA commands and results

Executed with:
D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe

From active source directory:
python -m pytest -q -x test_v873_native_tf_reader.py test_v872_multi_dsp_export.py test_v871_fir_v8_offline.py test_v870_v8_native_sidebar.py test_v868_smaart8_api_overlay.py test_v868_paths.py test_v868_databar.py

Observed: **41 passed in 4.68s**. This is software unit/regression QA only.
Production source is unchanged at GUI entrypoint; no active process killed/restarted.

## Exact continuation once official SDK arrives

1. Obtain official Smaart V8 V3 and Smaart V9 V4 SDK; identify documented API
   subscription/handshake, authorization, frame encoding, IDs, Fs, sample
   timing/sequence, Mag/Phase/coherence and optional delay semantics separately.
2. Implement specific SDK adapter(s) behind NativeSDKStream; no guesswork,
   no undocumented mutating commands; preserve original packet bytes in QA.
3. Verify engine/trace identity and timestamp provenance against Smaart host;
   require source generation changes on reconnect.
4. Capture a real frame from each edition under user-controlled Smaart sessions;
   A/B Mag/Phase unwrapped/wrapped, coherence, Fs, delay, frequency grid and
   client-side smoothing with Smaart on the SAME verified engine+trace.
5. Only then enable Auto Phase, Auto EQ and Auto FIR using provenance-gated
   snapshots with explicit stale-generation cancellation and no per-frame FIR design.
