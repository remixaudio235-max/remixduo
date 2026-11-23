"""V8.109 safety+continuity regression, no Smaart/audio/DSP use."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from types import SimpleNamespace as NS
import pytest
from mageq_presentation_gate_v853 import presentation_tick_ok
from signal_tools_gui_v813 import FIRDialog
from test_v8107_tick_rearm_no_blink import engine,commit,transient_scan,PAIR
from live_sync_v7 import SyncResult

class Field:
    def __init__(self): self.enabled=True;self.text=""
    def setEnabled(self,v):self.enabled=bool(v)
    def setText(self,v):self.text=v
    def hide(self): pass
    def blockSignals(self,*a):pass
    def clear(self):pass
    def addItem(self,*a):pass
    def setToolTip(self,*a):pass   # V8.118: FIR source shows full trace name

def _fir_preview(tmp_path,states,candidate="same"):
    path=tmp_path/"same.trf";path.write_bytes(b"same")
    stat=path.stat()
    token=(str(path),stat.st_mtime_ns,stat.st_size,3)
    snap=NS(hz=48000)
    o=NS(ready=True,order=[str(path),"other"],states=states,single_tick=None,
         single_candidate=(token[:3] if candidate=="same" else ("other",1,1)),
         current_single=lambda:None)
    preview=NS(mode="mag",fs=48000,taps=[0]*1024,source=path.stem)
    flag={"invalidations":0}
    x=NS(_fir_ready=True,engine=NS(observer=o),_fir_state=(token,snap),
         _approved=(token,"sha",snap,1024,30,16000,"mag"),
         _manual_token=None,_fir_token=token,_fir_fs=snap,result=preview,
         note=Field(),fs=Field(),source=Field(),summary=Field(),
         export_txt=Field(),export_wav=Field(),export_dsp=Field(),
         export_fir=Field(),export_menu=Field())
    x._verified_single=lambda:o.current_single()
    x._fir_fs_snapshot=lambda:snap
    x._one_tick_still_marked=lambda:FIRDialog._one_tick_still_marked(x)
    x.invalidate=lambda:(flag.__setitem__("invalidations",flag["invalidations"]+1),
                         setattr(x,"result",None))
    return x,o,preview,flag,token

def test_fir_ambiguous_viewport_one_poll_preserves_approved_preview(tmp_path):
    x,o,preview,flag,token=_fir_preview(tmp_path,{0:"unknown",1:"off"})
    FIRDialog.refresh_sources(x)
    assert x.result is preview, "FIR result was destroyed by one uncertain tick pixel"
    assert flag["invalidations"]==0
    assert not x.export_txt.enabled and not x.export_dsp.enabled
    assert x._fir_token is None and x._approved[0]==token

def test_fir_different_complete_count_does_not_retain_preview(tmp_path):
    x,o,preview,flag,token=_fir_preview(tmp_path,{0:"on",1:"on"})
    FIRDialog.refresh_sources(x)
    assert flag["invalidations"]==1 and x.result is None

def test_eq_ambiguous_two_known_on_must_refuse_display_bridge():
    token=("c:/a.trf",1,2,3)
    o=NS(ready=True,order=["a","b","c"],states={0:"on",1:"on",2:"unknown"},
         single_candidate=token[:3],current_single=lambda:None)
    ok,_,reason=presentation_tick_ok(o,token,100.,now=100.1)
    assert not ok,(reason,"two known on => cannot bridge candidate")

def test_eq_unready_observer_does_not_grant_display():
    token=("c:/a.trf",1,2,3)
    o=NS(ready=False,order=["a"],states={0:"on"},
         single_candidate=token[:3],current_single=lambda:None)
    ok,_,reason=presentation_tick_ok(o,token,100.,now=100.1)
    assert not ok,reason

@pytest.mark.parametrize("reason",["Smaart not visible",
    "Smaart HWND changed", "Data Bar HOLD: full scan failed",
    "Smaart 8: no verified TRF tick map; API V3 read-only"])
def test_sum_no_ghost_on_non_scan_transient(engine,reason):
    commit(engine)
    engine._clock["t"]+=0.3
    engine.found(SyncResult(None,reason,0,2,True,0.))
    assert not engine._selection_verified,(reason,"unsafe stale SUM display")
    assert engine.last_solve is None

def test_sum_ordinary_bad_scan_still_bridges(engine):
    commit(engine)
    engine._clock["t"]+=0.3
    engine.found(transient_scan())
    assert engine._selection_verified and not engine.solve.isEnabled()


def test_fir_ambiguous_rearm_restores_same_approved_preview(tmp_path):
    x,o,preview,flag,token=_fir_preview(tmp_path,{0:"unknown",1:"off"})
    preview.latency_ms=1.25
    FIRDialog.refresh_sources(x)
    assert x.result is preview and x._fir_token is None
    # Full 3/3 re-arm is represented by current_single() returning token;
    # the existing provenance-checking method reaccepts it, without DSP.
    o.states={0:"on",1:"off"}
    o.single_tick=token
    o.current_single=lambda:o.single_tick
    x._same_approved_source=lambda t,s:tuple(t[:3])==tuple(token[:3])
    x._refresh_export=lambda:None
    FIRDialog.refresh_sources(x)
    assert flag["invalidations"]==0 and x.result is preview
    assert x._fir_token==token and x._approved[0]==token

def test_fir_two_explicit_on_even_with_unknown_must_invalidate(tmp_path):
    x,o,preview,flag,token=_fir_preview(tmp_path,{0:"on",1:"on",2:"unknown"})
    o.order.append("third")
    FIRDialog.refresh_sources(x)
    assert flag["invalidations"]==1 and x.result is None
