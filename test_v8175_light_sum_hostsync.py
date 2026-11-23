"""V8.175 light SUM regression: stale layout from another Smaart edition
must not hide or replace the currently verified foreground native plot."""
import sys
sys.coinit_flags=2
from types import SimpleNamespace
import overlay_v7
class Sink:
    def __init__(self):
        self.plot_layout=SimpleNamespace(phase=(252,112,1442,417),mag=(252,572,1442,416),theme="light")
        self.plot_hwnd=10225996
        self.overlay_positioned=True
        self.applies=0
        self.refreshed=0
        self.graph_mag=SimpleNamespace(native_axis_ready=True)
        self._phase_axis_generation=0
        self._mag_axis_generation=0
    def _target_is_foreground(self,hwnd):
        return hwnd==10225996
    def _apply_plot_layout(self):
        self.applies+=1
        self.overlay_positioned=True
    def refresh_visibility(self):
        self.refreshed+=1
def test_stale_v8_success_cannot_replace_suite(monkeypatch):
    monkeypatch.setattr(overlay_v7,"locate_smaart",lambda **kwargs:SimpleNamespace(hwnd=10225996))
    s=Sink()
    previous=s.plot_layout
    old_v8=SimpleNamespace(phase=(215,83,1474,417),mag=(215,524,1474,417),theme="dark")
    overlay_v7.App.on_plot_layout(s,(5376414,old_v8))
    assert s.plot_hwnd==10225996 and s.plot_layout is previous
    assert s.overlay_positioned and s.applies==0 and s.refreshed==0
def test_stale_v8_failure_cannot_hide_suite(monkeypatch):
    monkeypatch.setattr(overlay_v7,"locate_smaart",lambda **kwargs:SimpleNamespace(hwnd=10225996))
    s=Sink()
    overlay_v7.App.on_plot_layout(s,(5376414,None))
    assert s.overlay_positioned and s.plot_layout is not None and s.refreshed==0
def test_suite_verified_layout_kept(monkeypatch):
    monkeypatch.setattr(overlay_v7,"locate_smaart",lambda **kwargs:SimpleNamespace(hwnd=10225996))
    s=Sink()
    layout=SimpleNamespace(phase=(252,112,1442,417),mag=(252,572,1442,416),theme="light")
    overlay_v7.App.on_plot_layout(s,(10225996,layout))
    assert s.plot_hwnd==10225996 and s.plot_layout is layout
    assert s.overlay_positioned and s.applies==0 # unchanged geometry
def test_suite_new_geometry_applies(monkeypatch):
    monkeypatch.setattr(overlay_v7,"locate_smaart",lambda **kwargs:SimpleNamespace(hwnd=10225996))
    s=Sink()
    layout=SimpleNamespace(phase=(252,90,1442,417),mag=(252,540,1442,416),theme="light")
    overlay_v7.App.on_plot_layout(s,(10225996,layout))
    assert s.plot_hwnd==10225996 and s.plot_layout is layout
    assert s.applies==1 and s.overlay_positioned
