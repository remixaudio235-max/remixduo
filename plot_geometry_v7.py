"""Read-only UI Automation chart discovery for Smaart Suite Windows.

Choose actual plot canvases by geometry, rather than assuming the lower
panel starts beyond 52% of the window's height. Small resize/dock changes
move that boundary. Never fabricate plots when native UIA is ambiguous.
"""
from __future__ import annotations
from dataclasses import dataclass
from pywinauto import Desktop
import time
from uia_serial_v8152 import serialized_uia

@dataclass(frozen=True)
class Plots:
    phase:tuple[int,int,int,int]
    mag:tuple[int,int,int,int]
    observed_at:float
    theme:str="dark"  # visual only; never used as a native proof bypass


def choose_canvas_pair(rectangles, window_rect):
    """Pure selection of two vertically stacked, matching native canvases."""
    wl,wt,wr,wb=window_rect
    width,height=wr-wl,wb-wt
    if width<700 or height<500:
        return None
    eligible=set()
    for bounds in rectangles:
        l,t,r,b=map(int,bounds)
        w,h=r-l,b-t
        if not (w>width*.48 and width*.16<h<height*.54):
            continue
        if not (l>=wl+150 and r<=wr-120 and t>=wt and b<=wb):
            continue
        # Avoid large nested chart containers: the real UIA canvas
        # starts after the left axis labels (typically +250 px).
        eligible.add((l,t,r,b))
    scored=[]
    seq=sorted(eligible)
    for a in seq:
        for b in seq:
            if b[1]<=a[1]:continue
            wa,ha=a[2]-a[0],a[3]-a[1]
            wb_,hb=b[2]-b[0],b[3]-b[1]
            gap=b[1]-a[3]
            if not (8<=gap<=max(115,height*.14)):
                continue
            if not (abs(a[0]-b[0])<=12 and abs(a[2]-b[2])<=12):
                continue
            if min(ha,hb)/max(ha,hb)<.75:
                continue
            # Prefer the inset canvas pair, not outer chart containers.
            # Wider x-offset from left window edge distinguishes them.
            score=(min(a[0],b[0]),min(ha,hb),-gap)
            scored.append((score,a,b))
    if not scored:return None
    scored.sort(key=lambda item:item[0],reverse=True)
    top,bottom=scored[0][1:]
    def shrink(p):
        x,y,r,b=p
        return (x+2,y+2,r-x-4,b-y-4)
    return shrink(top),shrink(bottom)


@serialized_uia
def locate_plots(hwnd):
    root=Desktop(backend="uia").window(handle=hwnd)
    rect=root.rectangle()
    bounds=(rect.left,rect.top,rect.right,rect.bottom)
    candidates=[]
    for item in root.descendants(control_type="Custom"):
        box=item.rectangle()
        candidates.append((box.left,box.top,box.right,box.bottom))
    selected=choose_canvas_pair(candidates,bounds)
    if selected is None:return None
    upper,lower=selected
    # These are geometrical slots ONLY; plot_role_v812 detects actual
    # Phase/Mag ordering separately from original Smaart title glyphs.
    return Plots(upper,lower,time.perf_counter())
