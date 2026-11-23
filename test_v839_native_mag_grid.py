"""V8.39: native Smaart 0dB/grid calibration independent of TF source."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
import pytest
import mag_sum_native_v826 as native
from smaart_native_y_grid_v839 import fit_native_mag_grid,saved_mag_grid_interval

ROOT=Path(__file__).parent
RECT=(252,539,1442,412)
WINDOW=(0,0,1920,1080)


def test_saved_live_smaart_zero_db_grid_measured_without_trace():
    img=Image.open(ROOT/"QA_V837_LIVE_AFTER_SCREEN.png")
    grid=fit_native_mag_grid(img,RECT,WINDOW,3.)
    assert grid.accepted,grid.reason
    assert grid.confidence>=.8
    assert abs(grid.zero_px-171.)<=1.
    assert abs(grid.grid_step_px-34.5)<1.
    assert abs(grid.y_max-14.87)<.3
    assert abs(grid.y_min+20.96)<.3
    assert abs((grid.y_max-grid.y_min)-35.83)<.5


def build_grid(*,zero=True,interference=False):
    im=Image.new("RGB",(1920,1080),"black")
    draw=ImageDraw.Draw(im)
    x,y,w,h=RECT
    z=171
    for k in range(-7,9):
        yy=y+z+round(k*34.5)
        if y+8<=yy<y+h-8:
            draw.line((x+72,yy,x+w-120,yy),fill=(18,19,21),width=1)
    if zero:
        draw.line((x+72,y+z,x+w-120,y+z),fill=(255,255,255),width=1)
    if interference:
        draw.line((x+72,y+z+55,x+w-120,y+z+55),fill=(255,255,255),width=1)
    return im


def test_grid_calibration_works_without_any_trace_pixels():
    grid=fit_native_mag_grid(build_grid(),RECT,WINDOW,3.)
    assert grid.accepted,grid.reason
    assert 10.<grid.px_per_db<12.1


@pytest.mark.parametrize("zero,interference",[(False,False),(True,True)])
def test_grid_rejects_missing_or_ambiguous_zero_baseline(zero,interference):
    grid=fit_native_mag_grid(build_grid(zero=zero,interference=interference),
                             RECT,WINDOW,3.)
    assert not grid.accepted


def test_grid_rejects_unknown_saved_interval():
    assert not fit_native_mag_grid(build_grid(),RECT,WINDOW,None).accepted


def test_grid_priority_over_unmatched_source(monkeypatch):
    im=build_grid()
    monkeypatch.setattr(native,"capture_native_window",lambda hwnd:(im,WINDOW))
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:3.)
    def forbidden_curve_match(*args):
        raise AssertionError("Cannot require a matching TF source for Y")
    monkeypatch.setattr(native,"axis_from_native_image",forbidden_curve_match)
    out=native.capture_sum_mag_axis(1234,RECT,())
    assert out.accepted and out.source_index==-1 and out.color=="GRID"
    assert out.score>=.8


def test_grid_falls_back_to_original_match_only_if_grid_fails(monkeypatch):
    im=build_grid(zero=False)
    monkeypatch.setattr(native,"capture_native_window",lambda hwnd:(im,WINDOW))
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:3.)
    fallback=native.SumMagAxis(True,-20.,16.,.90,0,"magenta","legacy",100)
    monkeypatch.setattr(native,"axis_from_native_image",lambda *args:fallback)
    assert native.capture_sum_mag_axis(123,RECT,("a","b")) is fallback
