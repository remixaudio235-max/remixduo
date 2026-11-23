"""R&D A/B, no production FIR edits or DSP exports: 114-379Hz measured TF."""
from pathlib import Path
from itertools import product
import numpy as np
from scipy.signal import freqz
from trf_core import read_trf
from remix_duo.core.filters import _smoothed_db,design_phase_only_fir
from remix_duo.core.fir_preview import phase_excess_rms
p=Path.home()/'Documents'/'Smaart Suite'/'Data'/'Transfer Function'/'Session Data'/'TUNNINNGGG-4.trf'
tr=read_trf(p); f=tr.hz;h=tr.h;c=tr.coherence
fs=48000;lf=114;hf=379
v=(f>=lf)&(f<=hf)&(c>=.75)&np.isfinite(c)&(abs(h)>1e-8)
x=f[v]; y=np.unwrap(np.angle(h[v])); weights=np.maximum(c[v],.75)
slope=np.polyfit(x,y,1,w=weights);excess=y-np.polyval(slope,x)
controls=np.geomspace(max(lf,x[0]),min(hf,x[-1]),192)
raw=np.interp(np.log(controls),np.log(x),excess)
smoothed={oct:_smoothed_db(controls,raw,octave=oct) for oct in (1/3,1/6,1/12,1/24,1/48)}
rows=[]
for taps in (1024,2048,4096):
 nfft=2**int(np.ceil(np.log2(taps*8)))
 freq=np.fft.rfftfreq(nfft,1/fs)
 safe=np.maximum(freq,1e-9)
 delay=(taps-1)/(2*fs)
 for oct,limit,taper,beta in product(smoothed,(75,120,180),(1/3,1/6,1/12), (5,7)):
  phase_target=np.interp(np.log(safe),np.log(controls),np.clip(-smoothed[oct],-np.deg2rad(limit),np.deg2rad(limit)))
  win=np.clip(np.log2(safe/lf)/taper,0,1)*np.clip(np.log2(hf/safe)/taper,0,1)
  des=phase_target*win;des[0]=0;des[-1]=0
  spec=np.exp(1j*(des-2*np.pi*freq*delay))
  spec[0]=spec[0].real;spec[-1]=spec[-1].real
  taps_array=np.fft.irfft(spec,nfft)[:taps]*np.kaiser(taps,beta)
  _,response=freqz(taps_array,worN=x,fs=fs)
  ripple=float(np.max(np.abs(20*np.log10(np.maximum(abs(response),1e-12)))))
  if ripple>1.5:continue
  before,after,impr,bins=phase_excess_rms(f,h,c,taps_array,fs,lf,hf)
  # pre energy of FIR before nominal mid point, relative to full FIR energy
  pre_ratio=float(np.sum(taps_array[:taps//2]**2)/max(np.sum(taps_array**2),1e-12))
  rows.append((round(after,3),round(impr,2),taps,round(ripple,3),str(round(oct,5)),limit,round(taper,5),beta,round(pre_ratio,3)))
 print('COMPLETED_TAPS',taps,'CANDIDATES',len(rows),flush=True)
print('BEST_SAFE_PHASE_RMS',flush=True)
for row in sorted(rows)[:18]:print(row,flush=True)
print('BEST_1024',flush=True)
for row in sorted(row for row in rows if row[2]==1024)[:10]:print(row,flush=True)
for taps in (1024,2048,4096):
 base=design_phase_only_fir(f,h,c,taps=taps,fs=fs,lf=lf,hf=hf)
 print('BASELINE',taps,phase_excess_rms(f,h,c,base.taps,fs,lf,hf),flush=True)
