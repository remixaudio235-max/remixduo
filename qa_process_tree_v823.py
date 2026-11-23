import psutil
from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_23_TRACE_SYNC_GUARD_QA")
for p in psutil.process_iter(["name","cwd","exe","cmdline","ppid","create_time"]):
    try:
        d=Path(p.info.get("cwd") or "C:\\")
        if (str(d).casefold()==str(root).casefold() and
            any(str(x).endswith("overlay_v7.py") for x in (p.info.get("cmdline") or []))):
            print("PID",p.pid,"PPID",p.ppid(),"EXE",p.info.get("exe"),"START",p.info.get("create_time"),"ARGS",p.info.get("cmdline"),flush=True)
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
