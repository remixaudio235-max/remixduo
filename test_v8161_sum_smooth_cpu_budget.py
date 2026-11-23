"""V8.161: live-smoothed source proof and adaptive native pan work budget."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from tf_display_smoothing import smooth_log_octaves
from trace_offset_native_v8114 import measure_trace_offsets
from test_v8114_trace_offset_native import (
    shape, F, trf, frame, RED, TEAL, PLOT, WIN, YMIN, YMAX,
)
from overlay_v7 import _native_pan_min_interval

def test_native_sum_offset_fits_confirmed_1_6_smaart_smoothing():
    a,b=shape(1),shape(2)
    aa=smooth_log_octaves(F,a,1/6)
    bb=smooth_log_octaves(F,b,1/6)
    image=frame([(aa,5.0,RED),(bb,-2.0,TEAL)])
    result=measure_trace_offsets(image,PLOT,WIN,
                                 (trf("a",a),trf("b",b)),YMIN,YMAX,
                                 smoothing_oct=1/6)
    assert result[0].offset_db==pytest.approx(5.0,abs=.4),result
    assert result[1].offset_db==pytest.approx(-2.0,abs=.4),result
    assert result[0].color!=result[1].color

def test_unsupported_smoothing_fails_closed():
    a,b=shape(1),shape(2)
    image=frame([(a,0.,RED),(b,0.,TEAL)])
    out=measure_trace_offsets(image,PLOT,WIN,
                              (trf("a",a),trf("b",b)),YMIN,YMAX,
                              smoothing_oct=.137)
    assert len(out)==2 and all(x.offset_db is None for x in out)

@pytest.mark.parametrize("gesture",["phase","mag"])
def test_native_pan_stays_responsive_during_gesture(gesture):
    assert _native_pan_min_interval(gesture)==pytest.approx(.025)

def test_passive_pan_never_uses_40hz_capture_loop():
    assert .15<=_native_pan_min_interval(None)<=.25
