from pathlib import Path
import numpy as np, time
from trf_core import read_trf,compute_sum,auto_align,TFTrace,synthetic
from tf_display_smoothing import smooth_phase_unit_phasor, smooth_log_octaves
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from overlay_v7 import SumGraph

folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(folder/"623.trf")
b=read_trf(folder/"TUNNING M-1.trf")
raw=compute_sum(a,b)
smoothed=compute_sum(a,b,mag_oct=1/6,phase_oct=1/6)
assert len(raw.hz)==len(smoothed.hz)==463
assert np.array_equal(raw.coherence,smoothed.coherence)
assert np.array_equal(raw.valid,smoothed.valid) or np.array_equal(raw.valid,smoothed.valid), "Unexpected coherence mask changes"
assert np.all(np.isfinite(smoothed.mag_db))
assert np.all(np.isfinite(smoothed.phase_deg))
assert smoothed.phase_valid is not None

def total_variation(y,mask):
    idx=np.where(mask)[0]
    neighbor=idx[np.diff(np.r_[idx[0]-2,idx])==1]
    return float(np.sum(np.abs(y[neighbor]-y[neighbor-1])))
in_band=(raw.hz>=100)&(raw.hz<=3000)
tv_raw=total_variation(raw.mag_db,in_band)
tv_smooth=total_variation(smoothed.mag_db,in_band)
assert tv_smooth < tv_raw * .87,(tv_smooth,tv_raw)
print("MAG_TV_REDUCTION_PERCENT",round((1-tv_smooth/tv_raw)*100,2))
print("PHASE_VALID",int(np.sum(smoothed.phase_valid)),"RAW_COH_VALID",int(np.sum(raw.valid)))
print("MAG_FREQ_BINS",len(smoothed.hz))

# The shortest circular mean of +179 and -179 degrees must be near 180, not 0.
f=np.geomspace(100,1000,64)
phase=np.radians(np.r_[np.repeat(179.,32),np.repeat(-179.,32)])
h=np.exp(1j*phase)
smooth,mask,conf=smooth_phase_unit_phasor(f,h,np.ones_like(f),1/3)
d=np.angle(np.exp(1j*np.radians(smooth[31:33]-180)),deg=True)
assert np.max(np.abs(d))<6,d
assert mask.all()
print("CIRCULAR_WRAP_PASS",smooth[31:33])

# Phase coherence-gate rejects untrustworthy points and prevents visual joins.
coh=np.ones_like(f)
coh[20:27]=0.02
smooth,mask,conf=smooth_phase_unit_phasor(f,h,coh,1/6,coh_gate=.6)
assert not mask[20:27].any()
assert np.all(np.isfinite(smooth))
print("PHASE_COH_GATE_PASS","masked",int(np.sum(~mask)))

# Option off must produce original unsmoothed response.
off=compute_sum(a,b,mag_oct=0,phase_oct=0)
assert np.allclose(raw.mag_db,off.mag_db,atol=1e-12)
assert np.allclose(raw.phase_deg,off.phase_deg,atol=1e-12)
print("RAW_ENGINE_UNCHANGED_PASS")

# Do not change Auto Align numerical candidates when smoothing UI changes.
candidates=auto_align(a,b,lf=60,hf=200)
assert candidates
print("SOLVER_UNMODIFIED", [(round(c.delay_ms,2),c.invert_trace2) for c in candidates[:2]])

app=QApplication([])
mag=SumGraph("mag")
mag.setGeometry(0,0,1200,400)
mag.y_min,mag.y_max=(-80,-44)
visible=smoothed.mag_db[(smoothed.hz>=20)&(smoothed.hz<=20000)]
mag.display_offset_db=round(-62-float(np.median(visible)),1)
mag.set_data(smoothed)
img=QImage(1200,400,QImage.Format.Format_ARGB32)
img.fill(0);mag.render(img)
assert mag._last_points>=250,mag._last_points
img.save("V72_SMOOTH_MAG_QA.png")
phase=SumGraph("phase")
phase.setGeometry(0,0,1200,400)
phase.y_min,phase.y_max=(-105,255)
phase.set_data(smoothed)
img2=QImage(1200,400,QImage.Format.Format_ARGB32)
img2.fill(0);phase.render(img2)
assert phase._last_points>40,phase._last_points
img2.save("V72_SMOOTH_PHASE_QA.png")
print("QT_RENDER_PASS","mag",mag._last_points,"phase",phase._last_points,
      "phase_segments",phase._last_segments)
t0=time.perf_counter()
for i in range(12):
    compute_sum(a,b,mag_oct=1/6,phase_oct=1/6)
print("SMOOTH_COMPUTE_AVG_MS",round((time.perf_counter()-t0)*1000/12,2))
