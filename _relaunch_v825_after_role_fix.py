"""Operator requested V8.25 overlay repair/relaunch.
Only terminate the exact current V8.25 pythonw overlay launcher/child.
Smaart, Generator, AutoEQ repos and unrelated processes remain untouched.
"""
from pathlib import Path
import psutil,subprocess,sys,time,os
ROOT=Path(__file__).resolve().parent
PYW=Path(r"D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\pythonw.exe")
def locate():
    matches=[]
    foreign=[]
    for p in psutil.process_iter(("pid","name","cmdline")):
        try:
            if (p.info.get("name") or "").lower()!="pythonw.exe":continue
            cmd=p.info.get("cmdline") or []
            if not any(Path(a).name.lower()=="overlay_v7.py" for a in cmd):continue
            cwd=Path(p.cwd())
            (matches if cwd==ROOT else foreign).append(p)
        except (psutil.AccessDenied,psutil.NoSuchProcess,OSError):continue
    return matches,foreign
old,foreign=locate()
print("EXACT_V825_PIDS",[(p.pid,p.ppid()) for p in old],flush=True)
print("FOREIGN_OVERLAY_PIDS",[(p.pid,str(p.cwd())) for p in foreign],flush=True)
if foreign:raise SystemExit("REFUSED: concurrent other overlay")
if len(old)!=2 or not any(p.ppid() in {q.pid for q in old} for p in old):
    raise SystemExit("REFUSED: unexpected V8.25 tree; no actions")
for p in sorted(old,key=lambda a:a.ppid() in {q.pid for q in old},reverse=True):
    try:p.terminate();p.wait(timeout=6);print("EXIT",p.pid,flush=True)
    except psutil.NoSuchProcess:pass
    except psutil.TimeoutExpired:raise SystemExit("STOP: non-exited V8.25 process")
if locate()[0] or locate()[1]:
    raise SystemExit("STOP: another overlay remains")
if not PYW.is_file():raise SystemExit("STOP: Pythonw missing")
# Launch only this requested V8.25 entrypoint and collect QA logs.
out=open(ROOT/"V825_ROLE_FIX_LIVE.stdout.log","ab",buffering=0)
err=open(ROOT/"V825_ROLE_FIX_LIVE.stderr.log","ab",buffering=0)
proc=subprocess.Popen([str(PYW),str(ROOT/"overlay_v7.py")],cwd=str(ROOT),
     stdin=subprocess.DEVNULL,stdout=out,stderr=err,
     creationflags=subprocess.CREATE_NO_WINDOW)
print("V825_RELAUNCH_PARENT_PID",proc.pid,flush=True)
time.sleep(1.8)
print("V825_RELAUNCH_TREE",[(p.pid,p.ppid()) for p in locate()[0]],flush=True)
print("SMAART_NOT_TOUCHED",flush=True)
