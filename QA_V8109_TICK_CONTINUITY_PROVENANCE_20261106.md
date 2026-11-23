# RemiX Duo V8.109 — SUM/MagEQ/FIR Tick Re-arm Continuity & Safety QA (2026-11-06)

## Scope and provenance
- QA source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA
- Branch: qa/remix-duo-v873-native-tf-reader, base HEAD 19350a5 (V8.106-108)
- Backup of original three modified files: D:\REMIX_DUO_CHECKPOINTS\V8109_TICK_CONTINUITY_20261106
- Full pre-P0 source checkpoint: D:\REMIX_DUO_CHECKPOINTS\P0_PRE_V8106_V8108_20261106_114905
- No changes to Smaart, hardware, generator, DSP, license, installed Windows V8.84, or existing watcher.
- No Smaart live process or RemiX Duo GUI was running when inspected; the legacy V8.27 autostart watcher remained active.

## Reproduced failures (RED against V8.108)
New: test_v8109_tick_continuity_provenance.py
- FIR preview unexpectedly invalidated by a single unknown tick pixel despite retained immutable same-Trace candidate.
- MagEQ presentation gate accepted two explicitly ON rows if a third row was UNKNOWN.
- MagEQ gate also accepted not-ready observer carrying a stale single_candidate.
- SUM display bridge kept previous pair for scanner resets, HWND changes, unsupported Smaart 8 or absent host, not just incomplete pixel captures.
- Initial suite: 7 FAIL, 2 PASS.

## V8.109 corrective changes
1. signal_tools_gui_v813.FIRDialog.refresh_sources:
   - Retain already calculated FIR data (do not recompute) when a partial/ambiguous viewport retains the same immutable single_candidate and zero or one known-ON rows.
   - Fail immediately on two or more known-ON rows, a complete zero-count, a different candidate, or unready scanner.
   - While suspended, disable all FIR exports and menus; NativeFIROverlay still has independent, 1.5 s, display-only proof and strict native frame/viewport verification.
   - When the identical file is reverified at 3/3, restore the approved preview without requiring recompute. File metadata/hash/Fs/taps/mode checks still apply via _same_approved_source.
2. mageq_presentation_gate_v853.presentation_tick_ok:
   - Refuse display on unready scanner, missing/inconsistent row map, or two known-ON rows even if another row is UNKNOWN.
   - Accept bounded display-only grace only for the matching, previously verified candidate and no explicit contradiction.
   - Does not authorize Export EQ, AutoEQ calculation, or PEQ drag.
3. overlay_v7.App._hold_selection_display:
   - Keep SUM only for known partial viewport/pixel READ status prefixes: Scroll changed, No unambiguous rows, Visible tick ambiguous, Tick chua xac minh, READ ERROR.
   - Immediately hide for absent Smaart, new HWND, Data Bar HOLD/reset/reinitialize, unsupported Smaart edition and pair path mismatch.
   - Same committed-pair and 1.5 s max grace unchanged; Solve remains disabled.

## Test evidence (2026-11-06 Admin-PC, offscreen)
- V8.109 + V8.107 + V8.106 + V8.108 + V8.53: 62 PASS; no failures.
- Shared + contracts: 72 PASS, 6 SKIP, zero failures.
- Full legacy runner: 421 PASS, 74 SKIP, 44 FAIL, 27 ERROR. This is NOT a full clean gate.
  - Required legacy Smaart Session Data fixtures are absent:
    C:\Users\Admin\Documents\Smaart Suite\Data\Transfer Function\Session Data\index.xml
    and named .trf files; Smaart Suite folder currently has only Config/Skins/log.
  - Controlled untouched baseline 19350a5 in isolated git worktree
    D:\REMIX_DUO_CHECKPOINTS\V8109_BASELINE_19350a5
    also fails: 395 PASS, 74 SKIP, 61 FAIL, 27 ERROR.
    Baseline differs from working QA due to absence of additional untracked fixture assets.
  - Do not infer that all legacy tests pass or that live Smaart fidelity is proven.

## Required native/live acceptance before release
- Neutralize V8.27 watcher double-launch risk in a controlled session, then launch exactly one QA overlay bound to the correct Smaart v9 PID/HWND.
- Verify two checked, visible TRFs for SUM; one checked TRF for MagEQ/FIR. Observe exact immutable source/FS/window and strict export/DSP gates.
- With no audio generator or speaker changes, verify 3/3 tick rearm under natural PrintWindow/viewport transient: window and graph continuity, not just selection_verified, and stale pixels never republished on source/HWND change.
- Capture screen+event log and report visible hide gaps before declaring no-blink LIVE PASS.
- Do not merge, replace installed EXE, or publish production as a result of unit QA alone.
