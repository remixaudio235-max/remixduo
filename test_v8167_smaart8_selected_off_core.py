"""Smaart 8 native-verified selected-row white X, no guessed state.

Fixtures are small left-gutter crops from actual Smaart 8 v8.5.2.1
before/after clicking SUB SKY 2.trf; no audio source / generator involvement.
"""
from pathlib import Path
from PIL import Image, ImageDraw
from smaart8_databar_v8121 import v8_row_states
from selection_v7 import scan_icon_white_cross

HERE=Path(__file__).resolve().parent/"fixtures"
RECT=(0,0,1920,1032)
ON=["off","off","off","off","on","off","off","on","off"]
OFF=["off","off","off","off","on","off","off","off","off"]


def screenshot(side):
    left=Image.open(HERE/("smaart8_v8167_selected_"+side+"_left.png"))
    assert left.size==(100,228)
    canvas=Image.new("RGB",(1920,1032),(6,6,6))
    canvas.paste(left,(0,90))
    return canvas


def test_selected_bright_row_does_not_erase_checked_icon():
    image=screenshot("on")
    rows=v8_row_states(image,RECT)
    assert [state for _,_,state in rows]==ON
    assert len(rows)==9


def test_selected_row_does_not_dilute_off_white_cross():
    image=screenshot("off")
    rows=v8_row_states(image,RECT)
    assert [state for _,_,state in rows]==OFF
    assert len(rows)==9
    # The broad selected-row crop was historically UNKNOWN; on some
    # native snapshots it correctly detects OFF instead. Either is safe,
    # but it must NEVER claim ON. The production v8 reader must prove
    # OFF from the document-icon core regardless of the row highlight.
    top,bottom,state=rows[7]
    assert state=="off"
    assert scan_icon_white_cross(image,(20,top,50,bottom)) in ("unknown","off")
    assert scan_icon_white_cross(image,(27,top,41,bottom))=="off"


def test_missing_selected_glyph_fails_closed_not_off():
    image=screenshot("off")
    # The rest of selected-row highlight remains, but the icon is absent.
    ImageDraw.Draw(image).rectangle((27,264,40,285),fill=(40,45,50))
    rows=v8_row_states(image,RECT)
    assert len(rows)==9
    assert rows[7][2]=="unknown"
    assert rows[4][2]=="on"
