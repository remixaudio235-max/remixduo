"""Read-only Smaart Suite *saved* plot smoothing sync.

The XML is on disk and may lag live UI until Smaart saves its session.
Confirmed observation on Admin-PC: smoothingId=5 corresponds to GUI 1/6 Oct.
Other ordinal values are provisional and must be validated against live UI.
Never edit SmaartConfig.xml or assert native Smaart DSP algorithm parity.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
import math

CONFIG=Path.home()/"Documents/Smaart Suite/Config/SmaartConfig.xml"
# Mapping from observed id 5 and likely consecutive fractional-octave IDs.
# Only 5 is verified with user screenshot / machine config today.
_ID_OCT={1:0.0,2:1/48,3:1/24,4:1/12,5:1/6,6:1/3}
# V8.124: id 2 = 1/48 Oct verified on Admin-PC 2026-11-12 (Smaart Suite
# Magnitude plot showed "1/48 Oct" with saved smoothingId=2; V8.115 log saw
# the same pair). Unverified ids kept native FIR/MagEQ hidden forever on a
# 1/48 Oct Magnitude plot ("Auto FIR không tạo FIR được").
# V8.134: id 3 = 1/24 Oct verified live 2026-11-12 (Phase plot "1/24 Oct",
# saved smoothingId=3).
# V8.151: id 4 = 1/12 Oct verified live 2026-11-15: the visible Magnitude
# selector showed "1/12 Oct" while the active saved Magnitude pane reported
# smoothingId=4. This is display registration only; FIR taps stay unsmoothed.
_VERIFIED_IDS=frozenset({2,3,4,5,6})

@dataclass(frozen=True)
class SavedSmooth:
    mag_id:int
    phase_id:int
    mag_oct:float
    phase_oct:float
    mag_verified:bool
    phase_verified:bool
    modified_ns:int

def read_saved_smooth(path=None):
    if path is None:
        from smaart_runtime_paths_v868 import running_major
        if running_major()==8:
            # Smaart 8 smoothing IDs are not yet calibrated against its GUI.
            return None
        path=CONFIG
    path=Path(path)
    try:
        mod=path.stat().st_mtime_ns
        root=ET.parse(path).getroot()
        # Phase2/Magnitude2 can be the active panes; Smaart does not
        # promise that the first plot of each type is visible.
        active={"phase":set(),"mag":set()}
        for el in root.iter("plotProperties"):
            name=el.findtext("name") or ""
            if el.findtext("visible")!="1":
                continue
            if name.startswith("Phase") and name[5:].isdigit():
                kind="phase"
            elif name.startswith("Magnitude") and name[9:].isdigit():
                kind="mag"
            else:
                continue
            smooth=el.findtext("smoothingId")
            if smooth is None:return None
            sid=int(smooth)
            if sid not in _ID_OCT:return None
            active[kind].add(sid)
        # Multiple active panes with different smoothing cannot authorize
        # one global AutoPhase smoothing value; fail closed.
        if any(len(active[kind])!=1 for kind in ("mag","phase")):
            return None
        mag=next(iter(active["mag"]))
        phase=next(iter(active["phase"]))
        return SavedSmooth(mag,phase,_ID_OCT[mag],_ID_OCT[phase],
                           mag in _VERIFIED_IDS,phase in _VERIFIED_IDS,mod)
    except (OSError,ValueError,ET.ParseError):
        return None
