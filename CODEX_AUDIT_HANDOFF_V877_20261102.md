# CODEX AUDIT HANDOFF — RemiX Duo V8.77
Date: 2026-11-02 | Windows Admin-PC

## Authoritative repo and active source (DO NOT create duplicate copy)
Git root: D:\REMIX_AUTO_ALIGN_V6_DEV
Active source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Primary GUI entrypoint: windows_v8_27_MAG_NATIVE_SYNC_QA\overlay_v7.py
Active branch: qa/remix-duo-v873-native-tf-reader
Verified HEAD at handoff: 459eb7edda08bd1f73e5702480cb393b2816a5ab
No Git remote configured; commits exist LOCAL on Admin-PC.
The active Pythonw command line points to this exact overlay_v7.py.
Build binaries are ignored under active-source dist/, NOT inside Git history.

## Committed V8.73–V8.77 chain (linear, NOT a main branch merge)
459eb7e — V8.77 frozen QA EXE and Inno Setup
34fc09d — V8.76 Cloudflare Worker+D1 central license (NOT deployed)
427e868 — V8.75 Smaart 8/9 installed processes + Known Documents + watcher
fd6d645 — V8.74 QA offline signed license and issuer
897716c — V8.73 Bitfocus Smaart API V3/V4 read-only adapters
c366003 — V8.73 Smaart SDK research, live TF hold
cc764f4 — V8.73 Native TF ingress fail-closed
f9cfe30 — V8.73 handoff baseline
674c3fe — active source snapshot immediately before V8.73
48f3af0 — FIR native smoothing baseline

