# RemiX Duo V8.75 — Smaart Install Discovery, Documents Trace, Auto-Start

Date: 2026-11-02 (Asia/Ho_Chi_Minh)
Single active source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Git branch: qa/remix-duo-v873-native-tf-reader
Previous commit: fd6d645
Rollback tag: checkpoint/remix-duo-v873-handoff-20261102

## Requirement

After RemiX Duo is installed, detect Smaart 8/9 already installed,
resolve each edition's Documents data directory to load saved TRF traces,
and launch RemiX Duo automatically when the user launches Smaart.
Smaart process, Generator, Sweep, Capture, sound card and DSP must never
be started or controlled by the companion.

## Implementation (same source, no new worktree)

- smaart_discovery_v875.py:
  Windows SHGetKnownFolderPath(FOLDERID_Documents) with HKCU User Shell
  Folders fallback for OneDrive/redirected Documents, no hardcoded
  C:\Users\Admin path. Detect installed edition using Windows .exe file
  version and Program Files/uninstaller records. Independently enumerate
  running genuine Smaart exe processes (edition, PID, creation time).
  Read-only list of .trf files in the edition-specific Session Data
  directory, no recursive whole-drive scan; no false Data Bar tick map
  or TF live stream claims.
- smaart_runtime_paths_v868.py:
  production trace_directory/saved_config now use Known Documents, keeping
  home= override (legacy tests) unchanged.
- overlay_v7.py:
  existing fallback Smaart Suite TRF path uses Known Documents, preserving
  full original GUI and LiveDataBar version switching.
- smaart_autostart_v875.py:
  lightweight, per-user login watcher (3s polling), starts Duo once
  per new verified Smaart process lifetime; never launches Smaart.
  Already-open Duo suppresses launching duplicates, and closing Duo
  while Smaart remains running does not trigger an unwanted relaunch.
  Windows named mutex stops duplicate watchers. On disable/uninstall
  watcher can self-exit when HKCU Run registration disappears.
- smaart_postinstall_v875.py:
  --scan to show installed editions and Documents counts.
  --enable registers only HKCU Run entry for a Pythonw dev watcher or
  packaged RemiXDuoSmaartWatcher.exe; --enable --start-now also starts
  observation immediately without signing out or rebooting.
  --status and --disable supported. Never modifies Smaart registry.
  Calls are per Windows user, do not need Administrator/UAC.
- qa_v875_real_trace_readonly.py:
  Manual read-only file parser QA: confirms existing trf_core can load
  actual saved files. Does not claim TF API/stream provenance.
- test_v875_smaart_install_autostart.py:
  deterministic unit tests covering 8/9 path isolation, redirected
  Documents routing, missing folders, shallow TRF catalog, invalid
  files, no auto-launch without Smaart, two editions -> one Duo,
  same Smaart episode single launch, wrong process/foreign Run entry,
  source vs packaged launcher and one-login watcher contract.

## Real Admin-PC read-only discovery PASS

- Smaart 8 installed:
  C:\Program Files (x86)\Smaart 8\Smaart.exe
  (edition determined by Windows executable version).
- Smaart 9 installed:
  C:\Program Files\Smaart Suite\Smaart.exe
- Known Documents resolves to C:\Users\Admin\Documents.
- Smaart 8 TRF path exists, 0 files:
  C:\Users\Admin\Documents\Smaart v8\Traces\Transfer Function\Session Data
- Smaart 9 TRF path exists, 113 .trf files:
  C:\Users\Admin\Documents\Smaart Suite\Data\Transfer Function\Session Data
- Manual parse QA against actual Smaart 9 saved files:
  0 delay-2.trf (Legacy, 463 bins): PASS
  0 delay-1.trf (Legacy, 463 bins): PASS
  111-1.trf   (MTW, 463 bins): PASS
  All cover approximately 1.465 to 23812.5 Hz. Data is OFFLINE SAVED TRF.
- Real Smaart processes detected at QA time: NONE; no Smaart opened.
- The Duo overlay process PIDs 31652 (wrapper), 29196 (child)
  were NOT terminated or relaunched.

## Autostart setup real status PASS

Commands (user-context, existing source):
  python smaart_postinstall_v875.py --scan
  python smaart_postinstall_v875.py --enable --start-now
  python smaart_postinstall_v875.py --status
  python smaart_postinstall_v875.py --disable

Admin-PC actual:
  --enable => ENABLED_AT_NEXT_USER_LOGON
  --status => {"enabled":true,"launcher_present":true,"status":"CONFIGURED"}
  --enable --start-now => ALREADY_ENABLED + WATCHER_STARTED_NOW
  background watcher pythonw wrapper PID 34236, child PID 23028.
  The two PIDs form a Python venv redirector parent/child chain, NOT two
  independent watchers. Startup single-instance mutex applies to runtime.
  --one-shot when no Smaart => DUO_NOT_LAUNCHED.
  Only RemiX Duo starts when a real Smaart edition process begins.

## Regression

103/103 tests PASS (14.72s):
  test_v875_smaart_install_autostart.py
  test_v874_duo_license.py
  test_v873_smaart_v3_v4_readonly.py
  test_v873_native_tf_reader.py
  test_v872_multi_dsp_export.py
  test_v871_fir_v8_offline.py
  test_v870_v8_native_sidebar.py
  test_v868_smaart8_api_overlay.py
  test_v868_paths.py
  test_v868_databar.py

## Release gate

PASS: genuine install discovery on Admin-PC, edition-isolated Windows
Known Documents TRF path, 113 V9 files cataloged, 3 actual TRF reads,
103 tests, HKCU Run entry and currently running no-audio watcher.
HOLD: FULL END-USER INSTALLER/EXE package (missing production-built
RemiXDuo.exe, RemiXDuoSmaartWatcher.exe and setup helper binaries).
The postinstall tool supports those binary names, but no packaged
installer or clean-machine install was executed. For customer installer,
bundle the EXEs, run a per-user postinstall hook with
  --enable --start-now
and always offer --disable on uninstall.
Exclude all RemiX Duo admin license issuer files and private keys from
customer package.
HOLD: actual Smaart-start to Duo GUI end-to-end physical QA, because
Smaart was not running/started during this safety-preserving session.
HOLD: TF streaming and Mag/Phase live parity, unchanged from V8.73.

## Important semantics

Saved .trf can be imported independently after file selection or verified
Smaart Data Bar mapping. Listing 113 files does NOT prove which Smaart
Data Bar checkboxes are ticked. Never blindly select unknown traces,
never generate fake realtime magnitude/phase data.
