# V8.82 read-only native viewport tick verification

Date 2026-11-02. Source windows_v8_27_MAG_NATIVE_SYNC_QA.
Smaart v9 PID 30288 HWND 986302, CWD C:/Users/Admin/Desktop.
Installed Duo PID 25288 CWD C:/Users/Admin/AppData/Local/Programs/RemiX Duo QA.
Installed EXE matches current dist SHA256
B4779926BA0A02AD8D2656CEF0D261F8A4879680447806D087ED8837E9AEF2B3.
Build guard reported NO_ACTIVE_OVERLAY because it inspects source pythonw
overlays; native window enumeration confirms the installed Duo windows exist.

Smaart was initially minimized. Restored existing window through Computer Use;
capture helper then timed out twice. Recovered evidence through the existing
source's read-only PrintWindow/UIA functions. No observer instance, full_scan,
scroll, tick, capture command, generator or soundcard operation was invoked.

## Results

- UIA rows = stored TRF paths = 113. Count equality is not independent proof
  of every row-to-filename mapping; visible image confirms the two named rows.
- First 20 samples: 37 visible rows, zero unknown icons, same two visible ticks
  20/20: `0 delay-2.trf`, `4,8 ms delay-1.trf`.
- First run median read 140.38ms; max 194.02ms.
- Extended run 100 samples: same pair 96 samples; empty visible tick set 4.
  Final sample had 25 visible rows (viewport changed during the overall run).
  Median read 75.455ms; max 239.31ms. No alternative pair observed.
- No contemporaneous screenshot of each empty sample was retained, therefore
  those four samples cannot be classified as detector error or true UI state.
- Global selection verified 0/100: offscreen states were deliberately not
  inferred from cached ticks. These results are not a 96% accuracy score.
- Duo's live accessibility tree identifies its active tool as Auto EQ.
  Current two visible ticks are appropriate for Phase, not EQ/FIR (one trace).
  This read-only probe does not inspect Duo's internal committed observer state.

Screenshot: V882_NATIVE_TICK_READONLY.png (native Smaart window, not desktop).
Harness: _qa_native_tick_readonly_v882.py [sample_count].

## Acceptance scope

READ-ONLY NATIVE visible pair observation: PASS for first stable 20 samples;
extended run records 96 pair/4 empty with viewport changes, not full acceptance.
Trace switch latency, stable 3/3 commit, 0/1/2/3+ tick transitions, offscreen
tick cache correctness, scrolling and actual Phase/EQ/FIR consumption: HOLD.
Require controlled transitions and frame-by-frame ground truth, restoring the
original pair afterwards. Do not claim full live GUI PASS from this measurement.

## Follow-up: window motion and anchor coherence

Installed geometry-timer build: EXE SHA256
D440316C4232F6AA61543B17F3E7F52F213208BB6D13C12BD24D1574F54863D9.
PID30256, CWD `C:\Users\Admin\AppData\Local\Programs\RemiX Duo QA`.
Smaart PID30288/HWND986302 unchanged. Activating Smaart restored the hidden
toolbar/panel; no startup hang was found (Python stack idle in app.exec).

Read-only native position sampling: 10047 samples over 59.99 seconds, 39 host
rectangle changes and two host sizes. The user moved windows. This was NOT
an automated controlled gesture benchmark. A final motion ended at 10000ms,
but toolbar placement corrected at 10628ms; a maximize transition at 49235ms
had a later 3px anchor correction at 50141ms. Do not describe the 16ms requested
timer interval as achieved latency. Capture evidence: local ignored
`V882_FOLLOW_NATIVE_SAMPLES.json`.
Subsequent inventory also found user-opened Smaart8 PID29480/HWND1248294
(minimized when inspected). Since the sample stored only the V9 host, periods
where Duo followed V8 must be excluded. The whole 60s run cannot produce a
valid aggregate lag percentile across targets; retain it as diagnostic evidence.

Found non-atomic UIA anchor acquisition: host rectangle was captured before
walking controls, without rechecking it afterwards. Motion during that walk
could bind a new control position to an old host origin. Fix rejects the
entire sample when the end host rectangle differs (or host is minimized or
destroyed); ToolHub retains and projects its previous coherent anchors.
Parameterized stable/moving UIA mock tests added in test_v882_fast_follow.py.
51 focused regression tests PASS. Historical test_v831_brand_toolbar.py FAILS
at obsolete `RemiX Dou` text assertion (current product name `RemiX Duo`);
not changed as part of geometry repair. Full historical suite is not PASS.

Computer Use activation/accessibility worked, but screenshot capture timed out
twice and element click failed `coordinate input geometry is unavailable`.
No generator, trace tick, DSP or audio route was operated. Post-anchor-fix
live motion acceptance remains HOLD until the rebuilt EXE is installed/measured.
