"""Read-only plot bounds discovery for Smaart 9.6.4 Windows.
Use UIA chart rectangles rather than percentage-of-window guesses.
Does not claim numeric axis scale parity. Invalid layouts fail closed.
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

@serialized_uia
def locate_plots(hwnd):
    root=Desktop(backend="uia").window(handle=hwnd)
    rect=root.rectangle()
    matches=set()
    for item in root.descendants(control_type="Custom"):
        r=item.rectangle()
        w,h=r.width(),r.height()
        if (w>rect.width()*.48 and
                rect.height()*.20<h<rect.height()*.52 and
                r.left>=rect.left+150 and r.right<=rect.right-120):
            matches.add((r.left,r.top,r.right,r.bottom))
    if len(matches)<2:return None
    ordered=sorted(matches,key=lambda q:q[1])
    plot=[r for r in ordered if r[2]-r[0]>900 and r[3]-r[1]>240]
    if len(plot)<2:return None
    upper=[p for p in plot if p[1]<rect.top+rect.height()*.54]
    lower=[p for p in plot if p[1]>=rect.top+rect.height()*.52]
    if not upper or not lower:return None
    phase=upper[0];mag=lower[0]
    if phase[3]>=mag[1]:return None
    def shrink(p):
        l,t,r,b=p
        return (l+2,t+2,r-l-4,b-t-4)
    return Plots(shrink(phase),shrink(mag),time.perf_counter())
