"""Read-only probe of original native chart title template matching."""
from PIL import ImageGrab
import numpy as np,win32gui
import plot_role_v812 as m
from plot_geometry_v7 import locate_plots
hwnd=win32gui.FindWindow(None,"Smaart Suite")
plots=locate_plots(hwnd)
image=ImageGrab.grab(all_screens=False)
a=m._read_mask(m.MAG_TEMPLATE)
b=m._read_mask(m.PHASE_TEMPLATE)
print("TEMPLATE_SHAPE_MAG",a.shape,"PHASE",b.shape,flush=True)
print("SCREEN",image.size,"PLOTS",plots,flush=True)
res=m.detect_plot_roles(image,plots.phase,plots.mag)
print("CURRENT_ROLE_SCORES",res,flush=True)
for name,rect in [("TOP",plots.phase),("BOTTOM",plots.mag)]:
    for tplname,tpl in [("MAG",a),("PHASE",b)]:
        scores=[]
        x,y,w,h=rect
        width=tpl.shape[1]
        for dy in range(-18,19,2):
            for dx in range(-35,36,3):
                yy=y+5+dy;xx=x+13+dx
                if yy<0 or xx<0:continue
                crop=image.crop((xx,yy,xx+width,yy+tpl.shape[0]))
                if crop.size!=(width,tpl.shape[0]):continue
                patch=m._mask(crop,width)
                scores.append((m._score_mask(tpl,patch),dx,dy))
        print("MATCH",name,tplname,"BEST",sorted(scores,reverse=True)[:6],flush=True)
