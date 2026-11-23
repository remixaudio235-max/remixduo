from pathlib import Path
import psutil
ROOT=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
matches=[]
for p in psutil.process_iter(["cwd","cmdline","name"]):
    try:
        if (str(p.info.get("cwd") or "").casefold()==str(ROOT).casefold()
            and (p.info.get("name") or "").lower() in ("pythonw.exe","python.exe")
            and any(str(arg).endswith("overlay_v7.py") for arg in p.info.get("cmdline") or [])):
            matches.append(p)
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
print("V824_INSTANCES",[(p.pid,p.info.get("name")) for p in matches],flush=True)
for p in matches:
    try:p.terminate()
    except psutil.NoSuchProcess:pass
gone,alive=psutil.wait_procs(matches,timeout=5)
if alive:raise RuntimeError("Could not stop V824 "+repr([p.pid for p in alive]))
print("V824_OLD_INSTANCES_CLOSED_PASS",flush=True)
