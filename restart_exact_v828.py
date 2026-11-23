"""Cut over only the existing V8.27 overlay process to updated V8.28 code.

Never terminate Smaart or unrelated python/Qt programs. Only the exact
source path may be stopped and relaunched.
"""
from pathlib import Path
import subprocess
import sys
import time
import psutil
import win32gui

directory=Path(__file__).resolve().parent
target=(directory/"overlay_v7.py").resolve()
venv=Path(r"D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\pythonw.exe")
if not target.is_file() or not venv.is_file():
    raise SystemExit("PREFLIGHT_MISSING_FILE")
smaart=win32gui.FindWindow(None,"Smaart Suite")
if not smaart:
    raise SystemExit("PREFLIGHT_NO_SMAART")
def exact_owner(p):
    try:
        return (p.name().lower()=="pythonw.exe" and
                len(p.cmdline())>=2 and
                Path(p.cmdline()[1]).resolve()==target and
                p.cwd().lower()==str(directory).lower())
    except (psutil.Error, OSError, ValueError):
        return False

previous=[p for p in psutil.process_iter() if exact_owner(p)]
print("PREVIOUS",[(p.pid,p.ppid()) for p in previous],flush=True)
if len(previous) != 2:
    raise SystemExit("ABORT: unexpected owner count; no process stopped")
children=sorted(previous,key=lambda p:p.ppid() not in [other.pid for other in previous])
for p in children:
    if p.is_running():
        print("STOP_EXACT",p.pid,flush=True)
        p.terminate()
gone,alive=psutil.wait_procs(children,timeout=3)
for p in alive:
    if exact_owner(p):
        print("FORCE_EXACT",p.pid,flush=True)
        p.kill()
        p.wait(timeout=3)
if any(exact_owner(p) for p in psutil.process_iter()):
    raise SystemExit("ABORT: old exact source still active")
with (directory/"V828_RUNTIME.stdout.log").open("a",encoding="utf-8") as stdout, (directory/"V828_RUNTIME.stderr.log").open("a",encoding="utf-8") as stderr:
    new=subprocess.Popen([str(venv),str(target)],cwd=str(directory),
                         stdout=stdout,stderr=stderr,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    print("START_REQUEST_PID",new.pid,flush=True)
    time.sleep(1.6)
    new_owners=[p for p in psutil.process_iter() if exact_owner(p)]
    print("NEW_OWNERS",[(p.pid,p.ppid()) for p in new_owners],flush=True)
    if not new_owners:
        raise SystemExit("RELAUNCH_FAILED_NO_OWNER")
    if not win32gui.IsWindow(smaart):
        raise SystemExit("SMAART_HANDLE_CHANGED")
    print("V828_RUNTIME_EXACT_SOURCE_PASS",flush=True)
