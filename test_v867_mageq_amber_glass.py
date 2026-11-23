"""V8.67: contour-locked fill, safety gating and offline paint latency."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import time
import numpy as np
from PyQt6.QtGui import QImage,QPainter
from PyQt6.QtWidgets import QApplication
from mageq_visual_v13 import MagEqGeometry,CorrectionSpan,draw_gradient

def test_mageq_foreground_has_high_contrast_stroke_and_dark_halo():
    from mageq_visual_v13 import MAGEQ_LINE,MAGEQ_LINE_WIDTH,MAGEQ_HALO_WIDTH
    assert MAGEQ_LINE == "#FFE45C"
    assert MAGEQ_LINE_WIDTH >= 4.0
    assert MAGEQ_HALO_WIDTH >= MAGEQ_LINE_WIDTH + 2.0

def synthetic(height=320,delta=32.0):
    x=np.linspace(70,450,750)
    before=230 + 25*np.sin((x-70)/34)
    eq=before-delta*(.55+.45*np.sin((x-70)/70)**2)
    original=np.c_[x,before]
    after=np.c_[x,eq]
    return MagEqGeometry(after,original,np.ones(len(x),bool),
       (CorrectionSpan(tuple(range(len(x))),True),),(),
       (0,0,600,height),5)

def render(geo):
    img=QImage(600,320,QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter=QPainter(img)
    try:
        n=draw_gradient(painter,geo)
    finally:
        painter.end()
    return img,n

def test_gradient_moves_with_curves_and_keeps_zero_outside():
    app=QApplication.instance() or QApplication([])
    geo=synthetic()
    im,n=render(geo)
    assert n==1
    assert im.pixelColor(10,10).alpha()==0
    assert im.pixelColor(300,10).alpha()==0
    assert im.pixelColor(300,300).alpha()==0
    ind=int(np.argmin(abs(geo.after[:,0]-320)))
    y_eq=geo.after[ind,1]
    y_raw=geo.original[ind,1]
    y_near=round(y_eq+(y_raw-y_eq)*.08)
    y_far=round(y_eq+(y_raw-y_eq)*.9)
    assert im.pixelColor(320,y_near).alpha() > im.pixelColor(320,y_far).alpha()
    assert im.pixelColor(320,round((y_eq+y_raw)/2)).alpha()>0
    assert im.pixelColor(320,round(y_raw+5)).alpha()==0

def test_subtle_changes_are_lighter_and_disconnected_quality_is_not_filled():
    a,_=render(synthetic(delta=32))
    b,_=render(synthetic(delta=4))
    assert a.pixelColor(300,205).alpha()>=b.pixelColor(300,205).alpha()
    geo=synthetic()
    blocked=MagEqGeometry(geo.after,geo.original,np.zeros_like(geo.reliable),
                          (),geo.markers,geo.rect,geo.source_revision)
    blank,spans=render(blocked)
    assert spans==0 and blank.pixelColor(300,220).alpha()==0

def test_offline_paint_no_unbounded_cost_and_save_preview(tmp_path):
    app=QApplication.instance() or QApplication([])
    geo=synthetic()
    samples=[];wall=[]
    for _ in range(15):
        t=time.process_time();w=time.perf_counter()
        img,n=render(geo)
        samples.append((time.process_time()-t)*1000)
        wall.append((time.perf_counter()-w)*1000)
        assert n==1
    p95=float(np.percentile(samples,95))
    wall_p95=float(np.percentile(wall,95))
    print(f"V867 gradient 600x320, 750 points, 15 frames: "
          f"CPU P95 {p95:.2f}ms; wall P95 {wall_p95:.2f}ms")
    # CPU cost is the renderer invariant. Wall-clock spikes on this shared QA
    # host include scheduler stalls from Smaart/overlay and are recorded, not
    # misreported as QPainter work.
    assert p95<33.33
    assert img.save(str(tmp_path/"V867_AMBERGLASS_OFFSCREEN.png"))
