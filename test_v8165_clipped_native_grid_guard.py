"""V8.165: viewport clipping is NOT missing source; strict grid + source ID."""
from dataclasses import replace
import numpy as np
import pytest
from PIL import ImageDraw
import smaart_native_y_grid_v839 as grid_module
from smaart_native_y_grid_v839 import fit_native_mag_grid
import trace_offset_native_v8114 as offset_module
from trace_offset_native_v8114 import measure_trace_offsets
from tf_display_smoothing import smooth_log_octaves
from test_v839_native_mag_grid import build_grid,RECT,WINDOW
from test_v8114_trace_offset_native import trf,F


def synth(clipped=True,zero=True,magenta=True,green=True):
    image=build_grid(zero=zero)
    x,y,w,h=RECT
    hz=F
    log=np.log(hz)
    source_a=-4.+3*np.sin(log*1.7)
    if clipped:
        source_a-=25.*np.exp(-((np.log(hz/360.)/.45)**2))
    source_b=-5.+3*np.cos(log*2.3)
    ya=smooth_log_octaves(hz,source_a,1/6)
    yb=smooth_log_octaves(hz,source_b,1/6)
    grid=fit_native_mag_grid(image,RECT,WINDOW,3.) if zero else None
    if not zero:
        y_min,y_max=-20.96,14.87
    else:
        assert grid.accepted
        y_min,y_max=grid.y_min,grid.y_max
    d=ImageDraw.Draw(image)
    def paint(vals,offset,color):
        xx=x+w*np.log(hz/20.)/np.log(1000.)
        yy=y+(y_max-(vals+offset))/(y_max-y_min)*h
        d.line(list(zip(xx,yy)),fill=color,width=2)
    if green:paint(ya,-1.,(30,135,61))
    if magenta:paint(yb,-8.,(171,53,119))
    if zero:
        # Use the axis measured from this exact rendered frame. The
        # 0 dB lattice can shift one pixel when curves intersect gridlines.
        live=fit_native_mag_grid(image,RECT,WINDOW,3.)
        assert live.accepted
        y_min,y_max=live.y_min,live.y_max
    return image,(trf("A",source_a),trf("B",source_b)),(y_min,y_max)


@pytest.fixture(autouse=True)
def saved_smaart_interval(monkeypatch):
    monkeypatch.setattr(grid_module,"saved_mag_grid_interval",
                        lambda **kwargs:3.)


def test_native_clipped_source_recovers_from_grid_and_color(monkeypatch):
    image,traces,(lo,hi)=synth(clipped=True)
    # Force the green source through the clipped path. The legacy synthetic
    # painter can produce stronger lines than real Smaart screenshot pixels.
    legacy=offset_module.choose_color_fit
    calls=[0]
    def force_green_fallback(*args,**kw):
        calls[0]+=1
        return None if calls[0]==1 else legacy(*args,**kw)
    monkeypatch.setattr(offset_module,"choose_color_fit",force_green_fallback)
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo,hi,
                               smoothing_oct=1/6)
    assert out[0].offset_db==pytest.approx(-1.,abs=.5),out
    assert out[1].offset_db==pytest.approx(-8.,abs=.5),out
    assert out[0].color=="green" and out[1].color=="magenta"
    assert "clipped" in out[0].reason


@pytest.mark.parametrize("delta",[-11.,8.])
def test_grid_axis_mismatch_rejects_clipped_fallback(delta,monkeypatch):
    image,traces,(lo,hi)=synth()
    monkeypatch.setattr(offset_module,"choose_color_fit",
                        lambda *args,**kwargs:None)
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo+delta,hi+delta,
                               smoothing_oct=1/6)
    assert out[0].offset_db is None,out


def test_native_zero_baseline_missing_rejects_clipped_fallback(monkeypatch):
    image,traces,(lo,hi)=synth(zero=False)
    monkeypatch.setattr(offset_module,"choose_color_fit",
                        lambda *args,**kwargs:None)
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo,hi,
                               smoothing_oct=1/6)
    assert out[0].offset_db is None,out


def test_wrong_mag_smoothing_cannot_pass_source_clipping():
    image,traces,(lo,hi)=synth()
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo,hi,
                               smoothing_oct=1/24)
    assert all(item.offset_db is None for item in out) or all(
        "clipped" not in item.reason for item in out)


def test_missing_green_source_must_hold():
    image,traces,(lo,hi)=synth(green=False)
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo,hi,
                               smoothing_oct=1/6)
    assert out[0].offset_db is None,out


def test_wrong_source_shape_cannot_claim_green_curve():
    image,traces,(lo,hi)=synth()
    bad=trf("A",np.full(len(F),-2.)+3*np.cos(np.log(F)*3.7))
    out=measure_trace_offsets(image,RECT,WINDOW,(bad,traces[1]),lo,hi,
                               smoothing_oct=1/6)
    assert out[0].offset_db is None,out


def test_same_color_one_source_not_two_independent_matches():
    image,traces,(lo,hi)=synth(magenta=False)
    out=measure_trace_offsets(image,RECT,WINDOW,traces,lo,hi,
                               smoothing_oct=1/6)
    assert not all(item.offset_db is not None for item in out),out


def test_incorrect_viewport_coordinates_hold():
    image,traces,(lo,hi)=synth()
    out=measure_trace_offsets(image,
            (RECT[0]+150,RECT[1],RECT[2],RECT[3]),
            WINDOW,traces,lo,hi,smoothing_oct=1/6)
    assert out[0].offset_db is None,out
