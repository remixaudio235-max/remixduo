# -*- coding: utf-8 -*-
"""Source-backed V0.6 MAG overlay registration and safety tests."""
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from native_eq_mag_v06 import build_state,native_fit_worker
from smaart_native_mag_fit import native_points,fit_native_mag
from smaart_eq_color_select import choose_color_fit

DATA=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
OLD=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\V79_LIVE_SMAART_GUI.png")
def qa_source():
 t=read_trf(DATA/"4,8 ms delay-1.trf")
 result=design_remix_eq(t.hz,t.h,t.coherence,fs=48000,
          target="House",filters=8,lf=60,hf=8000,boost=2,cut=-9,
          source="T1")
 assert result.status=="PREVIEW_READY" and 1<=len(result.peqs)<=8
 assert all(3<=b.q<=8 for b in result.peqs)
 s=build_state(t.hz,t.h,t.coherence,result.peqs,fs=48000,
              source_index=0,source_name="T1",revision=9)
 return result,s

def test_corrected_native_mag_uses_real_biquad_not_ui_curve():
    result,s=qa_source()
    delta=s.after_db-s.original_db
    assert np.min(delta)<-1.5
    assert np.max(np.abs(delta))<=9.01
    assert np.isfinite(s.after_db).all()
    assert result.rms_after<result.rms_before

def test_sum_fails_closed_until_viewport_identity_proven():
    result,s=qa_source()
    t=read_trf(DATA/"4,8 ms delay-1.trf")
    with pytest.raises(ValueError,match="SUM"):
        build_state(t.hz,t.h,t.coherence,result.peqs,
                    fs=48000,source_index=2,source_name="SUM",revision=10)
    with pytest.raises(ValueError,match="valid PEQ"):
        build_state(t.hz,t.h,t.coherence,(),fs=48000,
                    source_index=0,source_name="T1",revision=10)

def test_pixel_calibration_maps_corrected_db_to_actual_smaart_axis():
    result,s=qa_source()
    if not OLD.is_file():pytest.skip("Historical original Smaart screenshot missing")
    image=Image.open(OLD)
    rect=(252,553,1442,398)
    win=(0,0,image.width,image.height)
    fit=fit_native_mag(image,rect,win,s.freqs,s.original_db,s.coh,trace_color="cyan")
    assert fit.accepted
    before,trust=native_points(rect,fit,s.freqs,s.original_db,s.coh)
    after,_=native_points(rect,fit,s.freqs,s.after_db,s.coh)
    assert len(before)==len(after)
    assert np.allclose(before[:,0],after[:,0])
    valid=(s.freqs>=20)&(s.freqs<=20000)
    assert np.allclose(after[:,1]-before[:,1],
                       -(s.after_db-s.original_db)[valid]*fit.px_per_db,atol=.001)

def test_ambiguous_native_ref_color_scores_fail_closed(monkeypatch):
    from smaart_native_mag_fit import NativeMagFit
    import smaart_eq_color_select as selector
    _,s=qa_source()
    scores={"cyan":.89,"teal":.2,"blue":.87,"red":.3,"green":.2,"magenta":.2,"gold":.2}
    def fake_fit(img,rect,window,f,db,coh,*,trace_color,**_geometry):
        score=scores[trace_color]
        return NativeMagFit(200.,11.2,.0,score,.30,221,
                            score>.6,"QA synthetic overlap")
    monkeypatch.setattr(selector,"fit_native_mag",fake_fit)
    choice=selector.choose_color_fit(None,(252,553,1442,398),
                         (0,0,1920,1040),s.freqs,s.original_db,s.coh)
    assert choice is not None
    assert not choice.accepted
