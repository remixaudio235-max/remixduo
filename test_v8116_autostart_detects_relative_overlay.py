"""V8.116: autostart watcher must see a Duo started as `python overlay_v7.py`.

duo_running() only matched the ABSOLUTE script path, so an overlay launched
with a relative argument (cwd = install dir) was invisible and the watcher
would open a second overlay on the next Smaart start.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import smaart_autostart_v875 as auto


def fake_procs(monkeypatch, procs):
    import psutil
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: iter(procs))


def proc(cmdline, cwd, exe="C:/py/python.exe"):
    return NS(info={"name": "python.exe", "exe": exe, "cmdline": cmdline},
              cwd=lambda: cwd)


def test_relative_overlay_in_install_dir_is_detected(monkeypatch, tmp_path):
    (tmp_path / "overlay_v7.py").write_text("")
    fake_procs(monkeypatch, [proc(["python.exe", "-X", "faulthandler", "overlay_v7.py"], str(tmp_path))])
    assert auto.duo_running(tmp_path)


def test_relative_overlay_elsewhere_is_not_ours(monkeypatch, tmp_path):
    (tmp_path / "overlay_v7.py").write_text("")
    other = tmp_path / "other"; other.mkdir()
    fake_procs(monkeypatch, [proc(["python.exe", "overlay_v7.py"], str(other))])
    assert not auto.duo_running(tmp_path)


def test_absolute_overlay_still_detected(monkeypatch, tmp_path):
    (tmp_path / "overlay_v7.py").write_text("")
    fake_procs(monkeypatch, [proc(["pythonw.exe", str(tmp_path / "overlay_v7.py")], "C:/")])
    assert auto.duo_running(tmp_path)
