# V8.80 source stability audit and API research — 2026-11-02

Exact source: D:/REMIX_AUTO_ALIGN_V6_DEV/windows_v8_27_MAG_NATIVE_SYNC_QA.
Working-tree changes preserved; installed EXE remains previous V8.77 package.
No Smaart/GUI/audio launch, generator, capture, DSP or production load traffic.
Guard: HOLD:NO_ACTIVE_OVERLAY,NO_SMAART_WINDOW. Watcher wrappers 8012/9056
observed with --watch command line; runtime PIDs must be rechecked each session.
LocalDev project_list returned tool error; ordinary filesystem audit used.

## Fixed with RED/GREEN evidence

1. NativeSDKWorker empty nonblocking adapter busy-spun 914139 calls/150ms.
   Added interruptible 5ms event wait only for None frames. Stop remains bounded.
2. NativeTFReader.ingest edition=[] raised unhashable TypeError before validation.
   Reject malformed edition/API types before indexing bindings.
Tests: test_v880_reader_stability.py, both failed before fix, both pass after.
Reader/API/strict tests: 69 PASS. Combined package/license/asset suite: 90 PASS.

## Synthetic saturation benchmark

Command: build Python -m pytest (listed test modules), then stress_v880_reader.py.
No network/GUI/audio. ThreadPool producers send immutable synthetic packets as
fast as possible; latency is ingest + latest including lock wait, not end-to-end
SDK/Qt latency. Python CPU time includes all producer threads. Samples bounded
at 10000 per producer; the observed runs remained below that bound.

| Bins | Traces | Duration | Frames | Aggregate fps | p50 ms | p95 ms | p99 ms | Max ms |
|---|---|---|---|---|---|---|---|---|
| 1024 | 1 | 3.000s | 9778 | 3259.3 | 0.277 | 0.465 | 0.697 | 7.012 |
| 4096 | 4 | 8.016s | 4398 | 548.7 | 1.243 | 24.940 | 68.488 | 695.412 |
| 32768 | 4 | 8.093s | 327 | 40.4 | 80.213 | 239.648 | 454.642 | 906.098 |

Zero rejected valid frames; TTL hides stale frames; cache never exceeds bound.
Separate tracemalloc test: 50000 two-bin packets, 2184 bytes retained / 3704 peak,
one cached frame. This measures Python allocations in that case, NOT RSS or
large-frame long-term leak freedom. No hours-long soak/full-GUI test performed.

High-bin mode is NOT accepted for 4x23fps: 92 aggregate fps target exceeds
measured 40.4fps. Bottleneck inferred from code and CPU saturation: Python scalar
validation under reader RLock (ingest line ~179) serializes producers/consumers.
Next step: validate outside critical section with binding snapshot/recheck and
generation protection; then benchmark paced traffic and frame-to-render latency.

## Remaining findings

- P1 performance: high-bin validation holds shared lock; do not promise native
  4-trace realtime at maximum bins before improving and testing this path.
- P1 responsiveness: remix_duo_license_v874.py apply_online (line ~383) calls
  synchronous activate_online_and_save on GUI thread. HTTP timeout is 8 seconds
  per request, and request-activation adds another request; timeout is not a
  total wall-clock deadline. Move network work to a worker, with progress,
  cancellation and dialog-lifetime guards. Not fixed in this bounded patch.
- Integration HOLD: solver_ready remains False; NativeSDKStream abstract methods
  are not a working SDK connector. Current solver uses saved snapshots.
- Existing installed EXE does not contain these new reader fixes until rebuilt.

## API opportunity map

Local evidence: D:/SMAART_API_RESEARCH/companion-module-bsk-smaart/src/main.js
pollOnce (~300), openSplStream (~355), src/api.js flattenMeasurements and
flattenCalibratedChannels. V4 Companion HELP/index.js mostly control commands.

1. Read measurement inventory, type, active flag and delay from named measurement
   GET responses: useful for diagnostics and identity checks. Active measurement
   is NOT equivalent to the two user-checked displayed traces; retain tick QA.
2. SPL calibrated-channel streamEndpoint, metric values, violations and thresholds:
   suitable for a monitor panel, only after version/auth and live payload QA.
   Local module sends a targetFPS SET on that stream; do not blindly reuse it
   during read-only discovery.
3. Native Spectrum/TF/Live IR streaming is officially supported. Obtain versioned
   SDK/frame schema; bind engine/trace/generation/time/coherence/delay, compare
   against Smaart and only then feed Auto Phase/EQ/FIR. Local inspected code does
   not establish TF binary decoding, units or subscriptions.
4. eqx rationalacoustics trace/crv/ascii and FIR converters are offline format
   references, not evidence of live SDK TF streaming.
5. Generator/start/stop/findDelay/capture/SET controls require explicit controlled
   workflows; they were neither run nor silently enabled by this audit.

Primary sources checked:
- https://www.rationalacoustics.com/pages/integration-with-3rd-party-products
- https://support.rationalacoustics.com/support/solutions/articles/150000183495-how-to-use-the-smaart-client-window
- https://support.rationalacoustics.com/support/solutions/articles/150000092223-tips-for-using-smaart-s-api-web-viewer-remote-client-third-party-integrations-etc-

Next safe command: run stress_v880_reader.py in the build Python; then perform a
reviewed SDK adapter milestone. Live/native acceptance remains HOLD without
running Smaart and independent numeric parity evidence.
