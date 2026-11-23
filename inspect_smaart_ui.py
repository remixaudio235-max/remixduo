from pathlib import Path
from PIL import ImageGrab
import win32gui,win32process,win32con
from pywinauto import Desktop
OUT=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7")
im=ImageGrab.grab()
im.save(OUT/"smaart_windows_gui.png")
print("SCREENSHOT",im.size)
for hwnd in Desktop(backend="win32").windows():
    name=hwnd.window_text()
    if "Smaart" in name:
        h=hwnd.handle
        print("HWND",h,"TEXT",repr(name),"RECT",win32gui.GetWindowRect(h))
        try:
            w=Desktop(backend="uia").window(handle=h)
            print(w.print_control_identifiers(depth=5))
        except Exception as e:
            print("UIA_ERROR",str(e)[:250])
