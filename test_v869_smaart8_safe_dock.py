"""Smaart 8 right native controls must remain accessible."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from unittest.mock import patch
from smaart8_safe_dock_v869 import safe_v8_panel

HOST=(0,0,1649,895)
SCREEN=(0,0,1649,895)
NATIVE_TF=(1479,144,1640,300)
NATIVE_GENERATOR=(1479,703,1640,780)
NATIVE_MAG=(185,540,1470,812)

def overlaps(a,b):
    x,y,w,h=a
    l,t,r,bot=b
    return x<r and x+w>l and y<bot and y+h>t

def test_v8_panel_avoids_tf_generator_and_all_plots():
    panel=safe_v8_panel(HOST,SCREEN)
    assert panel is not None
    assert panel[0]>=1474
    assert panel[1]>=305
    assert panel[1]+panel[3]<=699
    assert panel[2]>=148 and panel[2]<=162
    for native in (NATIVE_TF,NATIVE_GENERATOR,NATIVE_MAG):
        assert not overlaps(panel,native),native

def test_v8_panel_follow_window_translation_without_native_overlap():
    shifted=(100,50,1749,945)
    display=(0,0,1920,1080)
    panel=safe_v8_panel(shifted,display)
    assert panel is not None and panel[0]>=1580 and panel[1]>=360
    assert panel[1]+panel[3]<749

def test_small_smaart_window_does_not_fall_back_over_tf():
    assert safe_v8_panel((0,0,1000,550),(0,0,1649,895)) is None
    assert safe_v8_panel((0,0,1649,590),(0,0,1649,895)) is None
    assert safe_v8_panel((0,0,800,895),(0,0,1649,895)) is None

def test_real_hub_uses_safe_slot_instead_of_legacy_tf_overlap():
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    try:
        hub._last_hwnd=123
        hub._last_host_edition=8  # normally populated by target discovery tick
        hub._last_host_rect=HOST
        with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=8):
            with patch.object(hub,"_screen_rect",return_value=SCREEN):
                assert hub._update_placements(HOST)
        # R5.9 top-right compact takes the native TF settings column
        # temporarily, never the Magnitude plot or Signal Generator.
        assert hub._panel_mode=="v8-top-right-compact"
        from smaart8_native_sidebar_v870 import v8_sidebar_rects
        x,y,w,h=hub.dock.geometry().getRect()
        assert (x,y,w,h)==v8_sidebar_rects(HOST,SCREEN).panel
        assert not overlaps((x,y,w,h),NATIVE_MAG)
        assert not overlaps((x,y,w,h),NATIVE_GENERATOR)
        assert hub.dock.scroll.horizontalScrollBarPolicy() is not None
    finally:
        hub.close()
        app.processEvents()
