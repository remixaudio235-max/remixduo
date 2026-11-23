"""QA: 114-379 Hz phase optimizer cross-check on complete 20-20k response."""
from pathlib import Path
from itertools import product
import numpy as np
from scipy.signal import freqz
from trf_core import read_trf
from remix_duo.core.filters import _smoothed_db,design_phase_only_fir
from remix_duo.core.fir_preview import phase_excess_rms

p=Path.home()/'Documents'/'Smaart Suite'/'Data'/'Transfer Function'/'Session Data'/'TUNNINNGGG-4.trf'
tr=read_trf(p);f=tr.hz;h=tr.h;c=tr.coherence
fs=48000;lf=114;hf=379
v=(f>=lf)&(f<=hf)&(c>=.75)&(abs(h)>1e-8)
x=f[v];y=np.unwrap(np.angle(h[v]));weights=np.maximum(c[v],.75)
co=np.polyfit(x,y,1,w=weights);ex=y-np.polyval(co,x)
ctrl=np.geomspace(x[0],x[-1],192)
raw=np.interp(np.log(ctrl),np.log(x),ex)
smooth={oct:_smoothed_db(ctrl,raw,octave=oct) for oct in (1/6,1/12,1/18,1/24,1/36)}
result=[]
taps=4096;nfft=2**int(np.ceil(np.log2(taps*8)))
freq=np.fft.rfftfreq(nfft,1/fs);safe=np.maximum(freq,1e-9);delay=(taps-1)/(2*fs)
for octave,taper,beta,scale in product(smooth,(1/3,1/6,1/12,1/24),(3,4,5,6,7),(0.6,0.8,1.0,1.2)):
    # Wider low-frequency correction requires longer tap, centered delay.
    phase=np.interp(np.log(safe),np.log(ctrl),-smooth[octave])*scale
    phase=np.clip(phase,-np.deg2rad(90),np.deg2rad(90))
    taper_weight=np.clip(np.log2(safe/lf)/taper,0,1)*np.clip(np.log2(hf/safe)/taper,0,1)
    phase*=taper_weight;phase[0]=0;phase[-1]=0
    desired=np.exp(1j*(phase-2*np.pi*freq*delay))
    desired[0]=desired[0].real;desired[-1]=desired[-1].real
    k=np.fft.irfft(desired,nfft)[:taps]*np.kaiser(taps,beta)
    r=np.fft.rfft(k,nfft)
    mag=20*np.log10(np.maximum(abs(r),1e-12))
    inband=(freq>=lf)&(freq<=hf)
    full=(freq>=20)&(freq<=20000)
    mx_in=float(np.max(abs(mag[inband])))
    mx_full=float(np.max(abs(mag[full])))
    if mx_in>1.5 or mx_full>1.5:continue
    before,after,impr,bins=phase_excess_rms(f,h,c,k,fs,lf,hf)
    center=taps//2
    early=float(np.sum(k[:center-int(.005*fs)]**2)/np.sum(k*k))
    # Build-time response magnitude + delay are physical quantities.
    result.append((round(after,3),round(impr,2),round(mx_in,3),
                   round(mx_full,3),round(early,5),octave,taper,beta,scale))
print('TOTAL_SAFE_CANDIDATES',len(result))
for z in sorted(result)[:18]:print('OPT',z)
for tap in (1024,2048,4096):
    original=design_phase_only_fir(f,h,c,taps=tap,fs=fs,lf=lf,hf=hf)
    N=2**int(np.ceil(np.log2(tap*8)));ff=np.fft.rfftfreq(N,1/fs)
    aa=20*np.log10(np.maximum(abs(np.fft.rfft(original.taps,N)),1e-12))
    print('BASELINE',tap,'RMS',phase_excess_rms(f,h,c,original.taps,fs,lf,hf)[1],
          'MAX_IN_DB',np.max(abs(aa[(ff>=lf)&(ff<=hf)])),
          'MAX_FULL_DB',np.max(abs(aa[(ff>=20)&(ff<=20000)])))
