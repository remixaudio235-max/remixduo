"""Regression reproducer: returning to a previously selected pair must re-load SUM."""
from pathlib import Path
import overlay_v7
from selection_v7 import SelectionController
from stable_ticks_v824 import StableTickGate
from live_sync_v7 import SyncResult
def _two(native_source,frame,stem="CM P1 SUB"):
    pair=("C:/Smaart/"+stem+"-1.trf","C:/Smaart/SUb P1 rin rin-1.trf")
    return SyncResult(pair,"Verified viewport 26 rows",26,26,False,
                      float(frame),pair,0,native_source,frame,pair)
def test_unprotected_clear_reproduces_lost_sum_on_same_pair():
    seen=[]
    c=SelectionController(lambda x:seen.append(x))
    pair=("C:/Smaart/CM P1 SUB-1.trf","C:/Smaart/SUb P1 rin rin-1.trf")
    assert c.apply(pair,"initial")
    # Original host switch cleared QWidget but not controller.last_pair.
    seen.append(None)
    assert not c.apply(pair,"rearm")  # authoritative controller thinks it is unchanged
    assert len([x for x in seen if x is not None])==1
def test_fixed_host_invalidate_reloads_exact_pair_and_rejects_stale_future():
    seen=[]
    c=SelectionController(lambda x:seen.append(x))
    pair=("C:/Smaart/CM P1 SUB-1.trf","C:/Smaart/SUb P1 rin rin-1.trf")
    assert c.apply(pair,"initial")
    old_generation=c.generation
    assert c.invalidate("Smaart edition changed")
    assert c.last_pair is None
    assert c.generation==old_generation+1
    assert not c.is_current(old_generation,pair)
    gate=StableTickGate(required=3)
    src=(99,"C:/Smaart")
    for i in range(1,3):
        frame=_two(src,i)
        d=gate.evaluate(frame,frame.active_names,frame.ambiguous)
        assert d.state=="pending",d
        assert c.last_pair is None
    frame=_two(src,3)
    d=gate.evaluate(frame,frame.active_names,frame.ambiguous)
    assert d.state=="valid" and d.changed
    assert c.apply(d.pair,"3/3 native rearm")
    assert seen[-1] is not None and seen[-1].names==pair
    assert c.is_current(seen[-1].generation,pair)
def test_no_pair_invalidate_is_idempotent_then_rearm():
    seen=[]
    c=SelectionController(lambda event:seen.append(event))
    assert not c.invalidate("Smaart edition changed")
    gate=StableTickGate(required=3)
    src=(99,"C:/Smaart")
    for i in range(1,4):
        frame=_two(src,i)
        d=gate.evaluate(frame,frame.active_names,frame.ambiguous)
    assert d.state=="valid"
    assert c.apply(d.pair,"3/3 native rearm")
def test_integrated_host_switch_uses_authoritative_invalidation_not_plot_only():
    text=(Path(overlay_v7.__file__).read_text(encoding="utf-8"))
    segment=text.split('if target_folder is not None and self.observer.folder!=target_folder:',1)[1].split('self.plot_hwnd=None;self.plot_layout=None',1)[0]
    assert 'self.controller.invalidate("Smaart edition changed")' in segment
    assert 'self.tick_gate=StableTickGate(required=3)' in segment
    assert "self._selection_verified=False" in segment
