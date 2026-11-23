import sys,numpy as np
from PIL import Image
from pathlib import Path
sys.path.insert(0,r"D:\R62_SMAART_NATIVE_1680_GEOMETRY_QA\src")
from smaart8_plot_profile_v868 import title_template,detect_v8_profile
arr=np.zeros((1050,1680,3),dtype=np.uint8);arr[:]=(10,10,10)
for y,role in ((81,"PHASE"),(508,"MAG")):
 tpl=title_template(role)
 th,tw=tpl.shape
 sub=arr[y+5:y+5+th,215+13:215+13+tw,:]
 sub[tpl]=255
im=Image.fromarray(arr)
print("SYNTH_PROFILE",detect_v8_profile(im),flush=True)
