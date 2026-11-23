# Implementation Plan: GitHub Release Update Notification

Source spec: `SPEC-github-release-updater.md`

## Overview

Implement a notify-only updater for the dedicated public repository
`remixaudio235-max/remixduo`. Pure shared code will fetch and validate stable
GitHub Releases, compare semantic versions and maintain a bounded cache. The
Windows overlay will start the check after startup on a dedicated worker and
show one Vietnamese update prompt without touching Smaart, audio or DSP state.

## Architecture Decisions

- Use `https://api.github.com/repos/remixaudio235-max/remixduo/releases` rather
  than `/latest`, because the client must explicitly reject drafts,
  prereleases and malformed tags before selecting the highest stable version.
- Keep HTTP, JSON, SemVer and URL validation in
  `src/remix_duo/update/github_release.py`; it imports neither Qt nor Win32 and
  is reusable on Windows/macOS.
- Use only Python standard library networking with a 3-second timeout, bounded
  response size, duplicate-key rejection and a product-specific User-Agent.
- Use the overlay's existing executor/lifecycle conventions. Completion is
  delivered to the GUI through a queued Qt signal; no modal work or network
  call runs on the GUI thread.
- V1 is notify-only. The action opens a strictly validated GitHub release page;
  it never downloads or executes an asset.
- Cache only non-sensitive status/version/timestamp data under the product app
  data path. Failures are quiet and receive a short retry backoff; a successful
  no-update result is cached for 24 hours.

## Dependency Graph

`release parser + transport + cache` → `Qt worker bridge` → `Vietnamese prompt`
→ `frozen self-check + production packaging` → `full/native verification`

## Task List

### Phase 1: Shared updater core

- [ ] Task 1: Implement and test strict GitHub release parsing, SemVer ordering,
  transport limits, repository URL validation and cache behavior.

### Checkpoint: Shared core

- [ ] Focused pure-Python updater tests pass with no live network dependency.
- [ ] Shared/contracts regression remains green.

### Phase 2: Application integration

- [ ] Task 2: Add delayed background update checking, queued result delivery,
  single-notification guard and bounded shutdown to the overlay lifecycle.
- [ ] Task 3: Add the Vietnamese styled update prompt and validated browser-open
  action, plus Qt mock tests for timing/threading/one-prompt behavior.

### Checkpoint: Integrated flow

- [ ] A mocked `v8.151.0` stable release produces exactly one notification.
- [ ] Offline/equal/older/draft/prerelease/wrong-host cases produce none.
- [ ] GUI-thread startup work attributable to updater stays below 50 ms.

### Phase 3: Release hardening

- [ ] Task 4: Add frozen updater self-check, package inclusion, source manifest
  refresh and release evidence updates.
- [ ] Task 5: Run focused, shared/contracts and full safe RC regression, then a
  read-only native startup observation without changing Smaart/audio state.

### Checkpoint: Complete

- [ ] All spec success criteria pass.
- [ ] Full safe regression has 0 FAIL.
- [ ] Production build remains fail-closed if updater configuration/self-check
  is invalid.
- [ ] Any unverified live/build/signing gate is reported as HOLD.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Network blocks GUI/startup | High | Dedicated worker, delayed launch, 3 s timeout, no waits on GUI thread. |
| Malicious/malformed GitHub response | High | Size limit, duplicate-key rejection, strict types/tag/owner/repo/host validation. |
| Wrong product release | High | Dedicated repo plus exact stable `vX.Y.Z` tags only. |
| Repeated prompts | Medium | Once-per-process guard and 24-hour cache for no-update results. |
| Worker survives Qt shutdown | Medium | Existing bounded executor shutdown pattern; no indefinite join. |
| Updater becomes an execution channel | High | Notify-only; validated browser URL; no asset download or execution. |
| API rate limiting/outage | Low | Quiet failure/backoff; updater never blocks primary app features. |

## Open Questions

- None blocking. The approved defaults are tag `v8.151.0` and reminder on the
  next later app start after `Để sau`.

## Task List Target

Tasks and checkpoints are tracked in `tasks/todo.md`.
