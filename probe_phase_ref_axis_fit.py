from pathlib import Path
import numpy as np,win32gui

from full_scan_v7 import printwindow_image
from plot_geometry_v7 import locate_plots
from trf_core import read_trf,matched
from tf_display_smoothing import smooth_phase_unit_phasor
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
h=win32gui.FindWindow(None,"Smaart Suite")
geo=locate_plots(h)
wx,wy,_,_=win32gui.GetWindowRect(h)
x,y,w,hh=geo.phase
image=np.array(printwindow_image(h).convert("RGB"))[y-wy:y-wy+hh,x-wx:x-wx+w]
from PIL import Image
Image.fromarray(image).save("V78_NATIVE_PHASE_AXES.png")
r=image[:,:,0].astype(float);g=image[:,:,1].astype(float);b=image[:,:,2].astype(float)
mask=((b>75)&(b>r*1.45)&(b>g*.68))|((r>95)&(r>g*1.20)&(r>b*.85)&(g>30))
mask[:12]=0;mask[-3:]=0;mask[:,:35]=0;mask[:,w-330:]=0
print("MASK_PIXELS",int(mask.sum()),"PLOT",geo.phase)
dilate=mask.copy()
for dy in range(-4,5):
 for dx in range(-4,5):
  dilate[4:-4,4:-4] |= mask[4+dy:mask.shape[0]-4+dy,4+dx:mask.shape[1]-4+dx]
a=read_trf(p/"4,8 ms delay-1.trf")
bf=read_trf(p/"TUNNINNGGG-8.trf")
f,ha,hb,coh=matched(a,bf)
phase,valid,_=smooth_phase_unit_phasor(f,ha,coh,1/6,coh_gate=.60)
xx=np.rint(w*np.log(f/20)/np.log(1000)).astype(int)
good=(f>30)&(f<3500)&(xx>40)&(xx<w-340)&valid
xx=xx[good];ph=phase[good]
print("USABLE_REF_BINS",len(xx),"PHASE_REF_SAMPLES",[(round(z,1),round(p,1)) for z,p in zip(f[good][:20],ph[:20])])
assert len(xx)>80
out=[]
for top in np.arange(-50.,400.,1.):
    value=(ph-(top-360.))%360.+(top-360.)
    yy=np.rint((top-value)/360*hh).astype(int)
    ok=(yy>=1)&(yy<hh-1)
    vals=dilate[yy[ok],xx[ok]].astype(float)
    s=-np.mean(vals)
    near=np.mean(vals>0)
    out.append((float(s),float(near),top,len(vals)))
print("TOP_FITS_RANKED", sorted(out)[:15])
print("TOP_NEAR_RANKED",sorted(out,key=lambda z:-z[1])[:15])

print('BEST_NONLOCAL', sorted([z for z in out if abs(z[2]-117)>35])[:12])
print('MEDIAN_SCORE',np.median([z[1] for z in out]))
