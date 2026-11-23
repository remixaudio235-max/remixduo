"""Read-only Magnitude Y axis from Smaart's own 0 dB line and grid.

Unlike curve-matching this is independent of trace colors, visible frequency
span, smoothing, phase/delay, and selected TF identity. No OCR, UI changes,
Smaart writes, or audio I/O. Reject if the native zero/grid geometry fails.
"""
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class NativeGridY:
    accepted: bool
    y_min: float=0.
    y_max: float=0.
    zero_px: float=0.
    px_per_db: float=0.
    grid_step_px: float=0.
    confidence: float=0.
    reason: str=""


def saved_mag_grid_interval(path=None,*,allow_inactive_consensus=False):
    # Only the *dB-per-grid interval* comes from the saved XML, NOT the
    # Y min/max/center. The latter are always measured live in native pixels.
    # An inactive-plot consensus is a HYPOTHESIS, never accepted alone:
    # capture_sum_mag_axis independently checks live native 0 dB + lattice
    # and source-curve pixels-per-dB before it may use the hypothesis.
    if path is None:
        from smaart_runtime_paths_v868 import running_major,saved_config
        if running_major()==8:
            path=saved_config(8)
    file=Path(path or Path.home()/"Documents/Smaart Suite/Config/SmaartConfig.xml")
    try:
        root=ET.parse(file).getroot()
        visible=set()
        stored=[]
        for node in root.iter("plotProperties"):
            name=node.findtext("name") or ""
            if name.startswith("Magnitude") and name[9:].isdigit():
                value=float(node.findtext("ordinateGridInterval"))
                if not (np.isfinite(value) and .5<=value<=20):
                    continue
                stored.append(value)
                if node.findtext("visible")=="1":
                    visible.add(value)
        if len(visible)==1:
            return next(iter(visible))
        if visible:
            return None
        if allow_inactive_consensus and len(stored)>=2 and len(set(stored))==1:
            return stored[0]
        return None
    except (OSError,ValueError,TypeError,ET.ParseError):
        return None


def saved_mag_grid_interval_major(major):
    """Read the EXACT edition's saved grid config; native pixels still prove Y.

    Avoid a costly EnumWindows/psutil running_major() search for each
    native capture when the HWND was already independently versioned.
    A new call reads the current XML; no cached/stale config or TTL bypass.
    """
    if major not in (8,9):
        return None  # Ambiguous host => fail closed.
    from smaart_runtime_paths_v868 import saved_config
    filename=saved_config(major)
    return saved_mag_grid_interval(filename) if filename else None


def fit_native_mag_grid(image,plot_rect,window_rect,grid_interval_db):
    if grid_interval_db is None or not np.isfinite(grid_interval_db):
        return NativeGridY(False,reason="Saved dB grid interval unavailable")
    x,y,w,h=map(int,plot_rect)
    l,t,r,b=map(int,window_rect)
    if not(w>=700 and h>=220 and l<=x and t<=y and x+w<=r and y+h<=b):
        return NativeGridY(False,reason="Invalid native plot bounds")
    rgb=np.asarray(image.crop((x-l,y-t,x-l+w,y-t+h)).convert("RGB"),
                   dtype=np.int16)
    # Ignore left labels/right Smaart controls and both top/bottom borders.
    region=rgb[8:h-8, max(60,int(.07*w)):min(w-100,int(.90*w))]
    if region.shape[1]<500:
        return NativeGridY(False,reason="Not enough native plot pixels")
    mn=region.min(axis=2)
    mx=region.max(axis=2)
    neutral=mx-mn<12
    light_theme=float(np.median(mn))>=175.
    if light_theme:
        # White chart background is NOT a zero-line. On light Suite the
        # true native 0 dB baseline is a single nearly-black line. Grey
        # arbitrary cursor lines (e.g. -12 dB) must never become 0 dB.
        zero_coverage=(neutral&(mn<80)).mean(axis=1)
        zero_candidates=np.flatnonzero(zero_coverage>.65)
    else:
        # Preserve original dark theme: single light neutral 0 dB axis.
        whites=(neutral&(mn>145)).mean(axis=1)
        zero_candidates=np.flatnonzero(whites>.57)
    # There must be exactly ONE interior bright horizontal line.
    groups=np.split(zero_candidates,np.where(np.diff(zero_candidates)>1)[0]+1)
    centers=[int(round(float(np.mean(g)))) for g in groups if len(g)]
    if len(centers)!=1:
        return NativeGridY(False,reason="0 dB baseline not unique")
    zero=centers[0]+8
    # Light Suite grid is pale grey (~229/230/233), not dark on black.
    # Smaart's black 0 dB baseline and arbitrary cursor line remain excluded.
    if light_theme:
        grids=(neutral&(mn>=195)&(mn<239)).mean(axis=1)
    else:
        grids=(neutral&(mn>=9)&(mn<110)).mean(axis=1)
    hits=np.flatnonzero(grids>.54)+8
    groups=np.split(hits,np.where(np.diff(hits)>2)[0]+1)
    rows=np.asarray([float(np.mean(g)) for g in groups
                     if len(g) and 8<=g[0]<h-8],dtype=float)
    # Border, 0 dB baseline and dense unrelated lines are excluded.
    rows=rows[(np.abs(rows-zero)>9)]
    if len(rows)<5:
        return NativeGridY(False,reason="Too few Smaart dB gridlines")
    gaps=np.diff(rows)
    adjacent=gaps[(gaps>=12)&(gaps<=h/4)]
    if len(adjacent)<4:
        return NativeGridY(False,reason="Inconsistent dB grid spacing")
    # In a gap spanning two or more grid intervals, other shorter gaps
    # dominate the robust median.
    pitch=float(np.median(adjacent))
    if pitch<12 or pitch>h/3:
        return NativeGridY(False,reason="Implausible dB pixel scale")
    # Verify that all detected lines agree with the zero-line grid lattice.
    distances=np.abs((rows-zero)/pitch-np.round((rows-zero)/pitch))*pitch
    agreement=float(np.mean(distances<2.4))
    if agreement<.80:
        return NativeGridY(False,reason="Grid does not align with 0 dB")
    px_per_db=pitch/float(grid_interval_db)
    y_max=float(zero/px_per_db)
    y_min=float(y_max-h/px_per_db)
    span=y_max-y_min
    if not (np.isfinite(y_min) and np.isfinite(y_max)
            and 8.<span<150. and -150.<y_min<150. and -150.<y_max<150.):
        return NativeGridY(False,reason="Unreasonable measured Y range")
    confidence=min(1.,agreement)
    return NativeGridY(True,y_min,y_max,float(zero),px_per_db,pitch,
                       confidence,"Native Smaart 0dB + dB grid lattice")
