"""V8.51 native EQ marker XY drag: real biquad, spacing and Qt mouse safety."""
import math,time
from types import SimpleNamespace
import numpy as np
import pytest
from PyQt6.QtCore import QPoint,Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from peq_marker_drag_v851 import (
    PEQMarkerGrip,bounded_marker_change,preview_after_drag)
from remix_autoeq_v05_adapter import PEQ,RemixEQResult
from engines.remix_autoeq_unified import AutoEQBand,cascade_biquads
from autoeq_spacing_v850 import close_pairs
from test_v845_fir_one_trace import init as init_tools
from native_eq_mag_v06 import build_state,FitFrame
from smaart_native_mag_fit import NativeMagFit

RECT=(252,539,1442,412)


def bands():
    return (PEQ(100.,-2.,8.),PEQ(200.,-4.,9.),PEQ(600.,-2.,4.))


def x_for(hz):
    return RECT[0]+RECT[2]*math.log(hz/20)/math.log(1000)


def test_xy_drag_changes_hz_gain_and_never_q():
    original=bands()
    output=bounded_marker_change(original,0,x_for(130),630,RECT,
        press_y=650,press_gain=-2,px_per_db=10,
        lf=60,hf=1800,cut=-9,boost=2)
    assert abs(output[0].freq_hz-130)<.01
    assert output[0].gain_db==0.
    assert output[0].q==8.
    assert output[1:]==original[1:]
    assert original[0].freq_hz==100.


def test_adjacent_peq_spacing_is_a_hard_limit_and_q_unchanged():
    original=bands()
    output=bounded_marker_change(original,0,x_for(195),680,RECT,
        press_y=650,press_gain=-2,px_per_db=10,
        lf=60,hf=1800,cut=-9,boost=2)
    assert output[0].freq_hz<=200/2**.25+1e-7
    assert not close_pairs(output)
    assert output[0].q==original[0].q
    down=bounded_marker_change(original,0,x_for(20),1200,RECT,
        press_y=650,press_gain=-2,px_per_db=10,
        lf=60,hf=1800,cut=-9,boost=2)
    assert down[0].freq_hz==60
    assert down[0].gain_db==-9.


def test_high_frequency_roi_cut_and_boost_bounds():
    original=bands()
    output=bounded_marker_change(original,2,x_for(12000),100,RECT,
        press_y=650,press_gain=-2,px_per_db=10,
        lf=60,hf=8000,cut=-9,boost=2)
    assert output[2].freq_hz==8000
    assert output[2].gain_db==2.
    assert output[2].q==4.


def test_reject_unusable_geometry_and_unsatisfiable_roi():
    with pytest.raises(ValueError):
        bounded_marker_change(bands(),0,300,400,(0,0,0,0),400,-2,10,
                              60,1800,-9,2)
    with pytest.raises(ValueError):
        bounded_marker_change(bands(),0,300,400,RECT,400,-2,0.,
                              60,1800,-9,2)
    with pytest.raises(ValueError):
        bounded_marker_change(bands(),0,300,400,RECT,400,-2,10,
                              90,110,-9,2)


def test_edited_mag_is_exact_biquad_and_does_not_change_original():
    f=np.geomspace(20,20000,960)
    src=np.full(len(f),-6.,dtype=float)
    orig=bands()
    eq=20*np.log10(abs(cascade_biquads(f,
        [AutoEQBand("P",p.freq_hz,p.gain_db,p.q) for p in orig],48000)))
    r=RemixEQResult(f,src,src+eq,np.zeros_like(f),orig,
        6.,5.,"PREVIEW_READY",48000,"QA",())
    w=np.ones_like(f)
    changed=bounded_marker_change(orig,0,x_for(122),608,RECT,
        650,-2,10,60,1800,-9,2)
    v=preview_after_drag(r,changed,w)
    neweq=20*np.log10(abs(cascade_biquads(f,
        [AutoEQBand("P",p.freq_hz,p.gain_db,p.q) for p in changed],48000)))
    assert np.allclose(v.after_db,src+neweq,atol=1e-10)
    assert np.array_equal(v.before_db,r.before_db)
    assert np.array_equal(r.after_db,src+eq)
    assert v.peqs[1:]==orig[1:]
    assert "MANUAL_PEQ_DRAG" in v.warnings[-1]
    assert v.rms_after>0.


