# GitHub Release Updater Tasks

Source plan: `tasks/plan.md`

## Task 1: Shared release-check core

**Description:** Add the platform-neutral release client, strict parser, SemVer
comparison, validated release URL and bounded cache model.

**Acceptance criteria:**
- [x] Only stable `vX.Y.Z` releases from `remixaudio235-max/remixduo` qualify.
- [x] Invalid, oversized, duplicate-key, wrong-host and network-error responses fail quietly.
- [x] Equal/older versions do not report an update; the greatest newer stable version does.

**Verification:**
- [x] `C:\rdv311\Scripts\python.exe -m pytest -q test_v8150_github_updater.py --tb=short`
- [x] `C:\rdv311\Scripts\python.exe -m pytest -q tests\shared tests\contracts --tb=short`

**Dependencies:** None

**Files likely touched:**
- `src/remix_duo/update/__init__.py`
- `src/remix_duo/update/github_release.py`
- `test_v8150_github_updater.py`

**Estimated scope:** Medium

## Checkpoint 1: Shared core

- [x] Focused and shared/contracts tests pass.
- [x] No Qt, Win32, Smaart or audio imports enter the updater core.

## Task 2: Background lifecycle integration

**Description:** Start one delayed check on an updater-specific executor, return
results via queued Qt signal and shut down with a finite timeout.

**Acceptance criteria:**
- [x] No network work executes on the GUI thread.
- [x] At most one check and one notification occur per process.
- [x] Close never waits indefinitely for updater I/O.

**Verification:**
- [x] Focused Qt mock verifies worker thread, delayed startup and bounded close.
- [x] Measured GUI-thread scheduling work is below 50 ms.

**Dependencies:** Task 1

**Files likely touched:**
- `overlay_v7.py`
- `test_v8150_github_updater.py`

**Estimated scope:** Small

## Task 3: Vietnamese notification flow

**Description:** Present the new version and actions `Cập nhật` / `Để sau`, then
open only the validated official GitHub release URL when requested.

**Acceptance criteria:**
- [x] A mocked newer stable version displays exactly one readable prompt.
- [x] `Cập nhật` opens only an HTTPS URL under the dedicated repository.
- [x] `Để sau` performs no browser/download/install action.

**Verification:**
- [x] Qt mock tests both actions and rejects wrong-host/repository URLs.
- [x] Existing toast/layout tests remain green.

**Dependencies:** Tasks 1-2

**Files likely touched:**
- `overlay_v7.py`
- `src/remix_duo/ui/widgets.py`
- `test_v8150_github_updater.py`

**Estimated scope:** Medium

## Checkpoint 2: Integrated flow

- [x] Mocked `v8.151.0` end-to-end flow passes.
- [x] Offline/equal/older/draft/prerelease cases are silent.
- [x] No Smaart/audio/DSP API is called by updater tests.

## Task 4: Frozen/package release gate

**Description:** Add frozen updater self-check, ensure packaging collects the
shared module and require configuration/parsing success before production build.

**Acceptance criteria:**
- [x] Frozen self-check succeeds only for the official repo and valid parser.
- [x] Production build fails before packaging if updater configuration is invalid.
- [x] QA license override remains absent from production hook.

**Verification:**
- [x] Production release tests pass.
- [x] Source SHA256 manifest is regenerated after final source changes.

**Dependencies:** Tasks 1-3

**Files likely touched:**
- `production_runtime_hook_v8150.py`
- `build_remix_duo_production_v8150.ps1`
- `test_v8150_production_release.py`
- `RELEASE_SOURCE_MANIFEST.sha256`

**Estimated scope:** Medium

## Task 5: Regression and native read-only evidence

**Description:** Run all relevant automated gates and observe startup behavior
without restarting/stopping Smaart or changing Generator/audio/DSP state.

**Acceptance criteria:**
- [x] Focused, shared/contracts and full safe RC collections have 0 FAIL.
- [x] Offscreen read-only startup benchmark shows no blocking or repeated prompt; native cutover remains HOLD.
- [x] Remaining build/live/clean-VM/signing limits are explicitly HOLD.

**Verification:**
- [x] Full safe RC pytest command completes at 0 FAIL.
- [x] Release report and root context notes contain exact evidence.

**Dependencies:** Tasks 1-4

**Files likely touched:**
- `QA_V8150_WINDOWS_RELEASE_RC1_20261115.md`
- `D:\REMIX_AUTO_ALIGN_V6_DEV\CURRENT_WORK_STATE.md`
- `D:\REMIX_AUTO_ALIGN_V6_DEV\FEATURE_ACCEPTANCE_MATRIX.md`

**Estimated scope:** Small

## Checkpoint 3: Complete

- [x] All spec success criteria met.
- [x] Full safe regression is 0 FAIL.
- [x] Release handoff reports exact source, runtime PID/CWD, tests and HOLD gates.

