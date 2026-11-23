"""Six reported defects: synthetic DSP, mocked observer and offscreen Qt only."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import time
from types import SimpleNamespace
import numpy as np
import pytest
from scipy.signal import freqz
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from signal_tools_core_v813 import design_linear_phase_fir
from trf_core import synthetic,matched


@pytest.mark.parametrize('fs',[44100,48000,96000])
@pytest.mark.parametrize('taps',[512,1024,4096])
def test_flat_fir_stays_transparent_in_band_and_neutral_region(fs,taps):
    f=np.geomspace(20,20000,1400)
    result=design_linear_phase_fir(f,np.ones_like(f,complex),np.ones_like(f),taps,fs)
    _,h=freqz(result.taps,worN=[100,1000,10000,16000,18000],fs=fs)
    assert np.max(abs(20*np.log10(abs(h))))<.1
    assert np.allclose(result.taps,result.taps[::-1],atol=1e-10)


def test_suite9_fs_uses_redirected_config_not_stale_home(monkeypatch,tmp_path):
    import smaart_fs_sync_v841 as fs
    import smaart_runtime_paths_v868 as paths
    from test_v841_smaart_fs_auto import config
    (tmp_path/'real').mkdir(); (tmp_path/'stale').mkdir()
    real=config(tmp_path/'real',96000); stale=config(tmp_path/'stale',48000)
    monkeypatch.setattr(paths,'running_major',lambda:9)
    monkeypatch.setattr(paths,'saved_config',lambda major:real if major==9 else None)
    monkeypatch.setattr(fs,'CONFIG',stale)
    assert fs.read_saved_smaart_fs().hz==96000


def test_unknown_edition_cannot_borrow_suite9_fs(monkeypatch,tmp_path):
    import smaart_fs_sync_v841 as fs
    import smaart_runtime_paths_v868 as paths
    from test_v841_smaart_fs_auto import config
    monkeypatch.setattr(paths,'running_major',lambda:None)
    monkeypatch.setattr(fs,'CONFIG',config(tmp_path))
    assert fs.read_saved_smaart_fs() is None


def test_gui_fs_binds_to_observer_window_with_both_editions_running(monkeypatch,tmp_path):
    import signal_tools_gui_v813 as gui
    import smaart_fs_sync_v841 as fs
    import smaart_runtime_paths_v868 as paths
    import smaart8_api3_readonly_v868 as api
    from test_v841_smaart_fs_auto import config
    real=config(tmp_path,96000)
    monkeypatch.setattr(paths,'running_major',lambda:None)  # multiple editions
    monkeypatch.setattr(paths,'saved_config',lambda edition:real if edition==9 else None)
    monkeypatch.setattr(api,'process_smaart_major',lambda hwnd:9 if hwnd==123 else None)
    monkeypatch.setattr(gui,'read_saved_smaart_fs',fs.read_saved_smaart_fs)
    dialog=SimpleNamespace(engine=SimpleNamespace(observer=SimpleNamespace(hwnd=123)))
    assert gui.TFDialog._saved_fs(dialog).hz==96000


def observer_page(monkeypatch,tmp_path,states):
    import live_sync_v7 as live
    import smaart8_api3_readonly_v868 as api
    files=[tmp_path/f'{i}.trf' for i in range(len(states))]
    for p in files:p.touch()
    obs=live.LiveDataBarV7(tmp_path)
    obs.ready=True; obs.hwnd=123; obs.order=files; obs.states=states.copy()
    obs.layout=(1000,800)
    bar=SimpleNamespace(iface_range_value=SimpleNamespace(CurrentValue=0))
    obs.header=(bar,0,0,800,0); obs.last_filecheck=time.perf_counter()
    obs.observe_single(time.perf_counter()-10)  # expired initial full-scan evidence
    page={}
    monkeypatch.setattr(api,'process_smaart_major',lambda _:9)
    monkeypatch.setattr(live.win32gui,'GetWindowRect',lambda _:(0,0,1000,800))
    monkeypatch.setattr(live,'printwindow_image',lambda _:None)
    monkeypatch.setattr(live,'_page',lambda *a,**k:page.copy())
    return obs,page


def test_unseen_selected_row_cannot_be_reauthorized_and_visible_rearms(monkeypatch,tmp_path):
    obs,page=observer_page(monkeypatch,tmp_path,{0:'on',1:'off'})
    page.update({1:'off'})
    for _ in range(3):obs.poll(123)
    assert obs.current_single() is None
    page.update({0:'on'})
    for _ in range(2):
        obs.poll(123); assert obs.current_single() is None
    obs.poll(123)
    assert obs.current_single()[0]==str(obs.order[0])


def test_pair_is_hidden_if_one_active_row_leaves_view(monkeypatch,tmp_path):
    obs,page=observer_page(monkeypatch,tmp_path,{0:'on',1:'on',2:'off'})
    page.update({0:'on',2:'off'})
    result=obs.poll(123)
    assert result.pair is None
    assert result.ambiguous>0


def test_different_grids_preserve_pure_delay_amplitude_and_phase():
    fb=np.geomspace(100,10000,51); middle=(fb[0]+fb[1])/2
    a=synthetic('a',np.sort(np.r_[fb,middle]))
    b=synthetic('b',fb,delay_ms=20)
    f,_,hb,_=matched(a,b)
    i=np.argmin(abs(f-middle))
    assert abs(abs(hb[i])-1)<1e-10
    assert abs(hb[i]-np.exp(-2j*np.pi*middle*.02))<1e-10


def test_underresolved_phase_segment_does_not_invent_middle_bin():
    a=synthetic('a',np.array([100.,105.,110.]))
    b=synthetic('b',np.array([100.,110.]),delay_ms=48)
    f,_,_,_=matched(a,b)
    assert 105 not in f


def test_fir_content_has_no_overlap_and_fits_its_layout():
    from signal_tools_gui_v813 import FIRDialog
    from remix_layout_v856 import style_fir
    app=QApplication.instance() or QApplication([])
    fir=FIRDialog(object())
    try:
        style_fir(fir,fir._action_row); fir.show(); app.processEvents()
        # Hidden legacy export widgets are unlaid-out by design. Their
        # default geometry is irrelevant to visible-widget overlap.
        assert fir.dsp_profile.isHidden() and fir.export_dsp.isHidden()
        assert not fir.details.geometry().intersects(fir.export_fir.geometry())
        assert fir.height()>=fir.main.minimumSize().height()
    finally:
        fir._really_close=True; fir.close()


def test_autophase_returns_immediately_and_keeps_gui_heartbeat(monkeypatch):
    import threading
    import overlay_v7 as gui
    app=QApplication.instance() or QApplication([])
    engine=gui.App(demo=True); engine.timer.stop(); engine.drag_timer.stop()
    f=np.geomspace(20,20000,200)
    engine.current_traces=(synthetic('a',f),synthetic('b',f,delay_ms=2))
    engine._selection_verified=True
    release=threading.Event()
    beats=[]; timer=QTimer(); timer.timeout.connect(lambda:beats.append(not release.is_set()))
    def slow(*a,**k):
        assert release.wait(4)
        return []
    monkeypatch.setattr(gui,'auto_align',slow)
    timer.start(10)
    try:
        start=time.monotonic(); engine.align()
        assert time.monotonic()-start<.1, 'Solver blocked GUI button slot'
        until=time.monotonic()+2
        while not beats and time.monotonic()<until:
            app.processEvents(); time.sleep(.005)
        assert any(beats), 'No GUI heartbeat while worker was still blocked'
        release.set()
        until=time.monotonic()+2
        while getattr(engine,'_align_future',None) is not None and time.monotonic()<until:
            app.processEvents(); time.sleep(.005)
        assert engine._align_future is None
    finally:
        release.set(); timer.stop(); engine.close(); app.processEvents()


@pytest.mark.parametrize('change',['roi','trace','tick','mode'])
def test_autophase_drops_stale_worker_results(monkeypatch,change):
    import threading
    import overlay_v7 as gui
    from trf_core import Candidate
    app=QApplication.instance() or QApplication([])
    engine=gui.App(demo=True); engine.timer.stop(); engine.drag_timer.stop()
    f=np.geomspace(20,20000,200)
    engine.current_traces=(synthetic('a',f),synthetic('b',f))
    engine._selection_verified=True
    entered,release=threading.Event(),threading.Event()
    calls=[]
    def slow(*args,**kwargs):
        calls.append(1); entered.set()
        assert release.wait(2)
        assert all(not a.h.flags.writeable for a in args)
        return [Candidate(1.,False,0.,100)]
    monkeypatch.setattr(gui,'auto_align',slow)
    try:
        engine.align(); assert entered.wait(1)
        for _ in range(5):engine.align()
        if change=='roi':engine.hf.setValue(engine.hf.value()+100)
        elif change=='trace':engine.current_traces=(synthetic('c',f),synthetic('d',f))
        elif change=='tick':engine._set_tick_presentation(False)
        else:
            engine.managed_mode=True; engine.overlay_tool_mode='eq'
        release.set()
        until=time.monotonic()+2
        while engine._align_future is not None and time.monotonic()<until:
            app.processEvents(); time.sleep(.005)
        assert engine._align_future is None
        assert len(calls)==1, 'Repeated clicks queued extra solves'
        assert engine.last_solve is None and engine._candidate_scope is None
    finally:
        release.set(); engine.managed_mode=False; engine.close(); app.processEvents()


def test_fir_dock_scroll_reaches_single_export_fir():
    from overlay_v7 import App
    from signal_tools_gui_v813 import ToolHub
    app=QApplication.instance() or QApplication([])
    engine=App(demo=True); engine.timer.stop(); engine.drag_timer.stop()
    hub=ToolHub(engine); hub.timer.stop(); hub.follow_timer.stop()
    hub.native_eq.timer.stop(); hub.native_fir.timer.stop()
    try:
        hub.select('fir'); hub.dock.apply_rect((0,0,205,310)); hub.dock.show()
        app.processEvents()
        bar=hub.dock.scroll.verticalScrollBar()
        # New compact FIR layout fits a normal 310px viewport outright.
        assert bar.maximum()==0
        # Smaller-height viewports must still support scrolling to Export.
        hub.dock.apply_rect((0,0,205,195))
        app.processEvents()
        assert bar.maximum()>0
        # Scroll to the actual action; hidden diagnostics remain absent.
        hub.dock.scroll.ensureWidgetVisible(hub.fir.export_fir,0,0)
        app.processEvents()
        bottom=hub.fir.export_fir.mapTo(hub.dock.scroll.viewport(),hub.fir.export_fir.rect().bottomRight())
        assert 0<=bottom.y()<hub.dock.scroll.viewport().height()
        assert not hub.fir.details.geometry().intersects(hub.fir.export_fir.geometry())
        assert hub.fir.export_txt.isHidden() and hub.fir.export_wav.isHidden()
        assert hub.fir.export_dsp.isHidden() and hub.fir.dsp_profile.isHidden()
    finally:
        hub.close(); app.processEvents()
