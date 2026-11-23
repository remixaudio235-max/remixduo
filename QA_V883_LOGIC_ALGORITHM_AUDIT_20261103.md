# RemiX Duo logic/algorithm audit — 2026-11-03

Exact source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA`.
Repository HEAD57039a4, branch qa/remix-duo-v873-native-tf-reader, dirty tree
preserved. Audit scope: FIR design/export gates, AutoPhase matching/solver,
Suite9 saved Fs, observer freshness, shared GUI scheduling/layout. This is
not a claim of exhaustive audit of all modules or a live/hardware acceptance.

## Findings requiring fixes

### P1 — Flat-input FIR MAG introduces a large unintended HF cut

`signal_tools_core_v813.py:174–177` centers an even-length truncation on an
integer sample, then averages it with its reverse. For flat input, the
zero-phase impulse has one nonzero center coefficient; averaging produces
two adjacent half-amplitude taps. Its magnitude acquires cos(pi*f/Fs),
instead of a transparent delayed response. Kaiser window changes the scalar
slightly, not the HF loss. Reproduced with 512,1024,4096 taps at48kHz:
10kHz -2.01dB; 16kHz -6.02dB; 20kHz -11.74dB, although target_db=0 everywhere.
The GUI finish gate (signal_tools_gui_v813.py:1099 onwards) checks symmetry,
finite values and maximum boost, so this unwanted attenuation is not rejected.
It can reach approved exported coefficients, not just the graph.

Fix: design the desired even-length linear-phase response around the correct
half-sample delay, rather than imposing symmetry on a miscentered impulse;
validate actual vs intended response over the working band and neutral regions.
Regression: flat input should remain within an explicit small tolerance through
the supported work band; test multiple taps/Fs and out-of-band unity separately.

### P1 — Suite9 Fs resolver ignores redirected Documents

`smaart_fs_sync_v841.py:27` calls saved_config(8) only for version8; Suite9
uses hardcoded home/Documents CONFIG despite V8.75 known_documents support.
Mocked redirected Suite9 config=96k and old hardcoded config=48k -> default
read returns48k; explicit redirected path correctly returns96k. If old file
is absent, valid Suite9 sessions instead get HOLD. Wrong Fs changes PEQ/FIR
design and export sample-rate metadata.

Fix: resolve config through saved_config for the exact verified target edition,
reject unknown/ambiguous editions, carry source path/edition in the provenance.
Test stale old config plus valid redirected config, not only the path helper.

### P1 — Cached offscreen tick can be refreshed as newly verified

`live_sync_v7.py:239–250` merges only visible rows into cached states, then
observe_single(now) sets single_verified_at=now for the whole cached selection
(`live_sync_v7.py:122`). Three scans of a different row can reauthorize an
unseen selected row after its old evidence expired. Repro: cached row0=on,
row1=off, full scan1000s old; three mocked valid viewport scans containing
only row1=off yield current_single()!=None for row0.

This does not prove a particular user's screenshot selected a wrong trace.
It proves the freshness contract can authorize stale offscreen state, e.g.
after a rapid tick/scroll transition missed between captures. EQ/FIR consume
this token; pair count likewise depends on cached offscreen states.

Fix: retain per-row evidence timestamps/epochs, require fresh selected-row
evidence and a defensible current global count. An old complete cache is not
a new complete observation. Fail closed with a specific reason until reverified;
do not introduce automatic intrusive scrolling during live operation.

### P2 — AutoPhase solver blocks GUI and prevents timely stale-state handling

`overlay_v7.py:1413` calls auto_align synchronously inside the button slot.
Synthetic benchmark with maxdelay180ms, LF20/HF20000:1200bins0.687s;
8000bins7.946s. This is measured once on this host, not a universal limit.
Qt timers, docking, toasts and queued tick updates cannot run during the slot.
The controller generation check after it is insufficient when the update that
would advance that generation is itself queued on the blocked GUI thread.

Fix: background solver with immutable trace/config snapshot, bounded workload,
cancel/supersede older requests and revalidate current selection on GUI completion.
Regression: GUI heartbeat continues during a deliberately slow solve and stale
result cannot publish after tick/source/ROI changes.

### P2 — Complex linear interpolation changes pure-delay magnitude

`trf_core.py:87` interpolates real/imag Cartesian values between different
frequency grids. The current ratio<1.25 guard does not constrain phase rotation.
Unit-amplitude20ms pure-delay samples at100/110Hz interpolate to0.809 at105Hz
(-1.84085dB), although the actual delayed TF amplitude is1. SUM and solver
therefore receive a fabricated magnitude change for such mismatched grids.
Same-grid exact matches do not hit this defect.

Fix: phase/delay-aware resampling with reliable unwrapping and separate magnitude
interpolation; reject under-resolved/ambiguous segments rather than inventing a
trustworthy bin. Test known pure delay on dissimilar grids and near wraps/nulls.

### P2 — FIR result details overlap DSP controls

`remix_layout_v856.py:205` forces570px; newer DSP widgets are appended at
`signal_tools_gui_v813.py:1051–1052`. Qt offscreen current layout minimum594px,
sizeHint676px. Details y463–549 intersects selector y500–529 and export
y534–564. Both QRect intersections reproduced TRUE.

Fix: let page content meet its layout minimum and scroll within the dock;
keep calculate/export controls reachable. Regression must check rectangles and
scroll reachability with DSP controls, not merely assert height==570.

## Evidence and validation

- `qa_v883_logic_repros.py`: five deterministic offline probes, five defects
  confirmed; exit1 intentionally means defects remain, not an execution crash.
- `QA_V883_LOGIC_REPRO_OUTPUT_20261103.txt`: captured output.
- Existing focused tests:44 PASS in4.18s, covering Fs fixtures, FIR modes/range,
  DSP export, tick concurrency, fast-follow, AutoEQ rescue/bypass.
- These passes do not cover the newly identified invariants. Historical tests
  asserting fixed570px/symmetric FIR alone cannot establish correct behavior.
- Source/config temp fixtures only, mocked native capture and offscreen Qt.
  No Smaart/audio/DSP/activation GUI operations. No product code changed/fixed.
- Guard HOLD:NO_ACTIVE_OVERLAY,NO_SMAART_WINDOW. Only pythonw watcher chain
  PIDs8012/9056 observed, not a running overlay.
- Suite9 missing MagEQ and earlier Windows AppHang remain live repro HOLD;
  this audit does not attribute either symptom to one unmeasured cause.

Suggested order: FIR magnitude math; tick freshness; exact-target Fs; async
AutoPhase; interpolation; FIR layout. Preserve current dirty worktree, license
and existing V8.25 rollback. Run synthetic/Qt regressions before packaging or
any controlled cutover. No merge or production restart performed.
