"""V8.157: Smaart 8 native MagEQ must use bound window, not Suite title."""
from types import SimpleNamespace as NS
from unittest.mock import Mock
import native_eq_mag_v06 as mag
from dock_geometry_v815 import compute_dock_rects, DockRects
from smaart8_native_sidebar_v870 import V8Slot

HOST=(0,0,1920,1040)
SCREEN=(0,0,1920,1040)

def test_v8_smaart_window_bound_not_findwindow(monkeypatch):
    monkeypatch.setattr(mag.win32gui,"IsWindow",lambda h:h==808)
    monkeypatch.setattr(mag.win32gui,"IsWindowVisible",lambda h:h==808)
    monkeypatch.setattr(mag.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(mag.win32gui,"FindWindow",Mock(side_effect=AssertionError("must never FindWindow Suite title")))
    hub=NS(engine=NS(observer=NS(hwnd=808)),_last_hwnd=808)
    assert mag.verified_smaart_host(hub)==808
    hub._last_hwnd=909
    assert mag.verified_smaart_host(hub)==0

def test_suite_window_still_supported(monkeypatch):
    monkeypatch.setattr(mag.win32gui,"IsWindow",lambda h:h==909)
    monkeypatch.setattr(mag.win32gui,"IsWindowVisible",lambda h:h==909)
    monkeypatch.setattr(mag.win32gui,"IsIconic",lambda h:False)
    hub=NS(engine=NS(observer=NS(hwnd=909)),_last_hwnd=909)
    assert mag.verified_smaart_host(hub)==909

def test_minimized_unverified_source_is_strict_hold(monkeypatch):
    monkeypatch.setattr(mag.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(mag.win32gui,"IsWindowVisible",lambda h:True)
    monkeypatch.setattr(mag.win32gui,"IsIconic",lambda h:True)
    hub=NS(engine=NS(observer=NS(hwnd=808)),_last_hwnd=808)
    assert mag.verified_smaart_host(hub)==0
    hub.engine.observer.hwnd=0
    assert mag.verified_smaart_host(hub)==0

def test_v8_slot_cross_edition_never_crashes_placement():
    # A stale V8Slot can pass through old asynchronous anchor results.
    slot=V8Slot(382,688,431)
    result=compute_dock_rects(HOST,slot,SCREEN)
    assert isinstance(result,DockRects)
    assert not result.anchors_valid
