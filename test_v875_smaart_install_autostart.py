"""V8.75 deterministic installed-Smaart/Documents/autostart QA (no audio/GUI)."""
from pathlib import Path
import sys
import pytest

import smaart_discovery_v875 as discovery
import smaart_postinstall_v875 as post
import smaart_autostart_v875 as watch
import smaart_runtime_paths_v868 as old


def test_version_paths_keep_isolation_and_unknown_fail_closed(tmp_path):
    d=tmp_path/"My Documents"
    v8=discovery.trace_folder(8,d)
    v9=discovery.trace_folder(9,d)
    assert "Smaart v8" in str(v8)
    assert "Smaart Suite" in str(v9)
    assert v8!=v9
    assert v8.is_relative_to(d) and v9.is_relative_to(d)
    assert discovery.trace_folder(0,d) is None
    assert discovery.config_file(0,d) is None
    assert "SmaartConfig.xml" in str(discovery.config_file(8,d))


def test_redirected_windows_documents_used_by_legacy_live_observer(monkeypatch,tmp_path):
    redirected=tmp_path/"Redirected" / "Documents"
    monkeypatch.setattr(discovery,"known_documents", lambda: redirected)
    assert old.trace_directory(8) == discovery.trace_folder(8,redirected)
    assert old.trace_directory(9) == discovery.trace_folder(9,redirected)
    assert old.saved_config(9) == discovery.config_file(9,redirected)
    assert old.trace_directory(7) is None
    # The explicit home argument keeps V8.68 unit-test compatibility:
    assert old.trace_directory(8,home=Path("D:/FakeUser")) == (
        Path("D:/FakeUser/Documents")/discovery.TRF_SUFFIX[8])


def test_missing_directory_or_invalid_version_is_not_a_trace_session(tmp_path):
    assert not discovery.scan_traces(8,documents=tmp_path).available
    assert not discovery.scan_traces(9,documents=tmp_path).available
    assert not discovery.scan_traces(7,documents=tmp_path).available


def test_shallow_sanitized_trace_listing_and_limit(tmp_path):
    folder=discovery.trace_folder(9,tmp_path)
    folder.mkdir(parents=True)
    for name in ("A.trf","b.TRF","C.trf", "not_a_trace.txt"):
        (folder/name).write_bytes(b"DATA")
    (folder/"subfolder").mkdir()
    (folder/"subfolder"/"deep.trf").write_bytes(b"DATA")
    inv=discovery.scan_traces(9,documents=tmp_path,max_names=2)
    assert inv.available and inv.count==3
    assert len(inv.filenames)==2 and inv.truncated
    assert all(x.lower().endswith(".trf") for x in inv.filenames)
    # Catalog is metadata: invalid .TRF is never declared as valid TF data.
    from trf_core import read_trf, TraceError
    with pytest.raises(TraceError):
        read_trf(folder/"A.trf")
    assert discovery.scan_traces(8,documents=tmp_path).count == 0


def test_scan_max_rejects_unbounded_folders(tmp_path):
    with pytest.raises(ValueError,match="INVALID_MAX_NAMES"):
        discovery.scan_traces(9,documents=tmp_path,max_names=10001)


def test_one_launch_per_smaart_lifetime_and_no_close_relaunch():
    seen=[]
    running=[(9,100,1.0)]
    watcher=watch.EpisodeWatcher(
        running=lambda: tuple(running),
        is_duo_running=lambda: False,
        launch=lambda: seen.append("start") or True
    )
    assert watcher.poll() and watcher.launches==1
    assert not watcher.poll()  # user closed Duo, same Smaart
    running[:]=[(9,100,2.0)]  # OS reused PID with new process lifetime
    assert watcher.poll() and watcher.launches==2
    running[:]=[]
    assert not watcher.poll()
    running[:]=[(8,500,1.0)]
    assert watcher.poll() and watcher.launches==3
    assert seen == ["start"]*3


def test_already_open_duo_does_not_get_relaunched():
    calls=[]
    running=[(8,200,5.0)]
    w=watch.EpisodeWatcher(
        running=lambda: tuple(running),
        is_duo_running=lambda: True,
        launch=lambda: calls.append(1) or True
    )
    assert not w.poll()
    assert not w.poll()
    assert calls == []


def test_two_smaarts_one_duo_and_retry_not_spammed():
    episodes=[(8,111,2.0),(9,222,3.0)]
    count=[]
    w=watch.EpisodeWatcher(running=lambda: tuple(episodes),
                           is_duo_running=lambda: False,
                           launch=lambda: count.append(1) or False)
    assert not w.poll()
    assert not w.poll()
    assert count == [1]  # No repeated error/restart loop


def test_launch_expects_only_own_exe_or_own_overlay(tmp_path):
    assert watch.launch_command(install=tmp_path) is None
    (tmp_path/"Smaart.exe").write_bytes(b"EXE")  # never start target Smaart
    assert watch.launch_command(install=tmp_path) is None
    (tmp_path/"overlay_v7.py").write_text("pass")
    py=tmp_path/"python.exe"
    py.touch()
    result=watch.launch_command(install=tmp_path,interpreter=py)
    assert result==[str(py),str(tmp_path/"overlay_v7.py")]
    (tmp_path/"pythonw.exe").touch()
    result=watch.launch_command(install=tmp_path,interpreter=py)
    assert result==[str(tmp_path/"pythonw.exe"),str(tmp_path/"overlay_v7.py")]
    (tmp_path/"RemiXDuo.exe").touch()
    assert watch.launch_command(install=tmp_path) == [str(tmp_path/"RemiXDuo.exe")]


def test_postinstall_only_uses_known_watcher_and_safe_quotes(tmp_path):
    path=tmp_path/"RemiX Duo"
    path.mkdir()
    python=tmp_path/"Python 3.11"/"python.exe"
    python.parent.mkdir()
    python.touch()
    (python.parent/"pythonw.exe").touch()
    (path/"smaart_autostart_v875.py").touch()
    cmd=post.watcher_command(path,interpreter=python)
    assert '"'+str(python.parent/"pythonw.exe")+'"' in cmd
    assert '"'+str(path/"smaart_autostart_v875.py")+'"' in cmd
    assert cmd.endswith('--watch')
    (path/"RemiXDuoSmaartWatcher.exe").touch()
    assert "RemiXDuoSmaartWatcher.exe" in post.watcher_command(path,interpreter=python)


def test_startup_registration_idempotent_and_foreign_safe(monkeypatch):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setattr(post,"watcher_command",lambda:"EXPECTED_WATCHER --watch")
    monkeypatch.setattr(post,"registered_command",lambda:"foreign")
    assert post.configure_autostart(True)=="OTHER_INSTALL_OWNS_STARTUP_ENTRY"
    assert post.configure_autostart(False)=="OTHER_INSTALL_OWNS_STARTUP_ENTRY"
    monkeypatch.setattr(post,"registered_command",lambda:"EXPECTED_WATCHER --watch")
    assert post.configure_autostart(True)=="ALREADY_ENABLED"
    monkeypatch.setattr(post,"registered_command",lambda:None)
    assert post.configure_autostart(False)=="ALREADY_DISABLED"


def test_no_running_smaart_no_launch():
    attempts=[]
    w=watch.EpisodeWatcher(running=lambda: (),
                           is_duo_running=lambda:False,
                           launch=lambda: attempts.append(1) or True)
    assert not w.poll() and attempts==[]
