"""V8.164 one-capture native-mask reuse, exact legacy score parity and fail closed."""
from PIL import Image
import numpy as np
import pytest
from smaart_native_mag_fit import NativeMagFrame,fit_native_mag
from test_v8114_trace_offset_native import (
    frame as make_image,shape,trf,PLOT,WIN,YMIN,YMAX,RED,TEAL,F)
from trace_offset_native_v8114 import measure_trace_offsets


def sample():
    a,b=shape(1),shape(2)
    image=make_image([(a,7.,RED),(b,0.,TEAL)])
    return image,a,b


@pytest.mark.parametrize("color,source",[( "red",0),("teal",1),("magenta",0)])
def test_cached_fit_has_exact_same_score_decision_and_geometry(color,source):
    im,a,b=sample()
    mag=(a,b)[source]
    t=trf("native",mag)
    baseline=fit_native_mag(im,PLOT,WIN,t.hz,mag,t.coherence,
                             trace_color=color)
    prepared=NativeMagFrame(im,PLOT,WIN)
    optimized=fit_native_mag(im,PLOT,WIN,t.hz,mag,t.coherence,
                              trace_color=color,frame=prepared)
    assert (optimized.accepted,optimized.bins,optimized.reason)==(
            baseline.accepted,baseline.bins,baseline.reason)
    for name in ("score","alternative_score","center_px",
                 "px_per_db","source_median_db"):
        assert getattr(optimized,name)==pytest.approx(getattr(baseline,name),
                                                       abs=1e-12)
    if optimized.accepted:
        assert np.array_equal(optimized.y(mag),baseline.y(mag))


def test_cache_stores_only_this_image_window_and_plot():
    im,a,b=sample()
    prepared=NativeMagFrame(im,PLOT,WIN)
    assert prepared.matches(im,PLOT,WIN)
    assert not prepared.matches(im.copy(),PLOT,WIN)
    assert not prepared.matches(im,(PLOT[0]+2,*PLOT[1:]),WIN)
    assert not prepared.matches(im,PLOT,(1,0,WIN[2],WIN[3]))
    t=trf("a",a)
    for wrong_image,wrong_plot,wrong_window in (
        (im.copy(),PLOT,WIN),
        (im,(PLOT[0]+2,*PLOT[1:]),WIN),
        (im,PLOT,(1,0,WIN[2],WIN[3]))):
        fail=fit_native_mag(wrong_image,wrong_plot,wrong_window,
                            t.hz,a,t.coherence,trace_color="red",
                            frame=prepared)
        assert not fail.accepted and "mismatch" in fail.reason.lower()


def test_prepared_frame_retains_required_250_pixels_and_color_separation():
    im,a,b=sample()
    prepared=NativeMagFrame(im,PLOT,WIN)
    assert "red" in prepared.visible_colors(["red","teal","magenta"])
    assert "teal" in prepared.visible_colors(["red","teal","magenta"])
    assert "magenta" not in prepared.visible_colors(["red","teal","magenta"])
    assert prepared.expanded("magenta") is None
    assert prepared.expanded("red") is prepared.expanded("red")


def test_two_trace_offsets_and_absent_trace_dont_turn_into_fake_pass():
    im,a,b=sample()
    good=measure_trace_offsets(im,PLOT,WIN,(trf("a",a),trf("b",b)),
                               YMIN,YMAX)
    assert good[0].offset_db==pytest.approx(7.,abs=.35)
    assert good[1].offset_db==pytest.approx(0.,abs=.35)
    missing=make_image([(b,0.,TEAL)])
    fail=measure_trace_offsets(missing,PLOT,WIN,
                               (trf("a",a),trf("b",b)),YMIN,YMAX)
    assert fail[0].offset_db is None
    assert fail[1].offset_db==pytest.approx(0.,abs=.35)


def test_cached_wrong_y_axis_still_rejected():
    im,a,b=sample()
    fail=measure_trace_offsets(im,PLOT,WIN,
                               (trf("a",a),trf("b",b)),-36.,36.)
    assert all(x.offset_db is None for x in fail)



@pytest.mark.parametrize("height,width,radius",[
    (1,1,0),(1,1,3),(1,7,3),(7,1,3),
    (5,5,1),(7,9,2),(20,14,3),(18,27,6),
    (440,1442,3)])
def test_separable_native_mask_expansion_exactly_matches_legacy_sum_area(
        height,width,radius):
    from smaart_native_mag_fit import expand
    rng=np.random.default_rng(height*10000+width*10+radius)
    mask=rng.random((height,width))<.05
    k=2*radius+1
    old=np.pad(mask.astype(np.int32),((radius,radius),(radius,radius)))
    sums=np.pad(old,((1,0),(1,0))).cumsum(axis=0).cumsum(axis=1)
    expected=(sums[k:,k:]-sums[:-k,k:]-sums[k:,:-k]+sums[:-k,:-k])>0
    assert np.array_equal(expand(mask,radius),expected)


def test_separable_mask_expansion_does_not_modify_input():
    from smaart_native_mag_fit import expand
    original=np.zeros((19,23),bool)
    original[12,11]=True
    previous=original.copy()
    out=expand(original,3)
    assert np.array_equal(original,previous)
    assert np.count_nonzero(out)==49