## What is and is NOT merged
- All above commits are ancestors of 459eb7e on the current branch.
- There is NO main/master branch and NO configured remote at handoff.
- Historical side worktrees under D:\REMIX_DUO_V8*_QA or
  D:\REMIX_DOU_V8*_QA carry independent qa/* branches. Tests of Git
  ancestry prove V8.63/V8.68/V8.71/V8.72 branch HEADs are NOT ancestors
  of the active V8.77 HEAD. Their common ancestor is 48f3af0.
- A snapshot/promoted source may contain matching features, but that
  DOES NOT prove Git merges or functional parity with every side branch.
- Audit their code paths and commits using git diff or git range-diff.
  Do not use git merge -X theirs or copy an entire old folder blindly.
- Do not claim "100% complete merge" without a feature-diff matrix.

## Tracked and dirty state at handoff
- Active source directory has 428 tracked files, 346 tracked Python.
- There are pre-existing NOT COMMITTED modifications (PRESERVE):
    AGENTS.md
    ALL_SESSIONS_SOURCE_INVENTORY_20261030.md
    CURRENT_WORK_STATE.md
    FEATURE_ACCEPTANCE_MATRIX.md
    START_NEW_CHAT_HERE.txt
    VERIFY_ACTIVE_BUILD.py
    windows_v8_27_MAG_NATIVE_SYNC_QA/V833_INVALID_COMPACT_QA.png
    windows_v8_27_MAG_NATIVE_SYNC_QA/V833_VERIFIED_LAYOUT_QA.png
    windows_v8_27_MAG_NATIVE_SYNC_QA/V834_MAG_PEAK.png
    windows_v8_27_MAG_NATIVE_SYNC_QA/V834_MAG_PRE.png
    windows_v8_27_MAG_NATIVE_SYNC_QA/V834_PHASE_PEAK.png
    windows_v8_27_MAG_NATIVE_SYNC_QA/V834_PHASE_PRE.png
- Existing root untracked (PRESERVE):
    _qa_pan_printwindow_replay_20261030.py
    _qa_readonly_dual_pan_20261030.py
    _sync_v827_handoff.py
- Ignored dist/build, internal QA images, cache NOT in a clone.
- Do not perform git reset --hard, git clean -fdx, broad git add -A.

## Exact commands for Codex (PowerShell on Admin-PC)
Set-Location 'D:\REMIX_AUTO_ALIGN_V6_DEV'
git status -sb
git log -12 --graph --oneline --decorate
git worktree list --porcelain
git branch -vv
git diff --name-status
git diff --stat
git ls-files windows_v8_27_MAG_NATIVE_SYNC_QA
git diff --stat qa/remix-duo-v872-fir-multidsp-export-20261101 HEAD -- windows_v8_27_MAG_NATIVE_SYNC_QA
git diff --stat qa/remix-duo-v868-smaart8-api3-overlay-20261101 HEAD -- windows_v8_27_MAG_NATIVE_SYNC_QA
git diff --check

Important: side worktrees use DIFFERENT versioned root folders. A path-limited
comparison to windows_v8_27_MAG_NATIVE_SYNC_QA cannot alone prove feature
parity if older branches worked under another directory. Search common file
names and track actual copied implementation, modules and tests.

## Audit entrypoints
windows_v8_27_MAG_NATIVE_SYNC_QA\overlay_v7.py
windows_v8_27_MAG_NATIVE_SYNC_QA\autoeq_core.py
windows_v8_27_MAG_NATIVE_SYNC_QA\fir_native_v846.py
windows_v8_27_MAG_NATIVE_SYNC_QA\fir_dsp_export_v872.py
windows_v8_27_MAG_NATIVE_SYNC_QA\smaart_live_tf_reader_v873.py
windows_v8_27_MAG_NATIVE_SYNC_QA\smaart_api_v3_v4_readonly_v873.py
windows_v8_27_MAG_NATIVE_SYNC_QA\smaart_discovery_v875.py
windows_v8_27_MAG_NATIVE_SYNC_QA\smaart_autostart_v875.py
windows_v8_27_MAG_NATIVE_SYNC_QA\remix_duo_license_v874.py
windows_v8_27_MAG_NATIVE_SYNC_QA\remix_duo_cloud_license_v876.py
windows_v8_27_MAG_NATIVE_SYNC_QA\cloudflare_duo_license_worker_v876.mjs
windows_v8_27_MAG_NATIVE_SYNC_QA\cloudflare_duo_license_schema_v876.sql
windows_v8_27_MAG_NATIVE_SYNC_QA\remix_duo_qa_v877_installer.iss
windows_v8_27_MAG_NATIVE_SYNC_QA\build_remix_duo_qa_v877.ps1
windows_v8_27_MAG_NATIVE_SYNC_QA\QA_V877_WINDOWS_INSTALLER_20261102.md
windows_v8_27_MAG_NATIVE_SYNC_QA\QA_V876_CLOUDFLARE_CENTRAL_LICENSE_20261102.md

## Known release/QA limitations to audit
- 117/117 Python and 6/6 Node Worker tests PASS as of V8.77 build;
  this does NOT establish all-feature or Smaart live TF parity.
- V8.73 Native Smaart live TF Mag/Phase SDK stream remains HOLD.
- V8.76 Cloudflare D1 Worker, secrets and domain are NOT deployed.
  CLOUD_WORKER_URL is intentionally blank, commercial frozen EXE
  fails closed until backend configured.
- V8.77 unsigned Inno Setup QA installer exists LOCAL only:
  D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA\
  dist\installer\RemiXDuo_QA_Setup_V8.77.exe
  SHA256: 582E0714C32B03FF3DC74D8E72BA8EF93ED931C4292CD1938E1EA59CB01513A7
  Ignored by Git. There is no clean-Windows-VM install acceptance.
- Commercial license issuer PRIVATE KEY and Cloudflare admin token
  live only in protected Windows profile, never in repository.
- QA runtime hook allows the existing V8.74 QA license for QA EXE.
  It must NEVER be included in commercial distribution.
- Current active source overlay_v7.py may already be running
  via 2 Pythonw wrapper/child PIDs; DO NOT stop it without permission.
- No Generator, Sweep, Capture, sound card or Smaart side effects
  while auditing. Use offline tests and static source diff first.
- Audit installer registration and uninstall, singleton lock before
  packaged --package-selfcheck, signer provenance and D1 activation
  concurrency, Python import boundaries, client API auth, Data Bar
  trace identity, overlay Mag/Phase parity. Flag any unsafe behavior.
- Owner wants ONE active source folder. Keep commits/checkpoints in
  current repo. Preserve all pre-existing dirty user files.

## Codex deliverables
1. Exact list of active modules and source ancestry.
2. Feature-by-feature comparison against side branches V8.63–V8.72
   and confirmation of which changes are PRESENT/MISSING/CONFLICTING.
3. Security audit of V8.74–V8.76 license and Cloudflare workflow.
4. Runtime/GUI import verification and Windows installer audit.
5. Regression results, missing QA and release blockers with evidence.
6. Propose a SAFE incremental merge plan; never blanket overwrite.
