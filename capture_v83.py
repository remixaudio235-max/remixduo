from PIL import ImageGrab
from pathlib import Path
import time,win32gui
p=Path(__file__).resolve().parent
time.sleep(.25)
ImageGrab.grab(all_screens=False).save(p/'V83_REAL_ANCHORED_GUI.png')
h=win32gui.GetForegroundWindow()
(p/'V83_REAL_FOREGROUND.txt').write_text(win32gui.GetWindowText(h),encoding='utf-8')
