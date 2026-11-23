from PIL import ImageGrab
from pathlib import Path
import time,win32gui
p=Path(__file__).with_name('V73_REAL_SMAART_ROI.png')
time.sleep(.6)
ImageGrab.grab(all_screens=False).save(p)
print('CAPTURED',p,'FRONT',win32gui.GetWindowText(win32gui.GetForegroundWindow()))
