"""Notify-only GitHub release checker for RemiX Duo."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


REPOSITORY = "remixaudio235-max/remixduo"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
RELEASE_ROOT = f"https://github.com/{REPOSITORY}/releases/tag/"
TIMEOUT_SECONDS = 3.0
MAX_RESPONSE_BYTES = 256_000
CACHE_TTL_SECONDS = 24 * 60 * 60
_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)\Z")


@dataclass(frozen=True)
class ReleaseResult:
    available: bool
    status: str
    version: tuple[int, int, int] = (0, 0, 0)
    title: str = ""
    url: str = ""


def _semver(value: str, *, tag: bool = False) -> tuple[int, int, int] | None:
    match = _TAG.fullmatch(value) if tag else re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return None
    parts = tuple(int(item) for item in match.groups())
    return parts if all(item <= 999_999 for item in parts) else None


def valid_release_url(url: str, tag: str) -> bool:
    if not isinstance(url, str) or not _semver(tag, tag=True):
        return False
    parsed = urllib.parse.urlsplit(url)
    return bool(
        parsed.scheme == "https" and parsed.hostname == "github.com" and
        parsed.username is None and parsed.password is None and
        parsed.port is None and not parsed.query and not parsed.fragment and
        parsed.path == f"/{REPOSITORY}/releases/tag/{tag}"
    )


def configured() -> bool:
    """Self-check immutable repository/channel configuration without network."""
    expected = "https://api.github.com/repos/remixaudio235-max/remixduo/releases"
    return bool(
        REPOSITORY == "remixaudio235-max/remixduo" and API_URL == expected and
        valid_release_url(RELEASE_ROOT + "v1.0.0", "v1.0.0")
    )


def parse_releases(payload, current_version: str) -> ReleaseResult:
    current = _semver(current_version)
    if current is None or not isinstance(payload, list):
        return ReleaseResult(False, "INVALID_RESPONSE")
    candidates = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        tag = item.get("tag_name")
        url = item.get("html_url")
        version = _semver(tag, tag=True) if isinstance(tag, str) else None
        if (version is None or type(item.get("draft")) is not bool or
                type(item.get("prerelease")) is not bool or item["draft"] or
                item["prerelease"] or not valid_release_url(url, tag)):
            continue
        title = item.get("name")
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            title = tag
        candidates.append((version, title.strip(), url))
    if not candidates or max(candidates)[0] <= current:
        return ReleaseResult(False, "UP_TO_DATE")
    version, title, url = max(candidates)
    return ReleaseResult(True, "UPDATE_AVAILABLE", version, title, url)


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_KEY")
        result[key] = value
    return result


def _cache_is_fresh(path: Path, version: str, now: int) -> bool:
    try:
        data = json.loads(path.read_text("utf-8"))
        return bool(
            isinstance(data, dict) and data.get("version") == version and
            type(data.get("checked_at")) is int and
            0 <= now - data["checked_at"] < CACHE_TTL_SECONDS
        )
    except (OSError, ValueError, TypeError, UnicodeError):
        return False


def _write_cache(path: Path, version: str, now: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".update-", delete=False) as out:
            temporary = Path(out.name)
            json.dump({"version": version, "checked_at": now}, out,
                      separators=(",", ":"))
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def check_for_update(current_version: str, *, transport=None,
                     cache_path: Path | None = None,
                     now: int | None = None) -> ReleaseResult:
    current_time = int(time.time()) if now is None else now
    cache = Path(cache_path) if cache_path is not None else None
    if cache is not None and _cache_is_fresh(cache, current_version, current_time):
        return ReleaseResult(False, "CACHED_UP_TO_DATE")
    request = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"RemiXDuo/{current_version} UpdateCheck",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    perform = urllib.request.urlopen if transport is None else transport
    try:
        with perform(request, timeout=TIMEOUT_SECONDS) as response:
            if getattr(response, "status", 200) != 200:
                return ReleaseResult(False, "UNAVAILABLE")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return ReleaseResult(False, "INVALID_RESPONSE")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicates)
        result = parse_releases(payload, current_version)
        if cache is not None and result.status == "UP_TO_DATE":
            _write_cache(cache, current_version, current_time)
        return result
    except (urllib.error.URLError, TimeoutError, OSError):
        return ReleaseResult(False, "UNAVAILABLE")
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return ReleaseResult(False, "INVALID_RESPONSE")
