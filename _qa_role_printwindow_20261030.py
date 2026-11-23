"""Read-only Smaart source HWND capture vs desktop capture for role parity."""
import win32gui,numpy as np
from full_scan_v7 import printwindow_image
from plot_geometry_v7 import locate_plots
from plot_role_v812 import detect_plot_roles
hwnd=win32gui.FindWindow(None,"Smaart Suite")
rect=win32gui.GetWindowRect(hwnd)
plots=locate_plots(hwnd)
im=printwindow_image(hwnd)
print("WIN_RECT",rect,"IMAGE",im.size,"IMAGE_STD",round(float(np.array(im).std()),2),flush=True)
a=plots.phase;b=plots.mag
if rect[0] or rect[1]:
    a=(a[0]-rect[0],a[1]-rect[1],a[2],a[3])
    b=(b[0]-rect[0],b[1]-rect[1],b[2],b[3])
print("PRINTWINDOW_ROLE_SCORES",detect_plot_roles(im,a,b),flush=True)
