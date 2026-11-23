# -*- coding: utf-8 -*-
"""Single-application V11 startup: ONE RemiX Signal hub embedded in Smaart.

Never launch autoeq_gui.py or a standalone AutoEQ compositor.
Never terminate/modify any other session, Smaart, soundcard or Generator.
"""
from pathlib import Path
import subprocess,sys
import psutil,win32gui
ROOT=Path(__file__).resolve().parent
MAIN="overlay_v7.py"
BLOCKED_SCRIPTS=("overlay_v7.py","autoeq_gui.py",
                 "autoeq_native_mag_overlay.py","autoeq_smaart_overlay.py",
                 "qa_run_v10_live.py","qa_run_v11_live.py")

def conflicts():
    found=[]
    for p in psutil.process_iter(("pid","name","cmdline")):
        try:
            if not (p.info.get("name") or "").lower().startswith(("python","py.exe")):
                continue
            argv=p.info.get("cmdline") or []
            hit=[Path(a).name.lower() for a in argv if Path(a).name.lower() in BLOCKED_SCRIPTS]
            if hit:
                found.append((p.pid,str(p.cwd()),hit[0]))
        except (psutil.AccessDenied,psutil.NoSuchProcess,OSError):
            continue
    return found

def main():
    existing=conflicts()
    if existing:
        print("V11_START_REFUSED_DUPLICATE_OVERLAY",existing)
        print("Đóng companion/AutoEQ độc lập hiện tại bằng GUI trước. Smaart vẫn giữ nguyên.")
        return 2
    hwnd=win32gui.FindWindow(None,"Smaart Suite")
    if not hwnd:
        print("V11_START_REFUSED_NO_SMAART")
        return 2
    if "--dry-run" in sys.argv:
        print("V11_SINGLE_HUB_READY",ROOT)
        print("NO_STANDALONE_AUTOEQ_WINDOW")
        return 0
    py=Path(sys.executable).with_name("pythonw.exe")
    if not py.is_file():raise RuntimeError("Own AutoEQ Python 3.11 Qt environment missing")
    proc=subprocess.Popen([str(py),MAIN],cwd=str(ROOT),
      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print("V11_SINGLE_HUB_STARTED",proc.pid)
    print("NO autoeq_gui.py, no generator, no DSP apply")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
