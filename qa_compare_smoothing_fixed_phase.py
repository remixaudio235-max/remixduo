from pathlib import Path
import numpy as np
from trf_core import read_trf,matched,compute_sum
from tf_display_smoothing import smooth_phase_unit_phasor
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(folder/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
f,h1,h2,coh=matched(a,b)
for d in (4.8,0):
 sum_sm=compute_sum(a,b,delay_ms=d,phase_oct=1/6)
 ref_sm,ref_valid,ref_conc=smooth_phase_unit_phasor(f,h1,coh,1/6,coh_gate=.6)
 region=(f>=60)&(f<=527.2)&sum_sm.phase_valid&ref_valid
 diff=np.angle(np.exp(1j*np.deg2rad(sum_sm.phase_deg[region]-ref_sm[region])),deg=True)
 w=coh[region]**2
 print("DELAY",d,"BINS",region.sum(),"SMOOTHED_SUM_VS_SMOOTHED_REF",
       "mean_abs",np.average(np.abs(diff),weights=w),
       "rms",np.sqrt(np.average(diff*diff,weights=w)),
       "p95",np.percentile(np.abs(diff),95),
       "max",np.max(np.abs(diff)))
# evaluate magnitude gain relative to ref and physical 2-source phase sum, not display shifted
corr=h2*np.exp(-2j*np.pi*f*4.8/1000)
roi=(f>=60)&(f<=527.2)&(coh>=.6)
gain=20*np.log10(np.maximum(abs(h1[roi]+corr[roi]),1e-15)/np.maximum(abs(h1[roi]),1e-15))
print("SUM_GAIN_VS_REF_MEDIAN_DB",np.median(gain),"P5_P95",np.percentile(gain,[5,95]))
