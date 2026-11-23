"""V8.120: Duo dock on Smaart 8 sits below the real TF engine boxes.

Live 2026-11-12 (Smaart 8.5.2.1, 1920x1032): Smaart 8 exposes no UIA tree,
and the fixed 380/1040 anchor put the dock over the "TUNNING" engine box
(ends at y=412). Fixture: real PrintWindow frame, left of x=1700 blanked.
"""
from pathlib import Path
from PIL import Image,ImageDraw
from smaart8_native_sidebar_v870 import detect_v8_slot,v8_sidebar_rects,V8Slot

HOST=(0,0,1920,1032)
FIX=Path(__file__).with_name("fixtures")/"smaart8_sidebar_1engine_1920x1032.png"


def test_real_smaart8_frame_slot_below_engine_box():
    slot=detect_v8_slot(Image.open(FIX),HOST)
    assert slot is not None
    assert 414<=slot.top<=432          # engine box ends at y=412
    assert 790<=slot.bottom<=806       # dark separator above Signal Generator at ~806
    panel=v8_sidebar_rects(HOST,HOST,slot).panel
    assert panel[1]==slot.top and panel[1]+panel[3]<=slot.bottom
    old=v8_sidebar_rects(HOST,HOST).panel
    assert old[1]<412                  # the fixed anchor overlapped the engine box


def test_more_engine_boxes_push_the_slot_down():
    im=Image.open(FIX).convert("RGB")
    d=ImageDraw.Draw(im)
    for k in range(2):                  # two more engine boxes like TUNNING
        y=420+k*60
        d.rectangle((1735,y,1900,y+52),outline=(40,200,40),fill=(38,58,58))
        d.rectangle((1745,y+10,1800,y+20),fill=(200,200,200))
    slot=detect_v8_slot(im,HOST)
    assert slot is not None and slot.top>=420+60+52


def test_no_free_area_fails_closed():
    im=Image.open(FIX).convert("RGB")
    d=ImageDraw.Draw(im)
    for y in range(420,800,30):
        d.rectangle((1735,y,1900,y+20),fill=(160,160,160))
    assert detect_v8_slot(im,HOST) is None
    assert v8_sidebar_rects(HOST,HOST,None).panel[1]==round(380*1032/1040)


def test_slot_is_typed():
    assert isinstance(detect_v8_slot(Image.open(FIX),HOST),V8Slot)
