"""V8.91 Windows Smaart process identity via Win32; no psutil.exe C extension."""
from types import SimpleNamespace
import pytest
import win_databar_v7 as watcher


@pytest.mark.parametrize("pid", [0,-1,True,"999"])
def test_invalid_pids_fail_closed(pid):
    assert watcher._process_binary_name(pid)==""


def test_locate_requires_smaart_executable_not_only_window_title(monkeypatch):
    monkeypatch.setattr(watcher.win32gui,"EnumWindows",lambda cb,extra:cb(55,extra))
    monkeypatch.setattr(watcher.win32gui,"IsWindowVisible",lambda hwnd:True)
    monkeypatch.setattr(watcher.win32gui,"GetWindowText",lambda hwnd:"Smaart Suite")
    monkeypatch.setattr(watcher.win32gui,"GetWindowRect",lambda hwnd:(10,20,1920,1060))
    monkeypatch.setattr(watcher.win32gui,"GetForegroundWindow",lambda:55)
    monkeypatch.setattr(watcher.win32process,"GetWindowThreadProcessId",lambda hwnd:(1,4321))
    monkeypatch.setattr(watcher,"_process_binary_name",lambda pid:"chrome.exe")
    assert watcher.locate_smaart() is None
    monkeypatch.setattr(watcher,"_process_binary_name",lambda pid:"smaart.exe")
    result=watcher.locate_smaart()
    assert result is not None and result.hwnd==55 and result.foreground
    monkeypatch.setattr(watcher,"_process_binary_name",lambda pid:"")
    assert watcher.locate_smaart() is None


def test_native_process_identity_real_self_has_no_exception():
    import os
    assert watcher._process_binary_name(os.getpid()) in ("python.exe","pythonw.exe")


def test_two_editions_bind_to_foreground_smaart_not_enum_order(monkeypatch):
    monkeypatch.setattr(watcher.win32gui,"EnumWindows",
                        lambda cb,extra:[cb(h,extra) for h in (90,80)])
    monkeypatch.setattr(watcher.win32gui,"IsWindowVisible",lambda hwnd:True)
    monkeypatch.setattr(watcher.win32gui,"GetWindowText",
                        lambda hwnd:"Smaart Suite" if hwnd==90 else "Smaart")
    monkeypatch.setattr(watcher.win32gui,"GetWindowRect",
                        lambda hwnd:(0,0,1920,1032))
    monkeypatch.setattr(watcher.win32gui,"GetForegroundWindow",lambda:80)
    monkeypatch.setattr(watcher.win32process,"GetWindowThreadProcessId",
                        lambda hwnd:(1,hwnd))
    monkeypatch.setattr(watcher,"_process_binary_name",lambda pid:"smaart.exe")
    result=watcher.locate_smaart()
    assert result.hwnd==80 and result.foreground
