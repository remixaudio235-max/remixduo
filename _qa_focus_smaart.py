import win32gui,win32api,win32con,ctypes,time
h=win32gui.FindWindow(None,"Smaart Suite")
f=win32gui.GetForegroundWindow()
print('BEFORE',f,h)
try:
 win32api.keybd_event(win32con.VK_MENU,0,0,0)
 time.sleep(.04)
 win32gui.SetForegroundWindow(h)
except Exception as exc:
 print('FAILED',repr(exc))
finally:
 win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
time.sleep(.12)
print('AFTER',win32gui.GetForegroundWindow())
