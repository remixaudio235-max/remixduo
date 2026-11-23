"""R64 physical 1680x1050 display / 1680x1002-1004 native workarea regression.
All input comes from actual installed R63 screenshots and saved Smaart8 TRFs.
No GUI, generator, audio hardware, or guessed source-axis values."""
from pathlib import Path
import pytest
import numpy as np
from PIL import Image
from smaart8_plot_profile_v868 import detect_v8_profile,detect_v8_roles
from mag_sum_native_v826 import _smaart8_native_source_axis
from smaart_runtime_paths_v868 import trace_directory
from trf_core import read_trf

ROOT=Path(r"D:\R63_SMAART_UNICODE_QA\R63_LIVE_FULL_QA")
FRAME=ROOT/"V8_RESOLUTION_SUM_MATRIX"/"1680x1050_R63_V8_2TRACE.png"
EXPECTED=((215,81,1234,405),(215,508,1234,405))

def source_pair():
    folder=trace_directory(8)
    files=[folder/name for name in ("full 30 bien.trf","SUB SKY 2.trf")]
    if not all(f.is_file() for f in files):pytest.skip("Original Smaart8 source pair unavailable")
    return [read_trf(f) for f in files]

@pytest.mark.parametrize("native_window_height",[1002,1003,1004,1050])
def test_r64_physical_smaart8_workarea_title_verified(native_window_height):
    if not FRAME.is_file():pytest.skip("R63 physical 1680 screenshot missing")
    im=Image.open(FRAME).crop((0,0,1680,native_window_height))
    assert detect_v8_roles(im,*EXPECTED)=="PHASE_TOP"
    assert detect_v8_profile(im)==EXPECTED

@pytest.mark.parametrize("native_window_height",[1002,1003,1004,1050])
def test_r64_native_y_uses_real_pixels_with_taskbar(native_window_height):
    if not FRAME.is_file():pytest.skip("R63 physical 1680 screenshot missing")
    im=Image.open(FRAME).crop((0,0,1680,native_window_height))
    pair=source_pair()
    _,mag=detect_v8_profile(im)
    proof=_smaart8_native_source_axis(im,mag,(0,0,1680,native_window_height),pair)
    assert proof.accepted,proof.reason
    assert proof.source_index==0 and proof.color=="green"
    assert proof.score>=0.9
    assert proof.x_min==20 and proof.x_max==20000
    assert -23<proof.y_min<-15 and 15<proof.y_max<24
    # A mismatched or duplicate pair cannot be assigned this Y proof.
    wrong=_smaart8_native_source_axis(im,mag,(0,0,1680,native_window_height),[pair[1],pair[1]])
    assert not wrong.accepted

def test_r64_titleless_image_does_not_authorize_geometry():
    blank=Image.new("RGB",(1680,1003),(12,12,12))
    assert detect_v8_profile(blank) is None

def test_r64_prior_1366_native_window_positive_unchanged():
    # This original PrintWindow source has native titles unobscured by Duo;
    # full desktop screenshots can have Duo overlays covering title glyphs.
    p=Path(r"D:\R59_SMAART8_TOP_RIGHT_DOCK_QA\R60_NATIVE_SMAART8_READONLY.png")
    if not p.is_file():pytest.skip("Original 1366 native PrintWindow frame unavailable")
    im=Image.open(p)
    assert detect_v8_profile(im)==((215,87,920,257),(215,368,920,257))

@pytest.mark.parametrize("resolution",["1366x768","1600x900","1440x900"])
def test_r64_other_overlay_obscured_native_titles_remain_fail_closed(resolution):
    # R63 full desktop screenshot has Duo overlay over the source title:
    # source geometry must NOT be invented from a partly obscured image.
    p=ROOT/"V8_RESOLUTION_SUM_MATRIX"/f"{resolution}_R63_V8_2TRACE.png"
    if not p.is_file():pytest.skip("R63 other resolution evidence missing")
    assert detect_v8_profile(Image.open(p)) is None
