from pathlib import Path
import numpy as np
from trf_core import read_trf,compute_sum
root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(root/"4,8 ms delay-1.trf");b=read_trf(root/"0 delay-1.trf")
for mag_smooth,phase_smooth in ((1/6,1/6),(1/6,1/12),(0,0)):
 d=compute_sum(a,b,4.8,False,.60,mag_smooth,phase_smooth)
 f=d.hz
 print("CASE",mag_smooth,phase_smooth,"TOTAL",len(f),"COH_GOOD",int(d.valid.sum()),"PHASE_GOOD",int(d.phase_valid.sum()))
 for lf,hf in ((20,20000),(54,154),(100,250),(250,650),(650,2000),(2000,20000)):
  roi=(f>=lf)&(f<=hf); n=int(roi.sum())
  low=int((roi&~d.valid).sum());lowphase=int((roi&~d.phase_valid).sum())
  print("ROI",lf,hf,"bins",n,"mag_quality_low",low,"phase_masked",lowphase,
        "coh_min",round(float(np.min(d.coherence[roi])),3) if n else None)
 for kind,lo,hi in (("mag",-80,-44),("mag",-21,15),("phase",439,799),("phase",-281,79)):
  y=d.mag_db-63.7 if kind=="mag" else (d.phase_deg-lo)%360+lo
  if kind=="mag" and lo==-21: y=d.mag_db
  inview=(y>=lo)&(y<=hi)
  print("RENDER",kind,lo,hi,"finite",int(np.isfinite(y).sum()),"within",int(inview.sum()),
        "outside",int((~inview).sum()),"quality low",int((~d.valid).sum()),
        "mask missing",int((~d.phase_valid).sum()) if kind=="phase" else 0)
 print("")
