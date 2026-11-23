"""Native layout transient detection must not erase SUM for one bad UIA frame."""
import time
from types import SimpleNamespace
import pytest
from overlay_v7 import App
import overlay_v7

@pytest.fixture
def rig(monkeypatch):
    fake=SimpleNamespace(
        plot_hwnd=99,
        plot_layout=SimpleNamespace(phase=(252,84,1442,412),
                                    mag=(252,539,1442,412)),
        _plot_native_window_rect=(0,0,1920,1040),
        _plot_last_good=time.monotonic(),
        overlay_positioned=True,
        refresh_visibility=lambda:None,
    )
    monkeypatch.setattr(overlay_v7.win32gui,"IsWindow",lambda hwnd:hwnd==99)
    monkeypatch.setattr(overlay_v7.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(overlay_v7.win32gui,"GetWindowRect",lambda hwnd:(0,0,1920,1040))
    return fake

def test_one_failed_frame_retains_sums(rig):
    App.on_plot_layout(rig,None)
    assert rig.plot_layout is not None
    assert rig.overlay_positioned

def test_old_good_frame_can_expire(rig):
    rig._plot_last_good-=3.
    App.on_plot_layout(rig,None)
    assert rig.plot_layout is None
    assert not rig.overlay_positioned

def test_window_move_invalidates_stale_screen_coordinates(rig,monkeypatch):
    monkeypatch.setattr(overlay_v7.win32gui,"GetWindowRect",lambda hwnd:(40,0,1960,1040))
    App.on_plot_layout(rig,None)
    assert rig.plot_layout is None
    assert not rig.overlay_positioned

def test_minimized_window_invalidates(rig,monkeypatch):
    monkeypatch.setattr(overlay_v7.win32gui,"IsIconic",lambda hwnd:True)
    App.on_plot_layout(rig,None)
    assert rig.plot_layout is None
