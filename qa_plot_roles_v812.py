from pathlib import Path
from PIL import Image
import numpy as np
from plot_geometry_v7 import locate_plots
from plot_role_v812 import detect_plot_roles,locate_role_plots
import win32gui
im=Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_11_AUTO_SMOOTH_COMPACT_QA\V812_BASE_SMAART_SCREEN.png").convert("RGB")
h=win32gui.FindWindow(None,"Smaart Suite")
bounds=locate_plots(h)
top,bot=bounds.phase,bounds.mag
scores=detect_plot_roles(im,top,bot)
print("CURRENT_MAG_UPPER",scores,flush=True)
assert scores.role=="MAG_TOP" and scores.confidence>.95
# If Smaart is actually in foreground, validate native screenshot.
# Never bring Smaart to foreground behind the user's back.
if win32gui.GetForegroundWindow()==h:
 live=locate_role_plots(h)
 print("LIVE",live,flush=True)
 assert live is not None and live.mag[1]<live.phase[1]
else:
 print("LIVE_NOT_FOREGROUND_SKIP_USER_SESSION_UNDISTURBED")
a=np.array(im.copy(),copy=True)
top_y,bot_y=top[1],bot[1]
height=30;x=top[0];width=120
temp=a[top_y:top_y+height,x:x+width].copy()
a[top_y:top_y+height,x:x+width]=a[bot_y:bot_y+height,x:x+width]
a[bot_y:bot_y+height,x:x+width]=temp
flipped=Image.fromarray(a)
flipped.save("V812_REVERSED_LAYOUT_SYNTHETIC.png")
swapped=detect_plot_roles(flipped,top,bot)
print("SWAPPED_PHASE_UPPER",swapped,flush=True)
assert swapped.role=="PHASE_TOP" and swapped.confidence>.9
a[top_y:top_y+height,x:x+width]=[0,0,0]
a[bot_y:bot_y+height,x:x+width]=[0,0,0]
missing=detect_plot_roles(Image.fromarray(a),top,bot)
print("NO_TITLES",missing,flush=True)
assert missing.role=="UNKNOWN"
print("V812_TITLE_ROLE_DETECTION_QA_PASS",flush=True)
