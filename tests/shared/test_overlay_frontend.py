from dataclasses import replace
import time
from PyQt6.QtWidgets import QApplication
from remix_duo.platforms.contracts import WindowRef,WindowState

def host():return WindowState(WindowRef('darwin',10,'start','20'),(100,80,1200,760),'Smaart',True,True,'9.6')

def test_manual_workspace_can_reopen_after_closing():
    from remix_duo.ui.overlay import OverlayController
    app=QApplication.instance() or QApplication([])
    class Backend:
        def configure_overlay(self,widget):pass
    c=OverlayController(Backend(),start=False)
    try:
        c.open_manual();old=c.manual;old.close()
        assert old._closed
        c.open_manual()
        assert c.manual is not old and not c.manual._closed
        assert c.manual.native_monitor is None
        from remix_duo.application.design import DesignRequest
        from remix_duo.core.traces import synthetic
        import numpy as np
        request=DesignRequest.create('fir',synthetic('flat',np.geomspace(20,20000,600)),fs=48000)
        c.manual.submit_request(request)
        deadline=time.monotonic()+5
        while c.manual.result is None and time.monotonic()<deadline:
            app.processEvents();time.sleep(.005)
        assert c.manual.result is not None
    finally:c.close()

def test_toolbar_and_tool_panel_follow_host_without_opening_workspace():
    from remix_duo.ui.overlay import OverlayController,overlay_rects
    app=QApplication.instance() or QApplication([])
    class Backend:
        def configure_overlay(self,widget):pass
    controller=OverlayController(Backend(),start=False)
    state=host();controller.follow_host(state)
    assert controller.bar.isVisible()
    assert controller.bar.width()==410
    assert set(controller.bar.buttons)=={'phase','eq','fir'}
    controller.open_tool('phase')
    assert controller.panel.isVisible() and controller.panel.width()==446
    newer=replace(state,rect=(160,120,900,600))
    controller.follow_host(newer)
    expected=overlay_rects(newer,controller.screen_bounds(newer))
    assert controller.bar.geometry().getRect()==expected[0]
    assert controller.panel.geometry().getRect()==expected[1]
    assert controller.native_plots==[]
    controller.follow_host(None)
    assert not controller.bar.isVisible() and not controller.panel.isVisible()
    controller.close()

def test_own_companion_focus_keeps_overlay_while_other_app_hides_it():
    from remix_duo.ui.overlay import OverlayController
    app=QApplication.instance() or QApplication([])
    class Backend:
        def configure_overlay(self,widget):pass
    controller=OverlayController(Backend(),start=False)
    companion=replace(host(),foreground=False,companion_foreground=True)
    controller.follow_host(companion)
    assert controller.bar.isVisible()
    controller.follow_host(replace(companion,companion_foreground=False))
    assert not controller.bar.isVisible()
    controller.close()

def test_missing_tick_proof_fails_closed_with_visible_reason():
    from remix_duo.ui.overlay import OverlayController
    app=QApplication.instance() or QApplication([])
    class Backend:
        def configure_overlay(self,widget):pass
    controller=OverlayController(Backend(),start=False)
    controller.follow_host(host());controller.open_tool('eq');controller.run_tool()
    assert 'HOLD' in controller.panel.status.text()
    assert controller.native_plots==[]
    controller.close()

def test_panel_restores_after_host_returns_but_explicit_hide_stays_hidden():
    from remix_duo.ui.overlay import OverlayController
    app=QApplication.instance() or QApplication([])
    class Backend:
        def configure_overlay(self,widget):pass
    c=OverlayController(Backend(),start=False);c.follow_host(host());c.open_tool('fir')
    c.follow_host(None);c.follow_host(host());assert c.panel.isVisible()
    c.hide_tool();c.follow_host(None);c.follow_host(host());assert not c.panel.isVisible()
    c.close()

def test_mac_entry_uses_overlay_by_default_and_workspace_only_when_requested(monkeypatch,tmp_path):
    from remix_duo import entry
    from remix_duo.platforms import factory,paths
    from remix_duo.licensing import gate
    from remix_duo.ui import overlay,workspace
    import PyQt6.QtWidgets as qt
    called=[]
    class Signal:
        def connect(self,*args):pass
    class App:
        def __init__(self,*args):self.aboutToQuit=Signal()
        def setApplicationName(self,*args):pass
        def setWindowIcon(self,*args):pass
        def setQuitOnLastWindowClosed(self,*args):pass
        def exec(self):return 0
    class Lease:
        def close(self):pass
    class Backend:
        platform='MAC'
        def acquire_lock(self,*args):return Lease()
    class View:
        def __init__(self,kind):called.append(kind)
        def close(self):pass
        def show(self):pass
    monkeypatch.setattr(qt,'QApplication',App)
    monkeypatch.setattr(factory,'services',lambda:Backend())
    monkeypatch.setattr(paths,'app_paths',lambda:type('Paths',(),{'data':tmp_path,'resource':lambda self,name:tmp_path/name})())
    monkeypatch.setattr(gate,'activation_gate',lambda:True)
    monkeypatch.setattr(overlay,'OverlayController',lambda backend:View('overlay'))
    monkeypatch.setattr(workspace,'Workspace',lambda backend:View('workspace'))
    assert entry.main([])==0 and called==['overlay']
    assert entry.main(['--workspace'])==0 and called==['overlay','workspace']
