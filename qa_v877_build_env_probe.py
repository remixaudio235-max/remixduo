"""V8.77 read-only build dependency audit; safe on live Admin-PC."""
import sys
import importlib.util
import os
import json
mods = ("PyQt6","numpy","pyqtgraph","PIL","win32gui","win32api",
        "psutil","pywinauto","websocket","cryptography","scipy",
        "sounddevice","mss","cv2","PyInstaller","pathlib")
print(json.dumps({
 "python":sys.executable,
 "no_user_site":os.getenv("PYTHONNOUSERSITE"),
 "sys_path":sys.path,
 "modules":{n:(
  getattr(importlib.util.find_spec(n),"origin",None)
  if importlib.util.find_spec(n) else "MISSING"
 ) for n in mods}
},indent=2))
