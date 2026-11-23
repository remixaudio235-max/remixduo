"""Branding regression: real ToolHub widgets, no audio or Smaart control."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from dock_geometry_v815 import SidebarAnchors,compute_dock_rects

def test_brand_lives_before_autophase_and_preserves_native_row():
    app=QApplication.instance() or QApplication([])
    engine=App(demo=True)
    engine.timer.stop()
    hub=ToolHub(engine)
    hub.timer.stop()
    assert hub.brand_text.text()=='RemiX Duo'
    assert not hub.brand_icon.pixmap().isNull()
    assert hub.brand_icon.pixmap().width()==24
    assert Path(__file__).with_name('remix_dou_swirl_toolbar32.png').is_file()
    screen=hub._screen_rect()
    l,t,r,b=screen
    ww=min(800,r-l-10); hh=min(650,b-t-12)
    host=(l+3,t+3,l+3+ww,t+3+hh)
    start_rt=host[2]-135
    anchors=SidebarAnchors(-1,-1,-1,
        (start_rt,host[1]+45,start_rt+35,host[1]+75),
        (start_rt+36,host[1]+45,start_rt+70,host[1]+75),
        (start_rt+71,host[1]+45,start_rt+108,host[1]+75),
        host)
    hub._anchors=anchors
    native=compute_dock_rects(host,anchors,screen)
    assert native and native.toolbar_mode=='full'
    assert hub._update_placements(host)
    app.processEvents()
    assert hub.brand_strip.isVisible(), 'brand hidden in full mode'
    assert hub.brand_icon.isVisible()
    assert hub.brand_text.isVisible()
    assert hub.width()==native.toolbar[2]+hub._brand_extra
    assert hub.x()==native.toolbar[0]-hub._brand_extra
    assert hub.x()+hub.width()==native.toolbar[0]+native.toolbar[2]
    gap=hub.buttons['phase'].geometry().left()-hub.brand_strip.geometry().right()-1
    assert 0<=gap<=8
    assert hub.buttons['phase'].text()=='Auto Phase'
    # V8.107: LAN tool removed; three native-aligned tools remain.
    assert set(hub.buttons)=={'phase','eq','fir'}
    assert all(button.isVisible() for button in hub.buttons.values())
    assert hub.grab().save(str(Path(__file__).with_name('V831_BRAND_OFFSCREEN_QA.png')))
    hub._set_toolbar_mode('menu')
    hub.brand_strip.hide()
    hub.setFixedSize(68,30)
    app.processEvents()
    assert not hub.brand_strip.isVisible()
    assert hub.menu_button.isVisible()
    hub.timer.stop();engine.timer.stop()
    hub.hide();hub.dock.hide();engine.hide()
    print('V831_BRAND_TOOLBAR_LAYOUT_PASS',flush=True)


def test_active_brand_has_room_for_full_remix_name():
    app=QApplication.instance() or QApplication([])
    engine=App(demo=True);engine.timer.stop()
    hub=ToolHub(engine,'RemiX Duo · ACTIVE','License: ACTIVE');hub.timer.stop()
    required=(1+24+4+hub.brand_text.sizeHint().width()+1+8)
    assert hub._brand_width>=required
    assert hub._brand_width==min(280,max(128,required))
    hub.hide();hub.dock.hide();engine.hide()
