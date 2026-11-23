"""R58 regression: native Smaart8 compact geometry, real pixels, no shortcuts."""
from pathlib import Path
import pytest
from PIL import Image
from smaart8_plot_profile_v868 import (detect_v8_profile,
    _compact_native_profile_candidates,detect_v8_roles)

ROOT=Path(__file__).resolve().parent
NATIVE=ROOT/"fixtures"/"r58_v8_compact_titles_1366.png"

def test_r58_real_native_1366x720_both_headers():
    im=Image.open(NATIVE).convert("RGB")
    assert im.size==(1366,720)
    phase,mag=detect_v8_profile(im)
    assert phase==(215,87,920,257)
    assert mag==(215,368,920,257)
    assert detect_v8_roles(im,phase,mag)=="PHASE_TOP"

@pytest.mark.parametrize("w,h",[
    (1366,720),(1376,712),(1600,852),(1280,672),
])
def test_r58_compact_candidate_is_inside_window(w,h):
    rects=_compact_native_profile_candidates(w,h)
    assert rects
    for phase,mag in rects:
        for x,y,width,height in (phase,mag):
            assert 0<x<x+width<w
            assert 0<y<y+height<=h
        assert mag[1]>=phase[1]+phase[3]

@pytest.mark.parametrize("w,h",[(900,580),(1920,1032),(2560,1440)])
def test_r58_out_of_scope_never_uses_compact_guess(w,h):
    assert _compact_native_profile_candidates(w,h)==()

def test_r58_blank_native_cannot_falsely_authorize_a_plot():
    blank=Image.new("RGB",(1366,720),(12,12,12))
    assert detect_v8_profile(blank) is None
