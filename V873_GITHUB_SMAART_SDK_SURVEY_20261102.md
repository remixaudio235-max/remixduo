# RemiX Duo V8.73 — GitHub Smaart API / SDK Search (2026-11-02)

Active source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Branch: qa/remix-duo-v873-native-tf-reader
Previous checkpoint: cc764f4

## Outcome

**No publicly verified, complete official Smaart V3/V4 TF-stream SDK was
found in the GitHub searches performed.** Multiple open-source WebSocket
clients do exist, but their GET / status, SPL or command capabilities MUST
NOT be misrepresented as realtime Transfer Function Mag/Phase decoding.

Official vendor statement:
https://www.rationalacoustics.com/pages/integration-with-3rd-party-products
- Smaart JSON commands over WebSocket.
- API and SDK free upon request, not a public GitHub SDK release.
- Third-party FIR Designer and Lake can stream Smaart 8/9 TF.
Smaart client/server docs:
https://support.rationalacoustics.com/support/solutions/articles/150000183495-how-to-use-the-smaart-client-window
- Transfer Function live stream exists, 23 FPS default maximum.
- Plot-side smoothing/banding do not prove incoming raw-frame representation.

## Ranked Github findings

1. V4 WebSocket control client (real implementation; no TF stream decoder):
   https://github.com/bitfocus/companion-module-rationalacoustics-smaart4
   - index.js: ws://<host>:<port>/api/v4/ and JSON {sequenceNumber:1,action:"get"}.
   - MIT; old Companion module; control/command rather than raw TF.
2. V3 WebSocket control client (already present in local research):
   https://github.com/bitfocus/companion-module-rationalacoustics-smaart3
   - src/index.js: ws://<host>:<port>/api/v3/; GET/status and mutating controls.
   - MIT; status-only baseline in current readonly V8.68 adapter.
3. TypeScript Smaart V4 API client:
   https://github.com/jvhtec/streamdeck-lake-smaart
   - plugin/smaart/smaartClient.ts: /api/v4/, get activeMeasurements,
     get measurements, get activeCalibratedInputs, realtime SPL
     streamEndpoint, GET state, actions for generator/capture/delay.
   - IMPORTANT: SPL streamEndpoint is NOT TF stream; do NOT port its
     generator/capture/DSP/trace visibility mutations to Duo.
   - docs/smaart-suite-api.md contains a proposed getData transfer JSON
     example that was **not** verified against genuine SDK or code
     execution. Treat it as UNVERIFIED and DO NOT send it to Smaart.
4. BSK Smaart Companion:
   https://github.com/BSKapps/companion-module-bsk-smaart
   (local copy at D:\SMAART_API_RESEARCH\companion-module-bsk-smaart)
   - Smaart control and live SPL; no confirmed raw TF decoder.
5. Open Sound Meter related request (NOT a usable SDK):
   https://github.com/psmokotnin/osm/issues/132
   - A March 2026 request proposes implementing Smaart-API-compatible
     *server* behavior so Waves TRACT can connect to OSM.
   - Search found no merged SDK/TF-stream PR. Could be an independent
     compatibility research lead, not evidence of V3/V4 client decoder.
6. https://github.com/jorembet/OpenSmaartLab
   - Independent C++/JUCE dual-channel TF analyzer with Mag/Phase/Coh.
   - NOT a Smaart API implementation; would open audio I/O and therefore
     is not suitable as the Duo passive Smaart Live TF Reader.
7. https://github.com/camprevail/SmaartFroge
   - Live SPL API application. NOT TF.
8. https://github.com/jianghuye/SmaartHook
   - Windows API hooking and DLL injection for Smaart UI localization,
     NOT an SDK or validated TF API. DO NOT inject/hook/replace DLLs in Smaart.

## Technical gates and next safe engineering action

- PASS: public example confirms WebSocket /api/v3/ for Smaart 8 and
  /api/v4/ for Smaart 9; JSON GET/status; V4 adapter feasibility.
- PASS: official Smaart docs confirm actual TF streaming exists in API.
- HOLD: exact TF subscription message, payload encoding, packet schema,
  bin units/ordering and frame provenance.
- HOLD: native Mag/Phase live stream A/B parity and coherence provenance.
- HOLD: Auto Phase / Auto EQ / Auto FIR real live hookup.

Next: on a user-started Smaart session with API enabled, perform ONLY
authorized/read-only GET and passive inbound WebSocket observation, with
no speculative command names, no stream playback, no generator/sweep/
capture or device routing. The official SDK is the only reliable basis
for a stream subscription until actual protocol evidence is acquired.

Do not edit overlay_v7.py or claim real TF connectivity. Retain
cc764f4 NativeSDKStream trust boundary and 41/41 unit regressions.
