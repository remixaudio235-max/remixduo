"""Version-isolated Smaart read-only paths.

Smaart 8's saved session is NOT Smaart Suite 9's session. Never mix
TRF traces, smoothing, Fs or implicit tick mappings across editions.
"""
from pathlib import Path
import win32gui
import win32process
import psutil
from smaart8_api3_readonly_v868 import process_smaart_major

def running_major():
    versions=set()
    def visit(hwnd,_):
        if not win32gui.IsWindow(hwnd):return
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        try:
            if psutil.Process(pid).name().lower() not in ("smaart.exe","smaart suite.exe"):
                return
        except psutil.Error:
            return
        v=process_smaart_major(hwnd)
        if v is not None:versions.add(v)
    win32gui.EnumWindows(visit,None)
    return next(iter(versions)) if len(versions)==1 else None

def trace_directory(major=None,home=None):
    from smaart_discovery_v875 import trace_folder, known_documents
    documents=(Path(home)/"Documents") if home is not None else known_documents()
    edition=running_major() if major is None else major
    return trace_folder(edition, documents=documents)  # Unknown edition: fail closed.

def saved_config(major=None,home=None):
    from smaart_discovery_v875 import config_file, known_documents
    documents=(Path(home)/"Documents") if home is not None else known_documents()
    edition=running_major() if major is None else major
    return config_file(edition, documents=documents)
