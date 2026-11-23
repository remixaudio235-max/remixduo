"""Stop only exact V8.23 RemiX Signal GUI processes.

Do not terminate other worktrees, Smaart, soundcard drivers or Windows apps.
"""
from pathlib import Path
import psutil
old=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_23_TRACE_SYNC_GUARD_QA")
targets=[]
for p in psutil.process_iter(["name","cwd","cmdline"]):
    try:
        if (str(p.info.get("cwd") or "").casefold()==str(old).casefold()
            and (p.info.get("name") or "").lower() in ("python.exe","pythonw.exe")
            and any(str(a).endswith("overlay_v7.py") for a in p.info.get("cmdline") or [])):
            targets.append(p)
    except (psutil.NoSuchProcess,psutil.AccessDenied):
        pass
print("EXACT_V823_INSTANCES",[(p.pid,p.info.get("name")) for p in targets],flush=True)
for p in targets:
    try:p.terminate()
    except psutil.NoSuchProcess:pass
gone,alive=psutil.wait_procs(targets,timeout=6)
if alive:raise RuntimeError("Failed to stop V8.23: "+str([p.pid for p in alive]))
print("V823_STOPPED_FOR_CONTROLLED_100_POLL_QA",flush=True)
