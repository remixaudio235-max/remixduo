"""Per-user marker distinguishing a clean close from a crash."""
import json,os,time
from pathlib import Path

MARKER=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"RemiXDuo"/"lifecycle.json"

def _write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data),encoding="utf-8")
    tmp.replace(path)

def mark_started(path=MARKER,pid=None):
    _write(path,{"pid":int(pid or os.getpid()),"clean":False,"at":time.time()})

def mark_clean(path=MARKER,pid=None):
    path=Path(path)
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError):data={}
    if pid is not None and data.get("pid") not in (None,int(pid)):return False
    data.update(pid=int(pid or os.getpid()),clean=True,at=time.time())
    _write(path,data);return True

def previous_exit_unclean(path=MARKER):
    try:return json.loads(Path(path).read_text(encoding="utf-8")).get("clean") is False
    except (OSError,ValueError,TypeError):return False

