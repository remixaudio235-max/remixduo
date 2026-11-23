import time
from pathlib import Path
import win32api,win32con,win32gui
from full_scan_v7 import printwindow_image
from phase_axis_follow_v77 import native_blue_mask,detect_vertical_shift
from plot_geometry_v7 import locate_plots

root=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd,"Smaart missing"
win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
time.sleep(.2)
assert not win32gui.IsIconic(hwnd),"Smaart still minimized"
geometry=locate_plots(hwnd)
assert geometry
rect=geometry.phase
x=rect[0]-29
y=rect[1]+int(rect[3]*.48)
print("START",hwnd,"PLOT",rect,"DRAG",x,y,flush=True)
win32gui.SetForegroundWindow(hwnd)
time.sleep(.15)
screen_rect=win32gui.GetWindowRect(hwnd)
initial=printwindow_image(hwnd)
initial.save(root/"V77_BEFORE_NATIVE.png")
before=native_blue_mask(initial,rect,screen_rect)

def drag(start_y,end_y,steps=14):
    win32api.SetCursorPos((x,start_y))
    time.sleep(.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    time.sleep(.15)
    for i in range(1,steps+1):
        ny=round(start_y+(end_y-start_y)*i/steps)
        win32api.SetCursorPos((x,ny))
        time.sleep(.035)
    time.sleep(.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
    time.sleep(.38)

drag(y,y+33)
middle=printwindow_image(hwnd)
middle.save(root/"V77_MIDDLE_NATIVE.png")
observed=native_blue_mask(middle,rect,screen_rect)
pan=detect_vertical_shift(before,observed)
print("PAN_DOWN_NATIVE_OBSERVATION",pan,flush=True)
# Restore the original plot immediately by reversing the exact pointer movement.
drag(y+33,y)
last=printwindow_image(hwnd)
last.save(root/"V77_RESTORED_NATIVE.png")
restored=native_blue_mask(last,rect,screen_rect)
back=detect_vertical_shift(before,restored)
print("RESTORE_NATIVE_OBSERVATION",back,flush=True)
print("V77_REAL_DRAG_TEST_DONE",flush=True)
