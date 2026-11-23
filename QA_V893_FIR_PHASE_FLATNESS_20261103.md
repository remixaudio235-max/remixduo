# RemiX Duo V8.92 / V8.93 — Source QA: FIR preview recovery and phase-quality truth
Date: 2026-11-03
Canonical shared source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
Git root: D:\REMIX_AUTO_ALIGN_V6_DEV

## Actual Smaart live findings
- On Admin-PC Smaart 9 PID 34140, RemiX Duo source overlay PID 15108 (prior running code), real PhaseFIR purple curve did overlay the teal reference trace when opening Auto FIR. Screenshot: %TEMP%\remix_fir_after_select.png.
- Measured trace TUNNINNGGG-4, saved Fs 48 kHz, 1024 taps, LF 111 Hz, HF 310 Hz, estimated FIR delay 10.656 ms.
- After foreground switched to Chrome and back, the physical PhaseFIR disappeared and the FIR summary still showed 1024 taps. Clicking design without freshly verified single TRF produced "FIR cần đúng 1 Trace tick đã xác minh". That observed fail-closed handling hid the display AND discarded previously accepted local taps.
- Concurrent Chrome input caused hit-target identity to change. Live HF drag and post-fix live export were NOT certified. No unsupported claims of PASS.
- No Smaart generator/sweep, audio I/O or hardware DSP writes.

## Quantitative physical FIR evidence (same original TRF)
Diagnostic runs of unchanged solver design_phase_only_fir with exact measured complex H, coherence >=0.75, Fs 48k:
- Band 111-310 Hz: pre Excess Phase RMS=33.760 degrees; after FIR 1024=32.969 degrees (improvement 2.3%). 2048=29.545 degrees (12.5%); 4096=26.895 degrees (20.3%). The FIR phase is real and finite but cannot make this band flat at 1024 taps.
- Band 368-3350 Hz: before=36.784 deg, after FIR 1024=19.918 deg (improvement 45.9%), after 4096=19.805 deg (46.2%).
- Band 60-3500 Hz: baseline solver refused all tested taps due to >1.5dB actual ripple, correctly HOLD rather than forge valid FIR.
- A proper FIR linear-phase centering delay yields an absolute phase slope; flattening must be evaluated in an *excess-phase, delay-compensated* domain. Current solver fits bulk propagation delay and limits phase correction to +/-75 deg with 1/3-octave smoothing/taper. Narrow LF/HF work bands and low tap count limit achievable improvement.

## Source modifications
- src/remix_duo/core/fir_preview.py (shared): phase_excess_rms computes before/after coherent, detrended RMS in active LF/HF from measured complex H and actual FIR taps; records metrics in FIRSource. No change to FIR design, coefficient export, amplitude limits or Smaart behavior.
- signal_tools_gui_v813.py (Windows integration): show excess-phase RMS and phase-quality warning when improvement is <20%; clarify result is not the absolute raw phase slope.
- signal_tools_gui_v813.py: retain immutable FIR preview during transient one-tick expiry, HOLD exports/paint until fresh 3/3; resume ONLY after matching original file SHA-256/size/mtime, Smaart HWND, saved Fs, FIR taps/mode/range and original source identity. A changed source, two ticks or UI parameter change fully invalidates FIR.
- test_v892_fir_safe_focus_resume.py and test_v893_fir_phase_quality.py added. Independent targeted QA 13/13 for focus workflow and original FIR tests, then 9/9 for quality and focus subset.

## Acceptance gate
- Source does NOT yet update the already running Windows Overlay PID 15108. Restart only that source process after further manual live acceptance and when no other user is actively using Chrome/Smaart.
- Need revisit real physical drag with verified HWND owner and actual Qt export picker. Do not count QtTest as physical mouse proof.
- Final Windows full regression: 76 test_v8*.py files plus tests/contracts and tests/shared: **513 passed, 1 skipped in 58.47s**, process exit 0. (The 1 skip is platform-specific.)
- Git checkpoint must include only src/remix_duo/core/fir_preview.py, signal_tools_gui_v813.py, tests v892/v893 and this report; unrelated dirty source remains untouched.
- Mac native Overlay/tick/axis remains HOLD and Mac bundle was not replaced in this operation.
- Preserve unrelated dirty source files: src/remix_duo/entry.py and src/remix_duo/ui/workspace.py; do not modify installed V8.84 Windows or original V8.85/V8.86 source folders.
