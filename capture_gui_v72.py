from PIL import ImageGrab
from pathlib import Path
import time
import win32gui
p=Path(__file__).with_name('V72_LIVE_GUI.png')
time.sleep(1.0)
ImageGrab.grab(all_screens=False).save(p)
Path(__file__).with_name('V72_GUI_FOREGROUND.txt').write_text(str(win32gui.GetWindowText(win32gui.GetForegroundWindow())),encoding='utf-8')
