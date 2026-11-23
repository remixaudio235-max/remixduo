import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from unittest.mock import patch
from smaart8_native_sidebar_v870 import v8_sidebar_rects,V8Slot
def test_v8_r59_1366x768_measured_live_top_right():
    host=(0,0,1366,768);screen=(0,0,1366,720)
    real=V8Slot(top=393,bottom=491,engine1_bottom=387,engine1_top=335)
    got=v8_sidebar_rects(host,screen,real)
    assert got.panel_mode=="v8-top-right-compact",got
    px,py,pw,ph=got.panel
    assert px>=1366-201 and pw>=180 and 195<=ph<=290
    assert px+pw<=1366-2  # strictly inside native sidebar / outside plots
    assert 0<=py<py+ph<=720
    assert got.toolbar_mode=="full"
    assert got.layout_tier=="compact"
    print("R57_GEO_1366_NATIVE",got)
def test_v8_r59_1376x760_alias():
    host=(0,0,1376,760);screen=(0,0,1376,712)
    real=V8Slot(393,483,387,335)
    got=v8_sidebar_rects(host,screen,real)
    assert got.panel_mode=="v8-top-right-compact",got
    px,py,pw,ph=got.panel
    assert px>=1376-201 and px+pw<=1376-2 and py+ph<=335-8
def test_v8_r57_offscreen_or_tiny_remains_failclosed():
    host=(0,0,850,580);screen=(0,0,1366,720)
    got=v8_sidebar_rects(host,screen,None)
    assert got.panel_mode=="no-native-space",got
def test_v8_r57_no_source_or_export_bypass():
    from inspect import getsource
    # Layout module has NO access to native export authorizations.
    import smaart8_native_sidebar_v870 as v
    assert all(x not in getsource(v.v8_sidebar_rects) for x in ("_native_export_ok","_refresh_export","SetValue","mouse.click"))
