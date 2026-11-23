import numpy as np,win32gui
from pathlib import Path
from trf_core import read_trf,compute_sum,matched
from tf_display_smoothing import smooth_phase_unit_phasor
from phase_axis_absolute_v79 import capture_fit,_colored_traces,_dilate_9
from full_scan_v7 import printwindow_image
from plot_geometry_v7 import locate_plots
h=win32gui.FindWindow(None,'Smaart Suite')
geo=locate_plots(h)
x,y,w,hh=geo.phase
wl,wt,_,_=win32gui.GetWindowRect(h)
im=printwindow_image(h)
mask=_dilate_9(_colored_traces(im.crop((x-wl,y-wt,x-wl+w,y-wt+hh)),w,hh))
folder=Path.home()/'Documents/Smaart Suite/Data/Transfer Function/Session Data'
a=read_trf(folder/'4,8 ms delay-1.trf')
b=read_trf(folder/'0 delay-1.trf')
fit=capture_fit(h,geo.phase,a,b,center_top=121)
f,hr,h2,coh=matched(a,b)
ref_deg,good,_=smooth_phase_unit_phasor(f,hr,coh,1/6,coh_gate=.6)
summed=compute_sum(a,b,delay_ms=4.8,phase_oct=1/6,mag_oct=1/6)
for label,deg in [('REF',ref_deg),('SUM',summed.phase_deg)]:
    xx=np.rint(w*np.log(np.maximum(f,1)/20)/np.log(1000)).astype(int)
    yy=np.rint(((fit.top_deg-deg)%360)*hh/360).astype(int)
    v=good&(f>=54)&(f<=200)&(xx>40)&(xx<w-340)&(yy>=1)&(yy<hh-1)
    hits=mask[yy[v],xx[v]]
    print('NATIVE_ABS_AXIS',fit,'TEST',label,'FREQ_BINS',v.sum(),'NATIVE_NATIVE_CURVE_HITS',round(hits.mean(),3))
    for sample in [60,70,80,90,100,120,160,190]:
        k=int(np.argmin(np.abs(f-sample)))
        print(' Hz',round(float(f[k]),1),'phase',round(float(deg[k]),1),'Y_PIXEL',round(float(y+yy[k]),1),'COLOR_HIT',bool(mask[yy[k],xx[k]]) if 1<=yy[k]<hh and 1<=xx[k]<w else None)
