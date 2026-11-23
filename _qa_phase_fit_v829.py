from pathlib import Path
import sys,time
from PIL import Image
import win32gui
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p))
from trf_core import read_trf
from phase_axis_absolute_v79 import fit_ref_phase_axis,capture_fit
from fast_phase_y_v80 import capture_fit_fast
from plot_role_v812 import locate_role_plots
data=Path.home()/'Documents/Smaart Suite/Data/Transfer Function/Session Data'
traces=[read_trf(data/name) for name in ('4,8 ms delay-1.trf','rrt-3.trf')]
phase=(252,112,1442,398)
for n in ('_qa_phase_gui_before.png','_qa_phase_gui_drag_down.png','_qa_phase_gui_restored.png'):
 image=Image.open(p/n).convert('RGB')
 for j in (0,1):
  fit=fit_ref_phase_axis(image,phase,(0,0,1920,1080),traces[j],traces[1-j],center_top=180.)
  print(n,j,fit,flush=True)
h=win32gui.FindWindow(None,'Smaart Suite')
phase=locate_role_plots(h).phase
for j in (0,1):
 t=time.perf_counter()
 fit=capture_fit(h,phase,traces[j],traces[1-j],center_top=180.)
 print('LIVE_PRINTWINDOW',j,fit,round((time.perf_counter()-t)*1000,1),flush=True)
t=time.perf_counter()
result=capture_fit_fast(h,phase,traces[0],traces[1],180.)
print('LIVE_FAST',result,'ELAPSED',round((time.perf_counter()-t)*1000,1),flush=True)
