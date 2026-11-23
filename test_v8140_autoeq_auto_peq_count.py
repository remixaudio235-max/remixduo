"""V8.140: Auto EQ chooses its PEQ budget instead of fixing it at eight."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
import numpy as np

from remix_duo.core import autoeq
from test_v845_fir_one_trace import init


def test_auto_peq_budget_selects_smallest_near_best_plan(monkeypatch):
    calls=[]
    base=autoeq.RemixEQResult(
        np.array([100.,1000.]),np.array([3.,-3.]),np.zeros(2),np.zeros(2),
        (autoeq.PEQ(500.,-2.,4.),),3.,1.,"PREVIEW_READY",48000,"fixture",())

    def fake_design(*args,filters,boost,cut,**kwargs):
        calls.append(filters)
        # Best is 8 filters. Six is only 0.04 dB worse and must win because
        # the extra complexity is not a meaningful flattening improvement.
        rms={1:1.4,2:1.1,3:.8,4:.55,5:.34,6:.24,7:.22,8:.20,
             9:.21,10:.22,11:.23,12:.24}[filters]
        return replace(base,rms_after=rms)

    monkeypatch.setattr(autoeq,"design_remix_eq",fake_design)
    result=autoeq.design_remix_eq_auto_limits(
        np.arange(32.),np.ones(32,complex),np.ones(32),fs=48000,filters=0)
    assert calls==[4,8,12]
    assert result.filters_auto
    assert result.filter_limit==8
    assert any("AUTO PEQ: tối đa 8" in w for w in result.warnings)


def test_auto_eq_panel_defaults_to_auto_peq_count():
    app,observer,engine,hub,_=init()
    try:
        assert hub.eq.filter_count.minimum()==0
        assert hub.eq.filter_count.value()==0
        assert hub.eq.filter_count.specialValueText()=="AUTO"
        assert hub.eq._parameters()["filters"]==0
    finally:
        hub.close();engine.close();app.processEvents()


def test_auto_peq_skips_12_after_8_hits_safety_gate(monkeypatch):
    calls=[]
    base=autoeq.RemixEQResult(
        np.array([100.,1000.]),np.array([3.,-3.]),np.zeros(2),np.zeros(2),
        (autoeq.PEQ(500.,-2.,4.),),3.,1.,"PREVIEW_READY",48000,"fixture",())

    def fake(*args,filters,**kwargs):
        calls.append(filters)
        if filters==8:
            raise ValueError("unacceptable target regression")
        return replace(base,filter_limit=filters,limits_auto=True)

    monkeypatch.setattr(autoeq,"_design_with_auto_limits",fake)
    result=autoeq.design_remix_eq_auto_limits(
        np.arange(32.),np.ones(32,complex),np.ones(32),fs=48000,filters=0)
    assert calls==[4,8]
    assert result.filter_limit==4
