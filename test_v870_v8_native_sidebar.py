"""V8 native UI parity: three top actions and safe TF-aware dock."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from unittest.mock import patch
from smaart8_native_sidebar_v870 import v8_sidebar_rects

def test_v8_user_actual_1920x1040():
    res=v8_sidebar_rects((0,0,1920,1040),(0,0,1920,1010))
    assert res.toolbar_mode=="full"
    assert res.panel_mode=="v8-native-sidebar"
    x,y,w,h=res.toolbar
    assert 1450<x<1550 and y==65 and w==205
    px,py,pw,ph=res.panel
    assert px>=1710 and 375<=py<=395
    assert py+ph<790
    assert px+pw<=1918

def test_v8_user_uploaded_scaled_1649x895():
    res=v8_sidebar_rects((0,0,1649,895),(0,0,1649,895))
    assert res.toolbar_mode=="full"
    px,py,pw,ph=res.panel
    # R5.9: top-right dock deliberately overlays native TF settings only
    # while open, HIDE restores access; never encroach on Magnitude.
    assert res.panel_mode=="v8-top-right-compact"
    assert py<150 and py+ph<=685  # remains clear of native Generator
    assert px>=1649-201
    assert res.toolbar[0]+205<px

def test_very_small_host_hides_panel_instead_of_covering_tf():
    res=v8_sidebar_rects((0,0,850,580),(0,0,1649,895))
    assert res.toolbar_mode=="menu"
    assert res.panel_mode=="no-native-space"

def test_qt_hub_v8_three_buttons_and_native_layout():
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    try:
        host=(0,0,1920,1040)
        hub._last_hwnd=123
        hub._last_host_edition=8  # normally populated by target discovery tick
        hub._last_host_rect=host
        with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=8):
            with patch.object(hub,"_screen_rect",return_value=(0,0,1920,1010)):
                assert hub._update_placements(host)
        expected=v8_sidebar_rects(host,(0,0,1920,1010))
        assert hub._toolbar_mode=="full"
        assert hub._panel_mode=="v8-native-sidebar"
        assert hub.dock.geometry().getRect()==expected.panel
        # V8.107: LAN tab removed; Smaart-native tabs unchanged.
        assert tuple(hub.buttons)==("phase","eq","fir")
        assert [b.text() for b in hub.buttons.values()]==[
            "Auto Phase","Auto EQ","Auto FIR"]
        assert hub.dock.geometry().top()>350
    finally:
        hub.close()
        app.processEvents()
