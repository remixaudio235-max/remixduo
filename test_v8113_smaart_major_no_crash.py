"""V8.113: overlay crashed live 2026-11-11 under low commit memory.

process_smaart_major() is called from App.tick() every 33 ms. Under memory
pressure win32api.GetFileVersionInfo raised pywintypes.error 1812, which is
NOT an OSError, escaped tick() and PyQt6 aborted the whole overlay.
It must fail closed (None) and not re-read Smaart.exe version info per tick.
"""
from types import SimpleNamespace as NS
import pywintypes
import smaart8_api3_readonly_v868 as api


def patch(monkeypatch,version):
    monkeypatch.setattr(api.win32process,"GetWindowThreadProcessId",lambda h:(1,4242))
    monkeypatch.setattr(api.psutil,"Process",
        lambda pid:NS(exe=lambda:r"C:\Program Files\Smaart Suite\Smaart.exe",
                      create_time=lambda:123.0))
    calls=[]
    def info(path,_):
        calls.append(path)
        if isinstance(version,Exception):raise version
        return {"FileVersionMS":version<<16}
    monkeypatch.setattr(api.win32api,"GetFileVersionInfo",info)
    api._MAJOR_CACHE.clear()
    return calls


def test_pywintypes_error_fails_closed(monkeypatch):
    patch(monkeypatch,pywintypes.error(1812,"GetFileVersionInfo","no resource"))
    assert api.process_smaart_major(77) is None


def test_version_cached_per_process(monkeypatch):
    calls=patch(monkeypatch,9)
    for _ in range(50):
        assert api.process_smaart_major(77)==9
    assert len(calls)==1
