"""V7 auto-selection state, event debouncing, and safe stale-result cancellation.

When an active pair changes, prior SUM is removed synchronously BEFORE
asynchronous TRF parsing/AutoAlign; never show stale lines.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import threading
import time

@dataclass(frozen=True)
class Selection:
    generation:int
    names:tuple[str,str]
    reason:str
    when:float

class SelectionController:
    def __init__(self,on_change:Callable[[Selection|None],None]):
        self.on_change=on_change
        self.generation=0
        self.last_pair:tuple[str,str]|None=None
        self.history=[]
        self.lock=threading.RLock()
        self.updated_at=0.

    def apply(self,active:list[str]|tuple[str,...],reason="DataBar",confirmed=True)->bool:
        # No data or ambiguous scan is NOT an invitation to reuse last pair.
        pair=tuple(active) if confirmed and len(active)==2 and active[0]!=active[1] else None
        if pair and (any(not Path(x).suffix.lower()==".trf" for x in pair)):
            pair=None
        with self.lock:
            if pair==self.last_pair:
                return False
            self.generation+=1
            self.last_pair=pair
            self.updated_at=time.perf_counter()
            record=Selection(self.generation,pair,reason,self.updated_at) if pair else None
            self.history.append((self.generation,pair,self.updated_at,reason))
        self.on_change(record)
        return True

    def invalidate(self,reason="invalid"):
        return self.apply([],reason=reason)

    def is_current(self,generation:int,pair:tuple[str,str])->bool:
        with self.lock:
            return self.generation==generation and self.last_pair==pair

def archive_order(folder:Path)->list[Path]:
    """Map Smaart 9.6.4 Data Bar files by index IDs plus verified new imports.

    Smaart may show newly imported ASCII TFs immediately as .trf at the TOP
    of Data Bar, *before* index.xml is saved. The old indexed order stays
    beneath newly imported entries; latest imported .trf appears first.
    This fallback is intentionally strict:
      - existing indexed paths must match a contiguous 0-based list;
      - all missing paths must be *newer* than the index.xml timestamp;
      - no duplicate names or tied import timestamps;
      - UIA row count is additionally checked by LiveDataBar/FullScan.
    It does NOT edit Smaart files or invent missing TF data.
    """
    from xml.etree import ElementTree as ET
    folder=Path(folder)
    all_paths=list(folder.glob("*.trf"))
    all_files={p.name.casefold():p for p in all_paths}
    if len(all_files)!=len(all_paths):
        raise ValueError("Ambiguous case-insensitive .trf filenames")
    index=folder.parent/"index.xml"
    if not index.is_file():
        raise ValueError("Smaart index.xml missing; mapping unverified")
    try:
        root=ET.parse(index).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Smaart index.xml parse failed: {exc}") from exc
    ids={}
    indexed=set()
    for element in root.findall(".//path"):
        name=str(element.text or "").strip()
        if not name.lower().endswith(".trf"):
            continue
        key=Path(name).name.casefold()
        if key not in all_files:
            raise ValueError(f"Smaart index references missing TRF: {name}")
        try:
            ix=int(element.attrib["adhocIndex"])
        except (ValueError,KeyError) as exc:
            raise ValueError("Smaart index has invalid row ID") from exc
        if ix in ids or key in indexed:
            raise ValueError("Duplicate row/Trace in Smaart index")
        indexed.add(key)
        ids[ix]=all_files[key]
    # V8.111: a fresh Smaart 9 session writes an index.xml stub with ZERO
    # trace entries (<traceTreeScanner>). Then every .trf is an unindexed
    # import and goes through the strict fresh-import checks below.
    if not ids:
        # V8.121: Smaart 8.5 and Smaart 9 fresh sessions write a
        # <traceTreeScanner> index: per-folder <item fileName> in Data Bar
        # display order (observed live on Smaart 8: SUB SKY 2, 0 delay).
        for scanner in root.iter("traceFolderScanner"):
            try:
                same=Path(scanner.attrib.get("path","")).resolve()==folder.resolve()
            except OSError:
                same=False
            if not same:continue
            for item in scanner.iter("item"):
                name=str(item.attrib.get("fileName","")).strip()
                if not name.lower().endswith(".trf"):continue
                key=Path(name).name.casefold()
                if key not in all_files:
                    raise ValueError(f"Smaart index references missing TRF: {name}")
                if key in indexed:
                    raise ValueError("Duplicate row/Trace in Smaart index")
                ids[len(ids)]=all_files[key]
                indexed.add(key)
    if ids and sorted(ids)!=list(range(len(ids))):
        raise ValueError("Smaart indexed row IDs incomplete/noncontiguous")
    missing=[p for k,p in all_files.items() if k not in indexed]
    if not missing:
        if len(ids)!=len(all_files):
            raise ValueError("Smaart index cardinality inconsistent")
        return [ids[i] for i in range(len(ids))]
    if len(missing)>16:
        raise ValueError(f"Too many unindexed imports: {len(missing)}")
    # Only accept fresh imports, never silently remap old or renamed traces.
    index_stamp=index.stat().st_mtime_ns
    if any(p.stat().st_mtime_ns <= index_stamp+1_000_000_000 for p in missing):
        raise ValueError("Unindexed .trf older than Smaart index; ambiguous order")
    times=[p.stat().st_mtime_ns for p in missing]
    if len(times)!=len(set(times)):
        raise ValueError("Imported .trf timestamps tied; ambiguous order")
    imported=sorted(missing,key=lambda p:p.stat().st_mtime_ns,reverse=True)
    # Note: recovered order MUST be corroborated against live Data Bar.
    return imported+[ids[i] for i in range(len(ids))]

def fresh_unindexed_imports(folder:Path)->tuple[Path,...]:
    """Metadata only; a visible GUI should label this provisional mapping."""
    from xml.etree import ElementTree as ET
    folder=Path(folder)
    index=folder.parent/"index.xml"
    if not index.is_file():
        return ()
    listed={Path(str(q.text)).name.casefold()
            for q in ET.parse(index).getroot().findall(".//path")
            if str(q.text).lower().endswith(".trf")}
    return tuple(p for p in folder.glob("*.trf") if p.name.casefold() not in listed)

def icon_color(image, rect):
    """V8.123: the trace's own Smaart colour from its Data Bar icon.

    Median of the saturated icon pixels as '#RRGGBB'; None for a grey or
    unreadable icon (never invent a colour).
    """
    import numpy as np
    clip=np.asarray(image.crop(tuple(map(int,rect))).convert("RGB"),dtype=np.int16)
    if clip.size==0:return None
    px=clip.reshape(-1,3)
    sat=(px.max(axis=1)-px.min(axis=1)>50)&(px.max(axis=1)>70)
    if sat.sum()<max(6,.08*len(px)):return None
    r,g,b=(int(v) for v in np.median(px[sat],axis=0))
    return f"#{r:02X}{g:02X}{b:02X}"


def scan_icon_white_cross(image, rect)->str:
    """Classify a Smaart TF Data Bar icon by its *internal* white-X pixels.

    The white Smaart sidebar/background MUST NOT contribute to X density.
    Real Smaart file icons have a folded white top-right page corner; crop
    to the interior of the coloured shape to avoid treating that as a tick.
    No reliable coloured icon -> UNKNOWN, never OFF. Critical for a new PC
    with different scaling/row geometry: missing icons must NOT yield 0/2.
    """
    import numpy as np
    clip=np.asarray(image.crop(tuple(map(int,rect))).convert("RGB"),
                    dtype=np.float32)/255.
    if clip.ndim != 3 or clip.shape[0]<8 or clip.shape[1]<8:
        return "unknown"
    hi=clip.max(axis=2)
    lo=clip.min(axis=2)
    color=(hi>.13)&((hi-lo)>.07)
    # A background- or DPI-clipped icon is not trustworthy. It cannot be
    # silently classified as OFF on the basis of white background.
    if float(color.mean())<.18:
        return "unknown"
    ys,xs=np.nonzero(color)
    if not len(xs):
        return "unknown"
    x0,x1=int(xs.min()),int(xs.max())
    y0,y1=int(ys.min()),int(ys.max())
    bw=x1-x0+1
    bh=y1-y0+1
    if bw<10 or bh<10:
        return "unknown"
    # Central region excludes outer white background and folded page corner.
    cx0=x0+max(1,int(round(bw*.20)))
    cx1=x0+max(2,int(round(bw*.78)))
    cy0=y0+max(1,int(round(bh*.24)))
    cy1=y0+max(2,int(round(bh*.78)))
    if cx1<=cx0 or cy1<=cy0:
        return "unknown"
    central_color=float(color[cy0:cy1,cx0:cx1].mean())
    central_white=float(((lo>.66)&((hi-lo)<.20))
                        [cy0:cy1,cx0:cx1].mean())
    # Two well-separated bands: do not guess on an anti-aliased uncertain X.
    if central_white>=.22 and central_color>=.20:
        return "off"
    if central_white<=.06 and central_color>=.78:
        return "on"
    return "unknown"
