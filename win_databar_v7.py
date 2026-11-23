"""Windows-only read-only Smaart window and Data Bar observer.

UIA on Smaart 9.6.4 exposes TreeItems as 'Level 0 row N' instead of the
stored trace name or on/off property. Therefore filename mapping and global
checkbox state CANNOT be assumed. A folder-sort map is deliberately gated
behind explicit calibration evidence. An unverified scan returns no selection.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os,time,ctypes
from ctypes import wintypes
import win32gui,win32process,win32con
from PIL import ImageGrab
from selection_v7 import scan_icon_white_cross,archive_order
from uia_serial_v8152 import serialized_uia

@dataclass(frozen=True)
class MainWindow:
    hwnd:int
    rect:tuple[int,int,int,int]
    foreground:bool

_kernel32=ctypes.WinDLL("kernel32",use_last_error=True)
_kernel32.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
_kernel32.OpenProcess.restype=wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes=(wintypes.HANDLE,wintypes.DWORD,
                                               wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD))
_kernel32.QueryFullProcessImageNameW.restype=wintypes.BOOL
_kernel32.CloseHandle.argtypes=(wintypes.HANDLE,)
_kernel32.CloseHandle.restype=wintypes.BOOL


def _process_binary_name(pid):
    """Fail-closed native process identity; no psutil extension on GUI timer.

    The previous psutil.Process(pid).exe() triggered a native Windows access
    violation during a real Smaart window enumeration.
    """
    if type(pid) is not int or pid<=0:return ""
    handle=_kernel32.OpenProcess(0x1000,False,pid) # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:return ""
    try:
        name=ctypes.create_unicode_buffer(32768)
        length=wintypes.DWORD(len(name))
        if not _kernel32.QueryFullProcessImageNameW(handle,0,name,ctypes.byref(length)):
            return ""
        return os.path.basename(name.value).casefold()
    finally:
        _kernel32.CloseHandle(handle)


def choose_smaart_host(found,prefer_hwnd=None):
    """Foreground Smaart wins; otherwise retain the explicitly bound HWND.

    The preferred HWND must be one of the independently verified visible
    Smaart windows in this scan. Never accept a foreign or vanished window.
    """
    if not found:
        return None
    front=next((window for window in found if window.foreground),None)
    if front is not None:
        return front
    if type(prefer_hwnd) is int and prefer_hwnd>0:
        bound=next((window for window in found if window.hwnd==prefer_hwnd),None)
        if bound is not None:
            return bound
    return found[0]


def locate_smaart(*,prefer_hwnd=None):
    found=[]
    def cb(hwnd,unused):
        if not win32gui.IsWindowVisible(hwnd):return
        title=win32gui.GetWindowText(hwnd)
        if not title or "Smaart" not in title:return
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        binary=_process_binary_name(int(pid))
        if binary not in ("smaart.exe","smaart suite.exe"):return
        r=win32gui.GetWindowRect(hwnd)
        if r[2]-r[0]<600 or r[3]-r[1]<450:return
        found.append(MainWindow(hwnd,r,hwnd==win32gui.GetForegroundWindow()))
    win32gui.EnumWindows(cb,None)
    # When a RemiX panel takes keyboard focus, no Smaart HWND is
    # foreground. Keep the previously verified host rather than jumping
    # to found[0] (z-order can point to the OTHER Smaart edition).
    return choose_smaart_host(found,prefer_hwnd)

class UIADataBarObserver:
    """Read state only on *visible* TreeItems. Never scroll behind the user.
    Full-list source needs independent test/calibration for Windows UIA mapping.
    """
    def __init__(self,folder:Path):
        self.folder=Path(folder)
        self.map_verified=False
        self.state={}
        self.order=[]
        self.cached_rows=[]
        self.cached_hwnd=None
        self.cached_at=0.
        self.error=""
        self.last_generation=0

    def calibrate_mapping(self,verified:bool):
        self.map_verified=verified
        self.order=archive_order(self.folder) if verified else []
        self.state.clear()

    @serialized_uia
    def poll(self):
        target=locate_smaart()
        if target is None or not target.foreground:
            return None,"Smaart not foreground"
        if not self.map_verified:
            return None,"WAIT: UIA row-to-TRF mapping not verified"
        if time.monotonic()-self.cached_at>.8 or target.hwnd!=self.cached_hwnd:
            try:
                from pywinauto import Desktop
                root=Desktop(backend="uia").window(handle=target.hwnd)
                raw=root.descendants(control_type="TreeItem")
                rows=[]
                for item in raw:
                    title=item.element_info.name or ""
                    if "Level 0 row " not in title:continue
                    try:
                        index=int(title.rsplit("row ",1)[1].split()[0])
                        r=item.rectangle()
                    except (ValueError,IndexError):
                        continue
                    # Normalize 1-based UIA row numbers to 0-based.
                    # (Adjusted later once full set is known.)
                    rows.append((index,r.left,r.top,r.right,r.bottom))
                # If no zero row present, shift indices down by one.
                if rows and all(r[0] != 0 for r in rows) and any(r[0] == 1 for r in rows):
                    rows=[(i-1,l,t,rr,b) for (i,l,t,rr,b) in rows]
                rows=[r for r in rows if 0<=r[0]<len(self.order)]
                self.cached_rows=rows
                self.cached_hwnd=target.hwnd
                self.cached_at=time.monotonic()
            except Exception as e:
                return None,"UIAutomation inaccessible: "+str(e)[:120]
        screen=ImageGrab.grab()
        l,t,r,b=target.rect
        changed=False
        scanned=0
        for index,x1,y1,x2,y2 in self.cached_rows:
            if y2>screen.height or y1<max(0,t+30) or y2>min(screen.height,b-35):
                continue
            # Icon area, not the text or scrollbar.
            status=scan_icon_white_cross(screen,(x1+8,y1+3,x1+23,y1+18))
            if status=="unknown":continue
            name=str(self.order[index])
            scanned+=1
            if self.state.get(name)!=status:
                self.state[name]=status
                changed=True
        if scanned==0:
            return None,"No visible Data Bar rows"
        if changed:self.last_generation+=1
        # Other enabled rows outside the scroll viewport remain unknown.
        if len(self.state)<len(self.order):
            return None,f"Partial observation: {len(self.state)}/{len(self.order)} rows"
        selected=tuple(k for k,v in self.state.items() if v=="on")
        if len(selected)!=2:
            return None,f"Expected exactly two ticks, observed {len(selected)}"
        return selected,"UIA Data Bar verified"
