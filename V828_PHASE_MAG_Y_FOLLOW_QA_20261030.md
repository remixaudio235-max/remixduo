# V8.28 Phase/Mag signed Y-follow — QA handoff
Date: 2026-10-30. Source updated in-place: windows_v8_27_MAG_NATIVE_SYNC_QA.

## Scope
- SUM Phase and SUM Mag use the same validated signed pixel-to-Y viewport mapping.
- Positive native Smaart trace shift moves its corresponding SUM overlay down; negative shifts move it up.
- Independent Phase/Mag frame timestamp watermarks reject out-of-order frames and low-confidence/old frames.
- Stale absolute native-axis results cannot undo a newer relative pan (generation in callback key).
- Temporary ambiguous Mag fit no longer hides a previously verified calibration immediately.
- Mag remains fail-closed until its native axis has been registered.
- No modification to saved TF complex H, coherence, delay, PEQ, DSP, .trf, Generator, soundcard.

## QA (current source)
- Pytest 28/28 PASS: test_v828_y_follow.py plus five baseline test files.
- Native PrintWindow Smaart original blue trace: accepted, score 1.000.
- Native Mag +18 px synthetic translation detected in the approximately 18–21 px band (within 4 px tolerance), PASS.
- Two-axis signed, return-to-origin, independent movement, stale-frame, low-confidence, and obsolete calibration regression PASS.
- Python syntax compile PASS.

## Acceptance boundary
- Interactive drag/gesture on actual Smaart GUI is still not established by the static/synthetic QA.
- Phase/Mag SUM uses saved .trf snapshots rather than a verified live complex H stream.
- Baseline source V8.25 and experimental V8.26 unchanged.
- Controlled restart complete: old exact-owner PIDs 2736/14732 stopped; new exact-owner PIDs 6636/14184 loaded the updated V8.27 source. Smaart PID 10372 responding, stderr empty. Real Y drag STILL HOLD.
