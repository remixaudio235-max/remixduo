"""V8.115: read Smaart's LIVE plot smoothing ("1/6 Oct") via UI Automation.

SmaartConfig.xml only changes when Smaart saves its session, so the SUM was
smoothed at the saved 1/48 Oct while Smaart displayed 1/6 Oct and the SUM
looked far rougher than the traces. Smaart 9 exposes each plot's smoothing
selector as a UIA ComboBox named "None" / "1/N Oct" inside the plot rect.
Read-only: names and rectangles only; nothing is clicked or changed.
"""
from __future__ import annotations
import re
from uia_serial_v8152 import serialized_uia

_NAME=re.compile(r"^\s*(?:(none)|1\s*/\s*(\d{1,3})\s*oct)\s*$",re.IGNORECASE)


def parse_smoothing(name:str)->float|None:
    m=_NAME.match(name or "")
    if not m:return None
    if m.group(1):return 0.0
    n=int(m.group(2))
    return 1.0/n if n>0 else None


def classify(elements,phase_rect,mag_rect):
    """elements: iterable of (name, (left, top, right, bottom)).

    Returns {"phase": oct, "mag": oct} for plots with exactly one consistent
    smoothing selector inside their rect; ambiguous plots are omitted.
    """
    found={"phase":set(),"mag":set()}
    for name,(l,t,r,b) in elements:
        value=parse_smoothing(name)
        if value is None:continue
        cx,cy=(l+r)/2,(t+b)/2
        for kind,(x,y,w,h) in (("phase",phase_rect),("mag",mag_rect)):
            if x<=cx<=x+w and y<=cy<=y+h:
                found[kind].add(value)
    return {k:next(iter(v)) for k,v in found.items() if len(v)==1}


@serialized_uia
def read_live_smoothing(hwnd,phase_rect,mag_rect):
    from pywinauto import Desktop
    root=Desktop(backend="uia").window(handle=hwnd)
    elements=[]
    for element in root.descendants(control_type="ComboBox"):
        r=element.rectangle()
        elements.append((element.element_info.name or "",(r.left,r.top,r.right,r.bottom)))
    return classify(elements,phase_rect,mag_rect)
