import win32gui
from pywinauto import Desktop
h=win32gui.FindWindow(None,"Smaart Suite")
root=Desktop(backend="uia").window(handle=h)
r=root.rectangle()
print('ROOT',r.left,r.top,r.right,r.bottom)
for control in root.descendants(control_type='Custom'):
    s=control.rectangle()
    w,t=s.width(),s.height()
    if w>850 and t>190:
        print('PLOT_CANDIDATE',s.left,s.top,s.right,s.bottom,'WH',w,t,'NAME',repr(control.element_info.name))
