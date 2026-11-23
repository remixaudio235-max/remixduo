"""Read-only vertical Y-pan simulation from one captured native frame."""
from pathlib import Path
import win32gui
from PIL import Image,ImageDraw
from trf_core import read_trf
from plot_geometry_v7 import locate_plots
from smaart_native_mag_fit import capture_native_window
from mag_sum_native_v826 import axis_from_native_image
root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
traces=(read_trf(root/"0 delay-2.trf"),read_trf(root/"4,8 ms delay-1.trf"))
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd
plot=locate_plots(hwnd)
im,rect=capture_native_window(hwnd)
first=axis_from_native_image(im,plot.mag,rect,traces)
assert first.accepted and first.score>.9,first
x,y,w,h=plot.mag
l,t,*_=rect
x-=l;y-=t
shift=18
target=im.copy()
area=im.crop((x,y,x+w,y+h))
# Simulates a chart's pixel contents after an 18px Y translation.
black=Image.new("RGB",(w,h),(8,14,18))
black.paste(area.crop((0,0,w,h-shift)),(0,shift))
target.paste(black,(x,y))
second=axis_from_native_image(target,plot.mag,rect,traces)
print("AXIS_SCROLL_18PX",first,second,flush=True)
assert second.accepted and second.color==first.color,second
before=first.y_max-first.y_min
after=second.y_max-second.y_min
assert abs(before-after)<1.2,(before,after)
dy_px=(second.y_max-first.y_max)*h/before
assert abs(dy_px-shift)<4,(dy_px,shift)
print("NATIVE_MAG_Y_PAN_18PX_PASS",round(dy_px,2),flush=True)
