import numpy as np
from pathlib import Path
from trf_core import read_trf,matched,auto_align,compute_sum,phase_match_percent
P=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(P/"4,8 ms delay-1.trf")
b=read_trf(P/"0 delay-1.trf")
res=auto_align(a,b,lf=60,hf=527.2,max_delay_ms=180)
f,h1,h2,c=matched(a,b)
print("PAIR",a.name,b.name,"FILES",a.path.name,b.path.name)
print("FREQ_RANGE",f.min(),f.max(),"POINTS",len(f))
print("TOP",[(q.delay_ms,q.invert_trace2,q.score_db,q.roi_bins) for q in res])
for delay,invert in [(0.,False),(4.8,False),(-4.8,False),(4.8,True),(res[0].delay_ms,res[0].invert_trace2)]:
 h2_corr=h2*np.exp(-2j*np.pi*f*delay/1000)*(-1 if invert else 1)
 hsum=h1+h2_corr
 roi=(f>=60)&(f<=527.2)&(c>=.6)
 outside=(f>527.2)&(f<=16000)&(c>=.6)
 def circular_stats(mask):
  if not mask.any():return None
  delta=np.angle(h2_corr[mask]*np.conj(h1[mask]),deg=True)
  err=np.angle(hsum[mask]*np.conj(h1[mask]),deg=True)
  w=c[mask]**2
  def stats(x):
   return dict(mean_abs=float(np.average(np.abs(x),weights=w)),rms=float(np.sqrt(np.average(x*x,weights=w))),p95=float(np.percentile(np.abs(x),95)),max=float(np.max(np.abs(x))))
  return dict(n=int(mask.sum()),phase2_vs_ref=stats(delta),sum_vs_ref=stats(err),circular_score=phase_match_percent(a,b,delay_ms=delay,invert_trace2=invert,lf=60,hf=527.2)[0])
 print("DELAY",delay,"INVERT",invert,"ROI",circular_stats(roi),"OUT",circular_stats(outside))
# assess file content consistency with nominal delay phase relation and gain
roi=(f>=60)&(f<=527.2)&(c>=.6)
ratio=np.abs(h2[roi])/np.abs(h1[roi])
print("MAG_B_A_DB",np.percentile(20*np.log10(ratio),[0,5,50,95,100]))
# Wrap behaviors in Smaart graph -105..255 vs model phase
s=compute_sum(a,b,delay_ms=4.8,phase_oct=1/6,mag_oct=1/6)
v=(s.hz>=60)&(s.hz<=527.2)&s.phase_valid
orig_phase=np.angle(h1[v],deg=True)
sum_phase=s.phase_deg[v]
circ_diff=np.angle(np.exp(1j*np.deg2rad(sum_phase-orig_phase)),deg=True)
print("SMOOTH_SUM_VS_RAW_REFERENCE",len(circ_diff),
      "absmean",np.mean(np.abs(circ_diff)),"p95",np.percentile(np.abs(circ_diff),95))
