from PIL import ImageGrab
from pathlib import Path
import time,win32gui
p=Path(__file__).with_name('V75_ASCII_IMPORT_GUI.png')
time.sleep(0.3)
ImageGrab.grab(all_screens=False).save(p)
Path(__file__).with_name('V75_CAPTURE_FOREGROUND.txt').write_text(win32gui.GetWindowText(win32gui.GetForegroundWindow()),encoding='utf8')
