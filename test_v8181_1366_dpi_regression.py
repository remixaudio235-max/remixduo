import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PIL import Image,ImageDraw
from types import SimpleNamespace
from databar_icon_geometry_v8181 import classify_uia_row_gutter
from full_scan_v7 import _page
from smaart8_native_sidebar_v870 import v8_sidebar_rects, V8Slot

def make_suite_compact(two=True,checked=(True,True)):
    im=Image.new("RGB",(1366,768),(245,245,245))
    d=ImageDraw.Draw(im)
    for i,(y,color) in enumerate([(165,(15,66,140)),(187,(171,38,121))]):
        d.rectangle((19,y,32,y+17),fill=color)
        d.polygon([(27,y),(32,y),(32,y+5)],fill=(245,245,245))
        if not checked[i]:
            d.line((22,y+6,29,y+13),fill=(255,255,255),width=2)
            d.line((29,y+6,22,y+13),fill=(255,255,255),width=2)
    return im

def test_smaart8_1366_native_panel_no_longer_disappears():
    z=v8_sidebar_rects((0,0,1366,768),(0,0,1366,768))
    assert z.anchors_valid,repr(z)
    assert z.panel_mode=="v8-native-sidebar"
    x,y,w,h=z.panel
    assert 1150<x<1250 and 415<=y<=435 and w>=145 and h>=115
    assert y>412 and y+h<=576  # below engine, above generator
    assert z.toolbar_mode=="full"

def test_smaart8_1366_moved_host_coordinates():
    z=v8_sidebar_rects((100,75,1466,843),(0,0,1600,900))
    assert z.anchors_valid
    assert z.panel[0]>=1250
    assert z.panel[1]>=495
    assert z.panel[1]+z.panel[3]<=655

def test_1920_behavior_unchanged():
    z=v8_sidebar_rects((0,0,1920,1040),(0,0,1920,1040))
    assert z.panel==(1720,380,195,394)

def test_truly_small_host_fail_closed():
    z=v8_sidebar_rects((0,0,850,580),(0,0,1366,768))
    assert not z.anchors_valid

def test_compact_suite_two_solid_icons_with_uia_offset():
    im=make_suite_compact()
    # UIA rectangle x drift (+10) and normal native row y; both pixels ON.
    assert classify_uia_row_gutter(im,163,29)=="on"
    assert classify_uia_row_gutter(im,185,29)=="on"

def test_compact_suite_off_cross_not_a_false_on():
    im=make_suite_compact(checked=(True,False))
    assert classify_uia_row_gutter(im,163,29)=="on"
    assert classify_uia_row_gutter(im,185,29)=="off"

def test_compact_suite_unknown_on_blank_or_bad_geometry():
    im=Image.new("RGB",(1366,768),(245,245,245))
    assert classify_uia_row_gutter(im,163,29)=="unknown"
    assert classify_uia_row_gutter(im,5000,29)=="unknown"

class FakeRow:
    def __init__(self,top,left=22):
        self.top=top
        self.left=left
    def rectangle(self):
        return SimpleNamespace(top=self.top,left=self.left)

def test_page_uses_bounded_fallback_for_uiarow_offset():
    im=make_suite_compact()
    # expected_x=left+7=29; actual icon begins at x19.
    uia={0:FakeRow(162),1:FakeRow(184)}
    result=_page(im,["a.trf","b.trf"],0,162,150,215,29,
                 row_height=22,uia_rows=uia,window_origin=(0,0))
    assert result=={0:"on",1:"on"},result

def test_page_onoff_then_unknown_when_icon_missing():
    im=make_suite_compact(checked=(True,False))
    uia={0:FakeRow(162),1:FakeRow(184)}
    result=_page(im,["a.trf","b.trf"],0,162,150,215,29,
                 row_height=22,uia_rows=uia,window_origin=(0,0))
    assert result=={0:"on",1:"off"},result
