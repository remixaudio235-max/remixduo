# RemiX Duo V8.73 - GitHub Bitfocus API V3/V4 Read-Only Integration QA

Date: 2026-11-02 Asia/Ho_Chi_Minh
Repo: D:\REMIX_AUTO_ALIGN_V6_DEV
Source (unchanged): D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Branch: qa/remix-duo-v873-native-tf-reader
Baseline at task start: c366003
Rollback: checkpoint/remix-duo-v873-handoff-20261102

## Upstream code examined (GitHub connector)

V3 (Smaart 8):
https://github.com/bitfocus/companion-module-rationalacoustics-smaart3/blob/main/src/index.js
Evidence: URL ws://host:port/api/v3/, initial JSON
{"sequenceNumber":1,"action":"get"}, response.error, response.authenticationRequired.
V4 (Smaart 9):
https://github.com/bitfocus/companion-module-rationalacoustics-smaart4/blob/main/index.js
Evidence: URL ws://host:port/api/v4/, identical initial JSON GET.
V4 README/HELP contains generator and control commands; those are NOT ported.

These public Bitfocus modules are control/GET clients, NOT established native TF
Mag/Phase frame decoders. Versioned URL does not establish TF streaming.

## Added in active source

- smaart_api_v3_v4_readonly_v873.py
  Exact V3/V4 URL mapping, no guessed alternate endpoints, and no V3 fallback
  on a V9 executable. Only one fixed outbound message: action GET. No password
  submit, no SET, no generator, no measurement start, no sweep, no capture, no
  audio I/O or DSP write.
  Before opening socket: inspect genuine Smaart executable and Windows file
  version, require correct major and listener ownership by that exact PID.
  During handshake: strict sequence+response structure, authentication/error
  check, and repeat PID+listener verification to prevent reuse/foreign port.
  Bind host only to 127.0.0.1; bounded response size/time; optional passive
  observation <=2 s stores only length, SHA256 and unverified message kind.
  Does NOT feed GET or unsolicited frames into NativeTFReader or solvers.
  User-triggered CLI --edition 8 or 9, optional --pid, no auto Smaart startup.
- test_v873_smaart_v3_v4_readonly.py
  Unit fixtures for actual GitHub URL and request syntax (NOT live TF data).
  Version isolation, timeout/port ownership, auth challenge fail-closed,
  malformed/wrong seq/error, PID replacement, oversize, observer metadata,
  stream-not-verified invariant, and no-actual-Smaart behavior.

## Executed test suite

D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe -m pytest -q -x
  test_v873_smaart_v3_v4_readonly.py test_v873_native_tf_reader.py
  test_v872_multi_dsp_export.py test_v871_fir_v8_offline.py
  test_v870_v8_native_sidebar.py test_v868_smaart8_api_overlay.py
  test_v868_paths.py test_v868_databar.py

RESULT: **62 passed in 7.51s**. Includes existing V8.72 / V8.73 QA.
No live Smaart process started. Existing Duo process tree left untouched.

## Device read-only checks

- Get-CimInstance Win32_Process | Where-Object Name -match 'Smaart'
  => no matching process.
- Get-NetTCPConnection -LocalPort 26000 -State Listen => no listener.
- Duo overlay_v7.py still running at wrapper PID 31652 and child PID 29196,
  both from original active source (observation only).
- Explicit CLI --edition 8 => {"status":"SMAART_NOT_RUNNING",
  "tf_stream_verified":false,"engine_verified":false,"trace_verified":false}
- Explicit CLI --edition 9 => same status, same false proof fields.

## Honest gate ledger

| Gate | Outcome | Why |
|---|---|---|
| Bitfocus V3/V4 URL and GET request reference | PASS | GitHub source inspected |
| Dedicated V3/V4 read-only transport and safe JSON checks | PASS (unit) | 62/62 QA |
| Process identity, listener PID, auth, sequence safeguards | PASS (unit) | Negative-path cases |
| Real Smaart V3 handshake | HOLD | Smaart 8 not running |
| Real Smaart V4 handshake | HOLD | Smaart 9 not running |
| Actual TF subscription and payload decoding | HOLD | Bitfocus GET is status only |
| Engine/Trace/Fs/timestamp from genuine native TF | HOLD | No genuine frames |
| Same-trace Mag/Phase parity with Smaart 8 | HOLD | No genuine frames |
| Same-trace Mag/Phase parity with Smaart 9 | HOLD | No genuine frames |
| Auto Phase, Auto EQ, Auto FIR solver realtime | HOLD | Strict dependency on parity |
| V8.72 GUI and audio safety | PASS (unchanged sources and regression) | No GUI restart, no audio actions |

## Next live QA (no generator/capture)

User starts the licensed Smaart version, enables API, with the soundcard
and existing measurements left under user control. Run only:

cd D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
& 'D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe' smaart_api_v3_v4_readonly_v873.py --edition 8 --observe-seconds 2

OR (separately)

& 'D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe' smaart_api_v3_v4_readonly_v873.py --edition 9 --observe-seconds 2

A GET_CONFIRMED_NOT_TF_STREAM result proves only read-only API connection.
No TF payload must be claimed from GET or unverified passive data.
Further documented TF stream negotiation/decoder and same-trace parity
required before any real solver input. Preserve V8.72 GUI and other dirty files.
