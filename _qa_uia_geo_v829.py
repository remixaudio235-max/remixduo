from pywinauto import Desktop
import win32gui
h=win32gui.FindWindow(None,'Smaart Suite')
root=Desktop(backend='uia').window(handle=h)
rect=root.rectangle()
print('SMAART',h,'RECT',rect,'DPI',rect.width(),rect.height())
for ctrl in root.descendants(control_type='Custom'):
 r=ctrl.rectangle()
 if r.width()>650 and r.height()>150:
  print('CUSTOM',(r.left,r.top,r.right,r.bottom),'WH',(r.width(),r.height()),repr(ctrl.element_info.name))
