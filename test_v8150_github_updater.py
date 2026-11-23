import io
import json
from pathlib import Path
import threading
import time

import pytest

from remix_duo.update.github_release import (
    API_URL, CACHE_TTL_SECONDS, ReleaseResult, check_for_update,
    configured, parse_releases, valid_release_url,
)


def release(tag, *, draft=False, prerelease=False, url=None, name=None):
    return {
        "tag_name": tag,
        "name": name or tag,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": url or (
            "https://github.com/remixaudio235-max/remixduo/releases/tag/" + tag
        ),
    }


def test_selects_highest_newer_stable_semver_only():
    result = parse_releases([
        release("v8.151.0"),
        release("v8.153.0", prerelease=True),
        release("v8.152.1"),
        release("duo-v99.0.0"),
        release("v8.200.0", draft=True),
    ], "8.150.0")
    assert result == ReleaseResult(
        True, "UPDATE_AVAILABLE", (8, 152, 1), "v8.152.1",
        "https://github.com/remixaudio235-max/remixduo/releases/tag/v8.152.1",
    )


def test_production_repository_configuration_is_valid():
    assert configured()


@pytest.mark.parametrize("tag", ["v8.150.0", "v8.149.9", "8.151.0", "v8.151", "v8.1.2.3"])
def test_equal_older_or_malformed_tags_do_not_notify(tag):
    result = parse_releases([release(tag)], "8.150.0")
    assert not result.available


@pytest.mark.parametrize("url", [
    "http://github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0",
    "https://evil.example/remixaudio235-max/remixduo/releases/tag/v8.151.0",
    "https://github.com/remixaudio235-max/tool/releases/tag/v8.151.0",
    "https://user@github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0",
    "https://github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0?x=1",
])
def test_release_url_is_locked_to_official_repository(url):
    assert not valid_release_url(url, "v8.151.0")
    assert not parse_releases([release("v8.151.0", url=url)], "8.150.0").available


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size):
        return self.payload[:size]


def test_network_check_uses_bounded_github_api_request(tmp_path):
    observed = {}

    def transport(request, timeout):
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        observed["accept"] = request.headers["Accept"]
        return Response(json.dumps([release("v8.151.0")]).encode())

    result = check_for_update("8.150.0", transport=transport,
                              cache_path=tmp_path/"cache.json", now=1000)
    assert result.available
    assert observed == {
        "url": API_URL, "timeout": 3.0,
        "accept": "application/vnd.github+json",
    }


def test_oversized_or_duplicate_json_fails_quietly(tmp_path):
    oversized = lambda *_args, **_kwargs: Response(b"[" + b" " * 300_000)
    duplicate = lambda *_args, **_kwargs: Response(
        b'[{"tag_name":"v8.151.0","tag_name":"v9.0.0"}]')
    assert check_for_update("8.150.0", transport=oversized,
                            cache_path=tmp_path/"a.json").status == "INVALID_RESPONSE"
    assert check_for_update("8.150.0", transport=duplicate,
                            cache_path=tmp_path/"b.json").status == "INVALID_RESPONSE"


def test_network_failure_is_quiet_and_does_not_write_cache(tmp_path):
    cache = tmp_path/"cache.json"
    def offline(*_args, **_kwargs):
        raise TimeoutError("offline")
    result = check_for_update("8.150.0", transport=offline,
                              cache_path=cache, now=1000)
    assert result.status == "UNAVAILABLE" and not result.available
    assert not cache.exists()


def test_no_update_cache_skips_network_for_24_hours(tmp_path):
    cache = tmp_path/"cache.json"
    calls = []
    def transport(*_args, **_kwargs):
        calls.append(1)
        return Response(json.dumps([release("v8.150.0")]).encode())

    first = check_for_update("8.150.0", transport=transport,
                             cache_path=cache, now=1000)
    second = check_for_update("8.150.0", transport=transport,
                              cache_path=cache, now=1000+CACHE_TTL_SECONDS-1)
    third = check_for_update("8.150.0", transport=transport,
                             cache_path=cache, now=1000+CACHE_TTL_SECONDS+1)
    assert [first.status, second.status, third.status] == [
        "UP_TO_DATE", "CACHED_UP_TO_DATE", "UP_TO_DATE"]
    assert len(calls) == 2


def test_cache_for_another_app_version_is_ignored(tmp_path):
    cache = tmp_path/"cache.json"
    cache.write_text(json.dumps({"checked_at": 1000, "version": "8.149.0"}))
    calls = []
    def transport(*_args, **_kwargs):
        calls.append(1)
        return Response(b"[]")
    check_for_update("8.150.0", transport=transport, cache_path=cache, now=1001)
    assert calls == [1]


def test_overlay_check_runs_off_gui_thread_and_delivers_once(monkeypatch, tmp_path):
    from PyQt6.QtWidgets import QApplication
    import overlay_v7 as gui

    app = QApplication.instance() or QApplication([])
    gui_thread = threading.get_ident()
    worker_threads = []
    result = ReleaseResult(True, "UPDATE_AVAILABLE", (8, 151, 0),
                           "RemiX Duo 8.151",
                           "https://github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0")

    def fake_check(*_args, **_kwargs):
        worker_threads.append(threading.get_ident())
        return result

    monkeypatch.setattr(gui, "check_for_update", fake_check)
    engine = gui.App(demo=True)
    engine.timer.stop(); engine.drag_timer.stop(); engine._update_timer.stop()
    delivered = []
    monkeypatch.setattr(engine, "_show_update_prompt", delivered.append)
    engine._start_update_check()
    deadline = time.monotonic() + 2
    while not delivered and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    engine._on_update_ready(result)
    assert worker_threads and worker_threads[0] != gui_thread
    assert delivered == [result]
    engine._align_closed = True
    engine.close()


def test_overlay_opens_only_validated_release_url(monkeypatch):
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import QApplication
    import overlay_v7 as gui

    app = QApplication.instance() or QApplication([])
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl",
                        lambda url: opened.append(url.toString()) or True)
    engine = gui.App(demo=True)
    engine.timer.stop(); engine.drag_timer.stop(); engine._update_timer.stop()
    engine._open_update_url(ReleaseResult(
        True, "UPDATE_AVAILABLE", (8, 151, 0), "v8.151.0",
        "https://github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0"))
    engine._open_update_url(ReleaseResult(
        True, "UPDATE_AVAILABLE", (9, 0, 0), "bad",
        "https://evil.example/releases/tag/v9.0.0"))
    assert opened == [
        "https://github.com/remixaudio235-max/remixduo/releases/tag/v8.151.0"]
    engine._align_closed = True
    engine.close()
