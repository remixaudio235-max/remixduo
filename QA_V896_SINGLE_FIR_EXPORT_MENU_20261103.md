# RemiX Duo V8.96 — One-button FIR export layout (2026-11-03)

## Source and scope
- Canonical source tree: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`; repo root `D:\REMIX_AUTO_ALIGN_V6_DEV`.
- Windows Smaart integration changes: `signal_tools_gui_v813.py`.
- Preserve the shared FIR/DSP engine and `src/remix_duo/core` untouched.
- The latest Phase+ source behavior is retained: FIR PHASE+ automatically selects 4096 taps and uses Phase+; its checkbox stays checked and hidden in accord with the previously accepted user preference; the visible combo label now reads `FIR PHASE+ | Pha`.
- FIR MAG retains its independent tap selection. No generator, capture, audio or Smaart session writes.

## UI contract
- Replace three visible export buttons and the vendor combobox with ONE visible `XUẤT FIR` button.
- Click opens a single compact menu: `TXT chung (.txt)` or `Theo hãng DSP / Crossover` submenu of available named profile formats.
- No permanently visible legacy TXT, WAV, or DSP buttons, and no vendor combobox occupying dock space.
- Keep underlying export handlers as hidden compatibility endpoints to avoid breaking older APIs and regression tests; do not duplicate visible controls.
- Vendor names are *coefficient-format profiles*, not manufacturer-certified device-native installers. Never claim automatic upload/flash or particular model compatibility.
- A selected profile that supports fewer taps than the current FIR is disabled (for example 512-tap Bose ControlSpace vs 4096-tap Phase+). Never truncate, pad or fake a fit.
- FIR export eligibility requires the original SHA-256 / Smaart native single-tick / source / sampling-rate / HWND / mode/taps/range proof. Revalidate after the destination dialog, before writing any bytes.
- When a trace becomes stale (HOLD) or FIR parameters change, the one visible Export FIR button is disabled immediately; popup closes on transient HOLD.

## Acceptance
- New `test_v896_fir_single_export_menu.py` exercises single visible control, actual FIR 1024 TXT coefficients, named miniDSP TXT action, 4096 Phase+ manufacturer tap-limit rejection, stale preview invalidation and preserved Phase+ identity.
- Update `test_v884_logic_fixes.py` scroll acceptance to target the new visible export button (old invisible DSP button is no longer a valid viewport target).
- Previous tests for legacy handlers/export hashes continue to pass.
- Windows full offscreen regression via `D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe`: **518 passed / 1 skipped** on 78 `test_v8*.py` files plus `tests/contracts` and `tests/shared`, exit code 0.
- After the visible combo label change, targeted GUI/FIR tests: **6 passed**, exit code 0.
- Installed Windows EXE V8.84, macOS QA app and current Smaart license/session remain unchanged. The Windows source overlay needs a source restart for this GUI layout to show.
