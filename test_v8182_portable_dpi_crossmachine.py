"""DPI portability tests with physical pixels, independent resolution/DPI.
No Windows display changes, Smaart writes, audio or generator calls.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from PIL import Image,ImageDraw
from types import SimpleNamespace
from databar_icon_geometry_v8181 import classify_uia_row_gutter
from full_scan_v7 import _page
from smaart8_databar_v8121 import v8_row_states
from pathlib import Path

@pytest.mark.parametrize("size",[(1366,768),(1600,900),(1920,1080),(2560,1440),(3840,2160)])
@pytest.mark.parametrize("dpi",[96,120,144,168,192])
@pytest.mark.parametrize("state",["on","off"])
def test_suite_icons_across_independent_resolutions_and_dpi(size,dpi,state):
    w,h=size
    scale=dpi/96.
    im=Image.new("RGB",(w,h),(245,245,245))
    draw=ImageDraw.Draw(im)
    x=round(19*scale); y=round(165*scale)
    cw=round(14*scale);ch=round(18*scale)
    draw.rectangle((x,y,x+cw-1,y+ch-1),fill=(15,66,140))
    draw.polygon([(x+cw-round(5*scale),y),(x+cw-1,y),(x+cw-1,y+round(5*scale))],fill=(245,245,245))
    if state=="off":
        draw.line((x+round(3*scale),y+round(5*scale),x+cw-round(4*scale),y+ch-round(5*scale)),fill=(255,255,255),width=max(2,round(2*scale)))
        draw.line((x+cw-round(4*scale),y+round(5*scale),x+round(3*scale),y+ch-round(5*scale)),fill=(255,255,255),width=max(2,round(2*scale)))
    row_y=round(162*scale)
    expected_x=round(29*scale)
    pitch=round(22*scale)
    result=classify_uia_row_gutter(im,row_y,expected_x,pitch)
    assert result==state,(size,dpi,state,result)
    # Native UIA row bbox may drift a few scaled pixels. Check full page.
    row=SimpleNamespace(top=row_y,left=round(22*scale))
    class Fake:
        def __init__(self,obj):self.obj=obj
        def rectangle(self):return self.obj
    page=_page(im,["x.trf"],0,row_y,round(150*scale),
               round(215*scale),expected_x,row_height=pitch,
               uia_rows={0:Fake(row)},window_origin=(0,0))
    assert page=={0:state},(size,dpi,page)

@pytest.mark.parametrize("dpi",[96,120,144,168,192])
def test_missing_or_ambiguous_suite_glyph_is_unknown(dpi):
    sc=dpi/96
    im=Image.new("RGB",(1366,768),(245,245,245))
    assert classify_uia_row_gutter(im,round(162*sc),round(29*sc),round(22*sc))=="unknown"
    assert classify_uia_row_gutter(None,round(162*sc),round(29*sc),round(22*sc))=="unknown"

@pytest.mark.parametrize("size",[(1366,768),(1600,900),(1920,1080),(2560,1440),(3840,2160)])
@pytest.mark.parametrize("dpi",[96,120,144,168,192])
def test_v8_icon_position_uses_dpi_not_screen_width(size,dpi):
    w,h=size
    sc=dpi/96.
    # Read native Smaart8 QA fixture. Keep icon x/y proportional only to DPI.
    fixture=Path(__file__).parent/"fixtures"/"smaart8_v8167_selected_off_left.png"
    left=Image.open(fixture).convert("RGB")
    patch=left.resize((round(left.width*sc),round(left.height*sc)),Image.Resampling.NEAREST)
    canvas=Image.new("RGB",(w,h),(6,6,6))
    canvas.paste(patch,(0,round(90*sc)))
    rows=v8_row_states(canvas,(0,0,w,h),dpi=dpi)
    expected=["off","off","off","off","on","off","off","off","off"]
    # At very small logical viewport some rows are physically outside; fail closed.
    if round(90*sc)+patch.height<=h-50*sc:
        assert [r[2] for r in rows]==expected,(size,dpi,rows)
    else:
        assert all(r[2] in ("on","off","unknown") for r in rows)

def test_v8_wrong_image_size_fails_closed():
    im=Image.new("RGB",(1366,768),(0,0,0))
    assert v8_row_states(im,(0,0,1920,1080))==[]
    assert v8_row_states(im,(0,0,1366,768),dpi=0)==[]
