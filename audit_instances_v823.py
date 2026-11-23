"""Read-only instance inventory for controlled RemiX V8.23 deployment."""
from pathlib import Path
import psutil
ROOT=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV")
for p in psutil.process_iter(["cwd","name","cmdline"]):
    try:
        args=p.info.get("cmdline") or []
        cwd=Path(p.info.get("cwd") or "C:\\")
        if ((p.info.get("name") or "").lower() in ("python.exe","pythonw.exe")
            and any(str(x).endswith("overlay_v7.py") for x in args)
            and str(cwd).casefold().startswith(str(ROOT).casefold())):
            print(f"PID={p.pid} VERSION={cwd.name}",flush=True)
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
