# RemiX Duo V8.93 — Windows Smaart Live GUI QA (2026-11-03)

## Production-safe source / process identity
- Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA (complete tree; do not copy src alone)
- Git HEAD at startup: 7d0c710; branch qa/remix-duo-v873-native-tf-reader.
- Old overlay PID 15108 was confirmed by command line and single Qt hub HWND, then closed; WM_CLOSE alone only hid the UI so the verified process was terminated. No other Python or Smaart processes were touched.
- New source launched by `py -3.11 -X faulthandler .\overlay_v7.py`, PID 31024. Smaart Suite PID 23344 remained running/responsive. RemiX hub and right FIR dock were confirmed visible on actual desktop, not merely through mocked Qt.
- No generator/sweep/audio I/O, device changes, DSP hardware writes, or license changes.

## Real desktop acceptance
1. PASS — new source overlay toolbar + FIR dock display on Smaart 9; source new diagnostic 'Excess RMS' appears in FIR result. Real screenshots %TEMP%\remix_v893_after_fir_focus_check.png and %TEMP%\remix_v893_fir_current_full.png.
2. PASS — PhaseFIR purple predicted line appeared next to actual teal source in one live frame (screenshot %TEMP%\remix_v893_fir_current_full.png).
3. PASS — physically dragged the verified Qt HF grip HWND (owner PID 31024) on Phase plot. LF remained ~114 Hz, HF moved from ~317 Hz to ~851 Hz. Screenshot %TEMP%\remix_v893_hf_drag_real.png. Previous prediction vanished; TXT/WAV/DSP export buttons disabled, recomputation required.
4. BLOCKED — clicked actual `THIẾT KẾ FIR` button, verified owner PID 31024 and foreground PID 23344. Live GUI displayed 'FIR cần đúng 1 Trace tick đã xác minh trong Smaart'. No new FIR computed; no false export or phase flattening claim. Screenshot %TEMP%\remix_v893_fir_recompute_after_hf_drag.png.
5. Observed LF/HF changed between some capture frames without a confirmed single action; do not certify multi-action ROI stability while simultaneous foreground/user input may be present.
6. NOT RUN live export picker because native one-trace selection gate blocked recomputation and export was correctly disabled. Earlier Qt offscreen export tests remain useful but are not physical desktop verification.
7. Chrome stole foreground intermittently. Overlay correctly hid while it was not target foreground and redisplayed after Smaart activation. No native audio session disturbance detected.

## QA / evidence / remaining issue
- Previous full regression on unchanged committed source: 513 passed / 1 skipped; new full live actions are recorded above.
- Need diagnose LiveDataBarV7 one-tick native selection: full scan `initialize()` mapping, PrintWindow visible rows, row_seen_at <=1.5s, single_stable 3/3, scrolling and hidden-active invalidation. The current displayed Smaart trace title alone is NOT proof of the Data Bar tick state.
- Never bypass `current_single()`, fake coherence, or paint/export previous FIR when source or session is unverified.
- Recheck LF/HF physical gestures and actual export TXT/WAV after one verified tick has been accepted, and ensure native PhaseFIR parity with actual source.
- This is a QA report only: source is running, but full live GUI acceptance is HOLD.
