# -*- coding: utf-8 -*-
"""V13 PEQ placement/gradient/read-only/12-filter regression."""
import math,time,hashlib
from types import SimpleNamespace
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage,QPainter
from mageq_visual_v13 import build_geometry,draw_mageq_details
from trf_core import read_trf
from engines.remix_autoeq_unified import AutoEQBand
from remix_autoeq_v05_adapter import design_remix_eq
from native_eq_mag_v06 import build_state,FitFrame
from smaart_native_mag_fit import fit_native_mag

DATA=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/4,8 ms delay-1.trf"
REF=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\V79_LIVE_SMAART_GUI.png")
def sample():
    tr=read_trf(DATA)
    r=design_remix_eq(tr.hz,tr.h,tr.coherence,fs=48000,
        target="House",filters=8,lf=60,hf=8000,boost=2,cut=-9,source=DATA.stem)
    assert r.status=="PREVIEW_READY"
    s=build_state(tr.hz,tr.h,tr.coherence,r.peqs,fs=48000,
                  source_index=0,source_name=DATA.stem,revision=7)
    im=Image.open(REF);rect=(252,553,1442,398)
    fit=fit_native_mag(im,rect,(0,0,im.width,im.height),
             s.freqs,s.original_db,s.coh,trace_color="cyan")
    assert fit.accepted
    return tr,s,FitFrame(7,rect,fit,"cyan",time.monotonic())

def test_all_marker_centers_exact_mag_eq_y_and_4_peq():
    tr,s,frame=sample()
    sha=hashlib.sha256(DATA.read_bytes()).hexdigest()
    geo=build_geometry(s,frame)
    assert len(geo.markers)==len(s.peqs) and 1<=len(s.peqs)<=8
    assert all(3<=b.q<=8 for b in s.peqs)
    assert len(geo.spans)>0
    for p,b in zip(geo.markers,s.peqs):
        assert p.visible and abs(p.frequency-b.f_hz)<1e-9
        # Coherence is display-only metadata. A marker remains usable even
        # when its local coherence indicator is low.
        assert isinstance(p.reliable,bool)
        expx=frame.plot[2]*math.log(p.frequency/20)/math.log(1000)
        expy=float(frame.fit.y(np.interp(math.log(p.frequency),
                                      np.log(s.freqs),s.after_db)))
        assert abs(p.x-expx)<1e-5 and abs(p.y-expy)<1e-5
    assert not s.after_db.flags.writeable
    assert hashlib.sha256(DATA.read_bytes()).hexdigest()==sha

def test_geometry_rejects_stale_viewport():
    _,s,frame=sample()
    with pytest.raises(ValueError,match="revision"):
        build_geometry(s,replace(frame,revision=frame.revision+1))
    with pytest.raises(ValueError,match="untrusted"):
        build_geometry(s,replace(frame,fit=replace(frame.fit,accepted=False)))

def test_dense_12_marker_layout_and_correction_gradient():
    tr,s,frame=sample()
    filters=tuple(SimpleNamespace(freq_hz=float(f),gain_db=float(1.4 if i%2==0 else -1.7),q=1.3)
           for i,f in enumerate(np.geomspace(75,5500,12)))
    src=build_state(tr.hz,tr.h,tr.coherence,filters,fs=48000,
              source_index=0,source_name=DATA.stem,revision=frame.revision)
    geo=build_geometry(src,frame)
    assert len(geo.markers)==12
    assert len(set(round(p.x,4) for p in geo.markers))==12
    assert any(p.visible for p in geo.markers)
    assert len(geo.spans)>0
    app=QApplication.instance() or QApplication([])
    img=QImage(frame.plot[2],frame.plot[3],QImage.Format.Format_ARGB32)
    img.fill(0)
    painter=QPainter(img)
    result=draw_mageq_details(painter,src,frame,geo)
    painter.end()
    assert result["peqs"]==12
    assert result["markers"]==sum(p.visible for p in geo.markers)
    assert result["gradient_spans"]>0
    assert result["labels"]<=12
    assert any(b.gain_db>0 for b in filters)
    assert any(b.gain_db<0 for b in filters)
    # Original input arrays/file never changed from drawing operations.
    assert np.array_equal(tr.h,read_trf(DATA).h)

def test_quality_gate_suppresses_gradient_but_numbers_remain_anchored():
    tr,s,frame=sample()
    s2=replace(s,coh=np.zeros_like(s.coh))
    geo=build_geometry(s2,frame)
    assert not geo.spans
    assert len(geo.markers)==len(s.peqs)
    assert all(not p.reliable for p in geo.markers if p.visible)
