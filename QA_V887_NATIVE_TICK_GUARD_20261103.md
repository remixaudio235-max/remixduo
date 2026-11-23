# RemiX Duo V8.87 — Native tick fail-closed hardening (2026-11-03)

Canonical Windows source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`
Mac QA source mirror: `/Users/dinhtran/RemiX_Duo_Build/V887/source`
Repo Git root: `D:\REMIX_AUTO_ALIGN_V6_DEV`

## Code change

- `src/remix_duo/platforms/contracts.py`: add `SelectionEvidence.verified_selected(current, now, expected)` for both 1-trace Auto EQ/FIR and 2-trace Auto Phase, preserving existing `verified_pair`.
- Reject stale monotonic timestamps, wrong native window identity, missing/duplicate tick names, unknown/offscreen tick, incomplete AX row scan and unsupported expected trace counts.
- `src/remix_duo/ui/overlay.py`: Auto Phase/EQ/FIR action uses the same strict evidence gate rather than checking only count/window/timestamp.
- `tests/contracts/test_tick_selection_guard_v887.py`: regression tests for both counts and invalid AX evidence.

## Test evidence

- Windows Admin-PC `py -3.11 -m pytest -q tests/contracts tests/shared` with Qt offscreen: **55 passed**.
- MacBook Air arm64 `/Users/dinhtran/RemiX_Duo_Build/V886/.venv/bin/python -m pytest -q tests/contracts tests/shared` from mirrored V887 source, Qt offscreen: **53 passed, 2 skipped** (Windows-only).
- Tests do not activate a generator, sweep, capture, Smaart audio control or change the active installed app.

## Gate status and source safety

- Mac installed V8.87 remains `~/Applications/RemiXDuo_V887_Overlay_QA_Final.app`. The changes above are **SOURCE-ONLY**; do not attribute them to the existing DMG/app.
- Live Smaart identity, trace/axis/TF/Fs and SUM/MagEQ/FIR overlay still **HOLD**.
- Native GUI live verification blocked: Mac console session reports `CGSSessionScreenIsLocked=Yes` (3 November).
- Intel build and clean install, Apple Developer ID/notarization and public release still **HOLD**.
- Preserve V8.84 installed Windows and the complete V8.85/V8.86/V8.87 source directories; do not merge dirty legacy branches blindly.

## Next acceptance

1. Unlock Mac, keep licensed Smaart running, verify screen/Accessibility consent; run strictly read-only AX tick scan with a known single trace then exactly two traces.
2. Compare current native window/process IDs, selected names, frequency sampling and axes to Smaart for each observed frame; reject every ambiguous case.
3. Measure visual overlay latency and stale-data behavior on move/resize/minimize/Spaces/multi-display. Never touch Smaart generator/audio.
4. Only after those gates, rebuild a new QA DMG and separately test native Intel, signing, notarization on a clean device.
