"""V8.172 regression: native X-axis ambiguity is fail-closed."""
from types import SimpleNamespace as NS
import smaart8_native_xaxis_v8172 as axis
from smaart_eq_color_select import ColorFit

class Frame:
    valid=True
    def __init__(self,*args,**kwargs):pass
    def visible_colors(self,*args,**kwargs):return ("cyan",)

def test_equally_strong_axis_hypotheses_never_authorize(monkeypatch):
    monkeypatch.setattr(axis,"NativeMagFrame",Frame)
    good=NS(accepted=True,score=.90,bins=240)
    monkeypatch.setattr(axis,"choose_color_fit",
        lambda *a,**k:ColorFit("cyan",good,0.,True))
    assert axis.select_smaart8_native_axis(None,(215,524,1474,417),
           (0,0,1920,1032),None,None,None) is None

def test_unknown_native_axis_fails_closed(monkeypatch):
    monkeypatch.setattr(axis,"NativeMagFrame",Frame)
    monkeypatch.setattr(axis,"choose_color_fit",lambda *a,**k:None)
    assert axis.select_smaart8_native_axis(None,(215,524,1474,417),
            (0,0,1920,1032),None,None,None) is None

def test_changed_trace_color_fails_closed(monkeypatch):
    monkeypatch.setattr(axis,"NativeMagFrame",Frame)
    assert axis.select_smaart8_native_axis(None,(215,524,1474,417),
           (0,0,1920,1032),None,None,None,preferred_color="magenta") is None
