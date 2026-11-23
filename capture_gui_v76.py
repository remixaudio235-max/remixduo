from PIL import ImageGrab
from pathlib import Path
import win32gui,time
root=Path(__file__).resolve().parent
time.sleep(0.5)
ImageGrab.grab(all_screens=False).save(root/'V76_REAL_SMAART_GUI.png')
(root/'V76_FOREGROUND.txt').write_text(win32gui.GetWindowText(win32gui.GetForegroundWindow()),encoding='utf-8')
