"""Smaart8 R5.9: compact native RIGHT column, no Phase/Mag occlusion."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from unittest.mock import patch
import pytest
from smaart8_native_sidebar_v870 import V8Slot,v8_sidebar_rects

@pytest.mark.parametrize("host,screen,slot",[
 ((0,0,1366,768),(0,0,1366,720),V8Slot(393,491,387,335)),
 ((0,0,1376,760),(0,0,1376,712),V8Slot(393,483,387,335)),
 ((0,0,1600,900),(0,0,1600,852),V8Slot(470,550,458,410)),
 ((120,45,1496,805),(0,0,1600,900),V8Slot(440,520,435,385)),
])
def test_r59_right_panel_does_not_occlude_phase_or_magnitude(host,screen,slot):
    g=v8_sidebar_rects(host,screen,slot)
    assert g.panel_mode=="v8-top-right-compact",g
    x,y,w,h=g.panel
    native_sidebar_left=host[2]-max(201,round(201*(host[2]-host[0])/1920))
    assert x>=native_sidebar_left+1
    assert x+w<=host[2]-2
    assert x+w<=screen[2]-2
    assert y>=screen[1]+4
    assert y+h<=slot.engine1_top-7
    assert y+h<slot.engine1_bottom
    assert h>=195
    assert g.layout_tier=="compact"
    # The Phase/Mag plot ends at or before the native sidebar start.
    for plot in ((host[0]+215,host[1]+87,native_sidebar_left,host[1]+350),
                 (host[0]+215,host[1]+369,native_sidebar_left,host[3]-84)):
        assert x>=plot[2] or (y>=plot[3] or y+h<=plot[1])

def test_r59_legacy_slot_still_safe():
    slot=V8Slot(393,491,387)
    out=v8_sidebar_rects((0,0,1366,768),(0,0,1366,720),slot)
    assert out.panel_mode=="v8-top-right-compact"
    x,y,w,h=out.panel
    assert x>=1166 and y+h<=387-max(45,round(90*768/1040))-8

def test_r59_missing_native_slot_keeps_panel_in_right_column():
    out=v8_sidebar_rects((0,0,1366,768),(0,0,1366,720),None)
    assert out.panel_mode=="v8-top-right-compact"
    x,y,w,h=out.panel
    assert x>=1166 and y+h<=720-30 and h>=195

@pytest.mark.parametrize("host,screen",[
 ((0,0,1920,1040),(0,0,1920,1010)),
 ((0,0,850,580),(0,0,1366,720)),
])
def test_r59_large_and_tiny_hosts_preserve_prior_policy(host,screen):
    got=v8_sidebar_rects(host,screen)
    assert got.panel_mode!= "v8-top-right-compact"
    if host[2]-host[0]==1920:
        assert got.panel_mode=="v8-native-sidebar"
    else:
        assert got.panel_mode=="no-native-space"

def test_r59_qt_compact_tool_tabs_and_scroller():
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    try:
        host=(0,0,1366,768)
        slot=V8Slot(393,491,387,335)
        hub._last_hwnd=123
        hub._last_host_edition=8
        hub._last_host_rect=host
        hub._anchors=slot
        with patch.object(hub,"_screen_rect",return_value=(0,0,1366,720)):
            assert hub._update_placements(host)
            g=v8_sidebar_rects(host,(0,0,1366,720),slot)
            assert hub._panel_mode=="v8-top-right-compact"
            assert hub.dock.geometry().getRect()==g.panel
            for tool in ("phase","eq","fir"):
                hub.select(tool)
                assert hub.dock.geometry().getRect()==g.panel
                assert hub.dock.scroll.verticalScrollBar().maximum()>=0
                assert hub.dock.scroll.widget() is hub.dock.stack
            assert hub.dock.scroll.verticalScrollBar().maximum()>0
            hub.hide_workspace()
            assert not hub.dock.isVisible()
    finally:
        hub.close()
        app.processEvents()


def test_r59_nonstandard_wide_host_never_floats_on_magnitude():
    host=(0,0,1850,1000)
    screen=(0,0,1850,970)
    # Native sidebar has no verified free space; old R5.7 might float LEFT.
    slot=V8Slot(932,942,-1,-1)
    got=v8_sidebar_rects(host,screen,slot)
    assert got.panel_mode in ("v8-top-right-compact","no-native-space")
    if got.panel_mode=="v8-top-right-compact":
        x,y,w,h=got.panel
        assert x>=host[2]-max(201,round(201*1850/1920))
        assert x+w<=1850-2
    assert got.panel_mode!="v8-floating-compact"
