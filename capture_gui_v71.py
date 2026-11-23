from PIL import ImageGrab
from pathlib import Path
import time
import win32gui
p=Path(__file__).with_name('V71_REAL_GUI_SCREEN.png')
time.sleep(1.0)
ImageGrab.grab(all_screens=False).save(p)
Path(__file__).with_name('V71_GUI_FOREGROUND.txt').write_text(str(win32gui.GetWindowText(win32gui.GetForegroundWindow())),encoding='utf-8')
