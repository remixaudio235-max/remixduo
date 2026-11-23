"""Stop only the old V8.22 overlay processes for controlled V8.23 cutover.
Does NOT touch Smaart or audio generators. Does NOT touch other RemiX trees.
"""
import psutil
from pathlib import Path
OLD=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_22_VISIBILITY_LIVE_QA")
owners=[]
for p in psutil.process_iter(["name","cwd","cmdline"]):
    try:
        info=p.info
        if (str(info.get("cwd") or "").casefold()==str(OLD).casefold()
            and (info.get("name") or "").lower() in ("python.exe","pythonw.exe")
            and any(str(x).endswith("overlay_v7.py") for x in (info.get("cmdline") or []))):
            owners.append(p)
    except (psutil.NoSuchProcess,psutil.AccessDenied):
        pass
print("FOUND_EXACT_V822_PROCESSES",[(p.pid,p.info.get("cwd")) for p in owners],flush=True)
for p in owners:
    try:
        p.terminate()
        print("TERMINATED_V822_PID",p.pid,flush=True)
    except psutil.NoSuchProcess:
        print("ALREADY_EXITED",p.pid,flush=True)
gone,alive=psutil.wait_procs(owners,timeout=4)
if alive:
    raise RuntimeError("V822 still running: "+repr([p.pid for p in alive]))
print("V822_OBSERVERS_STOPPED_COUNT",len(owners),flush=True)
