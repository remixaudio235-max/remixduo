import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
import numpy as np
from PyQt6.QtTest import QTest

from remix_duo.core import autoeq
from test_v845_fir_one_trace import init


def test_delayed_auto_notice_only_after_50ms(monkeypatch):
    import signal_tools_gui_v813 as tools
    app, observer, engine, hub, _ = init()
    calls=[]
    running={"value": True}
    monkeypatch.setattr(tools, "show_notice", lambda target, text: calls.append(text))
    try:
        tools.schedule_auto_wait_notice(hub.eq, lambda: running["value"])
        QTest.qWait(35); app.processEvents()
        assert calls == []
        QTest.qWait(30); app.processEvents()
        assert calls == ["Đang Auto, vui lòng đợi..."]
        calls.clear()
        tools.schedule_auto_wait_notice(hub.eq, lambda: running["value"])
        running["value"] = False
        QTest.qWait(65); app.processEvents()
        assert calls == []
    finally:
        hub.close(); app.processEvents()


def test_autoeq_limits_switch_from_auto_to_manual():
    app, observer, engine, hub, _ = init()
    try:
        eq=hub.eq
        assert eq.boost.isEnabled() and eq.cut.isEnabled()
        assert not eq._limits_manual
        eq.cut.setValue(-6.0)
        assert eq._limits_manual
        params=eq._parameters()
        assert params["boost"] == eq.boost.value()
        assert params["cut"] == -6.0
        eq.cut.setValue(-12.0)
        eq.boost.setValue(0.0)  # pair 0/-12 explicitly returns to AUTO
        assert not eq._limits_manual
        params=eq._parameters()
        assert params["boost"] is None and params["cut"] is None
    finally:
        hub.close(); app.processEvents()


def test_manual_limits_preserved_during_auto_peq_budget(monkeypatch):
    calls=[]
    base=autoeq.RemixEQResult(
        np.array([100.,1000.]),np.array([3.,-3.]),np.zeros(2),np.zeros(2),
        (autoeq.PEQ(500.,-2.,4.),),3.,1.,"PREVIEW_READY",48000,"fixture",())

    def fake(*args,filters,boost,cut,**kwargs):
        calls.append((filters,boost,cut))
        return replace(base,rms_after={4:.4,8:.2,12:.21}[filters],
                       filter_limit=filters,boost_limit_db=boost,cut_limit_db=cut)

    monkeypatch.setattr(autoeq,"design_remix_eq",fake)
    result=autoeq.design_remix_eq_auto_limits(
        np.arange(32.),np.ones(32,complex),np.ones(32),fs=48000,
        filters=0,boost=3.0,cut=-8.0)
    assert calls == [(4,3.0,-8.0),(8,3.0,-8.0),(12,3.0,-8.0)]
    assert result.filter_limit == 8
    assert not result.limits_auto
