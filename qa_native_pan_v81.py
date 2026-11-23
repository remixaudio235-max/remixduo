from PIL import Image
from pathlib import Path
import numpy as np,time
from native_fast_pan_v81 import colored_profiles,infer_pan,best_vertical_shift
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_8_PASSIVE_Y_QA\V78_NATIVE_PHASE_AXES.png')
im=np.asarray(Image.open(p).convert('RGB'))
# Native screenshot is full plot. fast crop is internal 65..900
off=150;width=800
roi=im[:,off:off+width].copy()
a,n=colored_profiles(Image.fromarray(roi))
print('SOURCE_PIXELS',n,'SRC_SHAPE',roi.shape,flush=True)
for dy in (-75,-41,-18,-4,0,6,21,52,78):
 out=np.zeros_like(roi)
 if dy>0:out[dy:]=roi[:-dy]
 elif dy<0:out[:dy]=roi[-dy:]
 else:out[:]=roi
 b,n1=colored_profiles(Image.fromarray(out))
 t=time.perf_counter()
 result=infer_pan(a,b)
 elapsed=(time.perf_counter()-t)*1000
 print('MOVE',dy,'RESULT',result,'ms',round(elapsed,1),flush=True)
 assert result.valid and abs(result.delta_px-dy)<=2,(dy,result)
print('FAST_PAN_SYNTH_ALL_PASS')
