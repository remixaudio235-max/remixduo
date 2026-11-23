from PIL import ImageGrab
from pathlib import Path
import time,win32gui
out=Path(__file__).with_name('V74_REAL_SMAART_MATCH_GREEN.png')
time.sleep(0.7)
ImageGrab.grab(all_screens=False).save(out)
print('CAPTURE',out,'FOREGROUND',win32gui.GetWindowText(win32gui.GetForegroundWindow()))
