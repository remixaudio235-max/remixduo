"""Real physical 125/150% Windows DPI captures, no resampled/synthetic icons.
Read-only replay only; all images are authentic cropped native Data Bar photos.
"""
from pathlib import Path
import pytest
from PIL import Image
from smaart8_databar_v8121 import v8_row_states
from databar_icon_geometry_v8181 import classify_uia_row_gutter

HERE=Path(__file__).resolve().parent/"fixtures"
EXPECTED=["on","off","off","off","off","on","off","off","off"]

@pytest.mark.parametrize("dpi,scale",[(120,125),(144,150)])
@pytest.mark.parametrize("skin",["dark","light"])
def test_v8_real_physical_dpi_trace_identity(dpi,scale,skin):
    gutter=Image.open(HERE/f"v8184_v8_{scale}_{skin}_native_gutter.png").convert("RGB")
    full=Image.new("RGB",(1920,1080),(6,6,6))
    full.paste(gutter,(0,0))
    rows=v8_row_states(full,(0,0,1920,1080),dpi=dpi)
    assert len(rows)==9,(scale,skin,rows)
    assert [row[2] for row in rows]==EXPECTED,(scale,skin,rows)

def test_suite_real_150_dim_green_on_and_adjacent_off():
    image=Image.open(HERE/"v8184_suite_150_dim_green_3rows.png").convert("RGB")
    # Saved original native screenshot, row19 is a dim green ON document.
    assert classify_uia_row_gutter(image,33,25,34)=="on"
    assert classify_uia_row_gutter(image,0,25,34)=="off"
    assert classify_uia_row_gutter(image,66,25,34)=="off"

def test_suite_missing_glyph_remains_unknown():
    image=Image.new("RGB",(100,105),(8,8,8))
    assert classify_uia_row_gutter(image,33,25,34)=="unknown"