def test_qt_grip_intercepts_only_small_window_without_focus():
    app=QApplication.instance() or QApplication([])
    events=[]
    grip=PEQMarkerGrip(3,lambda n,x,y,phase:
                       events.append((n,phase,x,y)) or True)
    grip.move(400,400)
    grip.show()
    app.processEvents()
    try:
        assert grip.size().width()==30 and grip.size().height()==22
        assert bool(grip.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        assert not grip.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        QTest.mousePress(grip,Qt.MouseButton.LeftButton,pos=QPoint(15,11))
        QTest.mouseMove(grip,QPoint(23,4))
        QTest.mouseRelease(grip,Qt.MouseButton.LeftButton,pos=QPoint(23,4))
        assert not grip.dragging
        assert events[0][1]=="start" and events[-1][1]=="end"
        assert all(t[0]==3 for t in events)
    finally:grip.close()


def test_drag_preview_requires_reverified_native_source_and_disables_export(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from signal_tools_gui_v813 import EQExportSnapshot
    app,obs,engine,hub,_=init_tools()
    hub.select("eq")
    hub.native_eq.timer.stop()
    hub.timer.stop()
    eq=hub.eq
    # Qt/offscreen drag QA owns a fake ONE-tick observer, but the real
    # Smaart background scan may overwrite its tick while the PEQ worker
    # runs. Freeze ONLY the synthetic source for this focused gesture
    # test; real trace-change/invalidation is covered by V8.53 suites.
    qa_token=eq._verified_single()
    assert qa_token is not None
    monkeypatch.setattr(eq,"_verified_single",lambda:qa_token)
    try:
        eq.compute()
        until=time.monotonic()+12.
        while eq.result is None and time.monotonic()<until:
            app.processEvents()
            time.sleep(.018)
        assert eq.result is not None
        assert eq.result.peqs
        assert hub.native_eq.source is not None
        src=hub.native_eq.source
        fit=NativeMagFit(170,11.5,0,1,0,150,True,"native")
        frame=FitFrame(src.revision,RECT,fit,"blue",time.monotonic(),
                       77,(0,0,1920,1040),src.source_identity,True,True)
        hub.native_eq.frame=frame
        engine.graph_mag.setGeometry(*RECT)
        engine.graph_mag.set_mageq(src,frame)
        engine.graph_mag.show()
        app.processEvents()
        # A pending Qt singleShot from initial native_ready can clear
        # the test's frame; bind synthetic proof AFTER processing it.
        hub.native_eq.frame=frame
        engine.graph_mag.set_mageq(src,frame)
        monkeypatch.setattr(eq,"_native_export_ok",lambda **kw:True)
        monkeypatch.setattr(hub.native_eq,"_source_binding_ok",lambda:True)
        import native_eq_mag_v06 as n
        monkeypatch.setattr(n,"frame_is_fresh_for_window",
                            lambda *a,**kw:True)
        n0=len(eq.result.peqs)
        start=eq.result.peqs[0]
        marker_x=x_for(start.freq_hz)
        # Offscreen App is intentionally not positioned on a real Smaart
        # native window; simulate its confirmed visible renderer only.
        monkeypatch.setattr(engine.graph_mag,"isVisible",lambda:True)
        assert eq.drag_peq_marker(1,marker_x,700,"start")
        assert not eq.export.isEnabled()
        assert eq._export_snapshot is None
        # Drag slightly right, upwards (Gain increases), respect spacing.
        assert eq.drag_peq_marker(1,marker_x+18,682,"move")
        assert eq.drag_peq_marker(1,marker_x+18,682,"end")
        assert len(eq.result.peqs)==n0
        assert eq.result.peqs[0].q==start.q
        assert not close_pairs(eq.result.peqs)
        assert eq._export_snapshot is not None
        assert hub.native_eq.source.source_identity==src.source_identity
        assert "MANUAL PEQ" in eq.summary.text()
        assert engine.graph_mag.mageq_source is hub.native_eq.source
        # Once native identity is missing, starting a new edit must fail.
        monkeypatch.setattr(eq,"_native_export_ok",lambda **kw:False)
        assert not eq.drag_peq_marker(1,marker_x,700,"start")
    finally:
        hub.close()
        engine.close()
        app.processEvents()



def test_real_graph_marker_grips_follow_native_pixels_and_hide_with_tool(monkeypatch):
    from overlay_v7 import App
    from mageq_visual_v13 import build_geometry
    app=QApplication.instance() or QApplication([])
    freq=np.geomspace(20.,20000.,1200)
    h=np.ones_like(freq,dtype=complex)*10**(-6/20)
    coh=np.ones_like(freq)
    source=build_state(freq,h,coh,(
        PEQ(120.,-3.0,8.),
        PEQ(500.,-2.5,8.),
        PEQ(1600.,-4.0,10.),
    ),fs=48000,source_index=0,source_name="QA",revision=851)
    frame=FitFrame(source.revision,RECT,
        NativeMagFit(205.,11.5,-6.,1.,0.,160,True,"QA native"),"blue",
        time.monotonic(),77,(0,0,1920,1040),source.source_identity,True,True)
    import native_eq_mag_v06 as n
    monkeypatch.setattr(n,"frame_is_fresh_for_window",lambda *a,**kw:True)
    engine=App(False)
    engine.timer.stop()
    engine.managed_mode=True
    engine.ui_tool_enabled=False
    engine.overlay_tool_mode="eq"
    engine.overlay_workspace_visible=True
    engine.overlay_positioned=True
    engine._eq_tick_safe=lambda:True
    engine.graph_mag.setGeometry(*RECT)
    engine.graph_mag.set_mageq(source,frame)
    engine.refresh_visibility()
    app.processEvents()
    try:
        geo=build_geometry(source,frame)
        for mark in geo.markers:
            g=engine.eq_peq_grips[mark.number]
            if mark.visible:
                assert g.isVisible()
                assert abs((g.x()+g.width()/2)-(RECT[0]+mark.x))<=1
                assert abs((g.y()+g.height()/2)-(RECT[1]+mark.y))<=1
        assert engine.graph_mag.testAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        engine.overlay_tool_mode="phase"
        engine.refresh_visibility()
        app.processEvents()
        assert not any(g.isVisible() for g in engine.eq_peq_grips.values())
        engine.overlay_tool_mode="fir"
        engine.refresh_visibility()
        app.processEvents()
        assert not any(g.isVisible() for g in engine.eq_peq_grips.values())
    finally:
        engine.close()
        app.processEvents()
