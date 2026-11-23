# Spec Delta: GitHub Release Update Notification — V1

Status: implemented (source); frozen artifact/native cutover pending

## Objective

Add a MeTube-style, notify-only updater to RemiX Duo. When GitHub contains a
newer stable release than the running application, the app informs the user in
Vietnamese and offers to open the official release page. Update checking must
never delay startup, block the GUI thread, touch Smaart/audio/DSP state, or run
downloaded executables.

## Current Behavior

V8.150 has no application updater. Existing GitHub references concern Smaart
API V3/V4 research and are unrelated to RemiX Duo release delivery. The
official public release repository is the dedicated, currently empty
`remixaudio235-max/remixduo` repository.

## New Behavior

- After the main window is stable, a background worker requests the configured
  GitHub Releases API endpoint over HTTPS with a short timeout.
- It accepts only a well-formed response for `remixaudio235-max/remixduo`,
  ignores draft and prerelease entries, accepts only tags matching
  `v<major>.<minor>.<patch>` and compares that semantic version with the local
  package version.
- When the newest stable remote version is greater than the local version, the
  GUI queues one non-blocking Vietnamese notification containing the new
  version and release name, with actions `Cập nhật` and `Để sau`.
- `Cập nhật` opens only the validated HTTPS `html_url` on `github.com` for the
  configured repository. It does not download, execute or install an asset.
- No notification appears when versions are equal/older, the endpoint is not
  configured, the response is invalid, rate-limited, offline or timed out.
- A successful no-update check is cached for 24 hours per released version.
  A discovered update may be reminded on the next app start after `Để sau`, but
  never more than once per process.
- Diagnostic logs contain status/error categories only; no token, license ID,
  machine code or full response payload is recorded.

## Tech Stack

- Python standard library HTTP/JSON/version parsing in shared source.
- Existing Qt worker/thread infrastructure for asynchronous execution.
- Existing RemiX Duo toast/dialog styling for the user notification.
- No new third-party runtime dependency.

## Commands

- Focused tests:
  `C:\rdv311\Scripts\python.exe -m pytest -q test_v8150_github_updater.py --tb=short`
- Shared/contracts tests:
  `C:\rdv311\Scripts\python.exe -m pytest -q tests\shared tests\contracts --tb=short`
- Full safe RC regression: enumerate root `test*.py`, excluding only
  `test_hide_other_window_v7.py`, `test_live_sync_probe.py` and
  `test_uia_scroll_restore.py`, then include `tests\shared` and
  `tests\contracts`.

## Project Structure

- `src/remix_duo/update/github_release.py`: pure validation, HTTP request,
  SemVer comparison, cache model and update result.
- `overlay_v7.py`: delayed worker launch and GUI notification wiring only.
- `test_v8150_github_updater.py`: deterministic network fixtures, security and
  version/cache behavior.
- `QA_V8150_WINDOWS_RELEASE_RC1_20261115.md`: verified release evidence.

## Code Style

```python
result = check_for_update(
    current_version=__version__,
    repository=GITHUB_RELEASE_REPOSITORY,
    transport=transport,
)
if result.available:
    update_available.emit(result)
```

Pure functions return immutable results; GUI code consumes them through queued
signals. Network and parsing code must not import Qt or any Windows API.

## Testing Strategy

- Unit: SemVer ordering including `v8.151.0`, equal/older versions, malformed
  tags, draft/prerelease filtering, wrong host/repository URL, oversized JSON,
  duplicate keys, timeout/rate limit/offline behavior and cache expiration.
- Qt mock: worker starts after the main window, never runs on the GUI thread,
  emits at most one notification, and opens only a validated release URL.
- Regression: licensing, startup, Smaart trace recognition, Auto Phase/EQ/FIR
  and shutdown suites remain at 0 FAIL.
- Native: read-only startup observation confirms no visible freeze and no
  Smaart/Generator/audio mutation. Network failure must not alter the UI.

## Boundaries

- Always: HTTPS only; strict `remixaudio235-max/remixduo`
  owner/repository/host validation; strict `v` release channel; timeout and
  response-size limit; background execution; 24-hour cache; fail silently on
  availability failures; record only non-sensitive diagnostic categories.
- Ask first: configure the production GitHub owner/repository; add private-repo
  authentication; change notification frequency; add download/install logic.
- Never: embed GitHub tokens; accept an arbitrary release URL; execute an
  asset; bypass Authenticode; downgrade; block startup; touch Smaart/audio/DSP.

## Success Criteria

1. A mocked stable `v8.151.0` release causes exactly one Vietnamese update
   notification when local version is `8.150.0`.
2. Equal/older, draft, prerelease, malformed, wrong-repository and network-error
   responses cause no notification and no crash.
3. Update checks execute outside the GUI thread, time out, and do not add more
   than 50 ms to GUI-thread startup work.
4. `Cập nhật` can open only the configured repository's HTTPS GitHub release
   page; no downloaded file is executed.
5. Focused, shared/contracts and full safe RC regressions finish with 0 FAIL.
6. Production build remains fail-closed until the frozen updater self-check
   confirms repository, product-channel configuration and parsing.

## Out of Scope (Deferred)

- Automatic download/install: deferred until Authenticode plus a separately
  signed release manifest, atomic rollback and clean-VM upgrade evidence exist.
- Mandatory/forced updates: deferred; V1 is user-controlled notification only.
- Private GitHub repositories: deferred to avoid shipping credentials.
- Delta/binary patching: deferred; unnecessary for notify-only V1.

## Open Questions

1. Approve the proposed release tag format `v8.151.0` for the dedicated repo.
2. Should `Để sau` remind on every app start or suppress that version for a
   chosen interval? The proposed default is once per later app start.
