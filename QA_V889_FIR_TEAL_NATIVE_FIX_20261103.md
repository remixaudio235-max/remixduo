# RemiX Duo V8.89 QA — PhaseFIR native teal trace recovery
Date: 2026-11-03
Canonical source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Git root: D:\REMIX_AUTO_ALIGN_V6_DEV

## Real-machine findings (Admin-PC, Smaart Suite 9)
- User screenshot shows FIR PHASE, 1024 taps, LF 368 Hz, HF 3350 Hz, Fs 48 kHz, group delay 10.66 ms, but missing predicted PhaseFIR.
- Read-only native Smaart window: HWND 0xab0d26; Phase plot (252,84,1442,412); Mag plot (252,539,1442,412).
- Saved config verifies Phase and Mag smoothing ID 5 => 1/6 octave. Existing make_source() already applies coherence-weighted 1/6 octave smoothing to source.original_phase. Do not double smooth it.
- Live saved TRF source: TUNNINNGGG-4.trf (463 bins, 424 with coherence >= 0.6).
- Before fix: 0 recognized pixels across six color masks (cyan, blue, red, green, magenta, gold); native_fir_frame() returned None, so PhaseFIR HOLD was inevitable.
- Actual Smaart turquoise/teal trace sample: RGB (27,224,166) with thousands of valid plot pixels.
- Fix: add separate teal detection mask in smaart_native_mag_fit.trace_color_mask and in smaart_eq_color_select.choose_color_fit palette; reject cyan/green cross-matches and keep source/pixel score/identity gates.
- After fix on real saved TRF+actual PrintWindow: native_fir_frame present, mag color teal, phase_verified=True, phase_score=1.0; predicted phase points 416, RGBA phase raster 2,376,416 bytes, fresh native frame=True.
- Real FIR phase design: 1024 taps, 48,000 Hz, LF 368 / HF 3350, group delay 10.656ms. All coefficients finite. Temporary TXT and float WAV exports passed: 1024 samples at 48,000 Hz, with files deleted after QA.
- User-facing FIR preview cannot be considered visible until re-opening/re-designing in the running source overlay. PrintWindow proves engine's native drawing eligibility, not manual live mouse acceptance.

## Interaction coverage
- QA QtTest workflow: FIR MAG native LF/HF drag (separate from Auto Phase), design/worker, TXT/WAV button export, switch PHASE, old FIR invalidation, drag 368/3350, design/worker, WAV export, tab switch, HIDE and restored tool visibility.
- 22 focused tests passed before broad suite. Full new QtTest workflow passed. Regression tests reject teal/cyan/green confusion and require source-color phase pixels.
- The broad test suite must be recorded after its final run, not inferred from startup progress.

## Safety / deployment
- Smaart process 34140 remains online; no generator, sweep, ASIO/device opening, audio capture, hardware DSP writes, or changes to Smaart configuration.
- Windows live source overlay process 8612 was loaded before the code change and must be explicitly restarted to use this code.
- Preserve unrelated dirty entry.py and ui/workspace.py files (from the earlier offline source run), and retain Windows V8.84 installed binary and Mac V8.87 app unchanged.
- Native Mac live tick/axis verification remains HOLD. This change is Windows-specific Smaart color recognition within the canonical shared repo.

## Final QA evidence
- Windows QA v8 suite (72 files, existing Python 3.11 venv with websocket-client): 442 passed, 1 skipped in 46.82 seconds.
- QtTest full GUI FIR MAG -> PHASE -> LF/HF drag -> design -> TXT/WAV -> tab switch -> HIDE passed.
- No physical mouse-drag on live Smaart was certified by these tests; source overlay must be restarted for patch to load.

## Direct on-screen Windows/Smaart UI acceptance (post-checkpoint)
- Reloaded the real source overlay using Python PID 17828; original Smaart Suite PID 34140 kept alive.
- Clicked Auto FIR on the attached Smaart toolbar. Exactly one source TRF: TUNNINNGGG-4; Fs 48kHz.
- Mouse drag on the native MAG plot: LF 30 -> 368 Hz and HF 16000 -> 3350 Hz; both visual labels and FIR spin boxes matched exactly.
- Mouse click THIET KE FIR in MAG: native preview cyan MagFIR drawn on the Smaart plot, 1024 taps, delay 10.66ms.
- Switched MAG to PHASE with actual on-screen dropdown: previous MagFIR cleared, same LF/HF repositioned onto Phase plot.
- Mouse click THIET KE FIR in PHASE: PhaseFIR purple predicted curve drawn next to original teal phase, 1024 taps, 48kHz, 10.66ms.
- Native Phase preview sampled 14 consecutive screenshots with Smaart foreground continuously: 7021 purple pixels in each frame, 14/14 visible, no renderer flicker during this stable interval.
- Independent UX finding: temporary switch away from Smaart can invalidate verified one-trace selection and FIR computed result; returning requires clicking Design again. This is fail-closed behavior but a usability issue; do not automatically restore results without fresh tick/source/Fs/hash verification.
- Live Export dialogs not exercised; QtTest button/export workflow and temporary real-TRF TXT/WAV coefficients both PASS. No hardware writes or noise/sweep generated.
- Temporary screenshot evidence on Admin-PC: %TEMP%\\remix_fir_real_drag.png, remix_fir_mag_result_live.png, remix_fir_real_phase_mode.png, remix_fir_phase_result_live.png.
