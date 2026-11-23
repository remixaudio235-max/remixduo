"""V8.121: Smaart 8 Data Bar tick reading from PrintWindow pixels.

Smaart 8.5 exposes NO UI Automation tree (a single Pane), and its API V3 can
only send commands (hide/capture/rename), never report which traces are
shown. The Data Bar is therefore read from pixels, read-only:
- trace rows = coloured document icons in the left column (x 24..46 at
  1920 px), one per row, top to bottom; the orange "Session Data" folder
  icon is excluded;
- each icon is classified with the same white-cross rule as Smaart Suite
  (no cross = shown/"on", white X = hidden/"off", otherwise "unknown").
Caller maps rows to selection_v7.archive_order() and fails closed when the
visible row count differs from the number of files.
"""
from __future__ import annotations
import numpy as np
from selection_v7 import scan_icon_white_cross


def _is_folder(mean_rgb):
    r,g,b=mean_rgb
    return r>110 and b<45 and r>g*1.25      # orange folder (152,99,5)


def v8_row_states(image,host,*,dpi=96):
    """Native image-pixel trace rows, independently of screen resolution.

    DPI is obtained from GetDpiForWindow, never window width / 1920.
    """
    l,t,r,b=map(int,host)
    w,h=r-l,b-t
    if image is None or not hasattr(image,"size") or image.size!=(w,h):
        return []
    if not isinstance(dpi,(int,float)) or not (72<=dpi<=288):
        return []
    sx=sy=float(dpi)/96.
    x0,x1=round(20*sx),round(50*sx)
    y0,y1=round(100*sy),min(h-round(50*sy),round(900*sy))
    if not (0<=x0<x1<=w and 0<=y0<y1<=h):
        return []
    arr=np.asarray(image.convert("RGB"),dtype=np.int16)
    if arr.shape[0]<y1 or arr.shape[1]<x1:
        return []
    band=arr[y0:y1,x0:x1]
    hi=band.max(axis=2);lo=band.min(axis=2)
    # Dark/desaturated trace colours are valid in Smaart 8. The icon gutter
    # has no trace-name text, so use a restrained floor and retain the folder
    # exclusion below. The former >40/>80 gate dropped dark-green icons and
    # shifted every following tick-to-file mapping into a row-count HOLD.
    colorful=((hi-lo)>12)&(hi>35)
    frac=colorful.mean(axis=1)
    rows=[];start=None
    for i,value in enumerate(np.append(frac,0.)):
        if value>.15 and start is None:start=i
        elif value<=.15 and start is not None:
            if i-start>=round(8*sy):rows.append((start,i))
            start=None
    out=[]
    for a,c in rows:
        # The Session Data folder glyph is materially shorter than a trace
        # document icon at every supported DPI.  Reject it before the more
        # permissive dark-colour gate can treat it as a trace row.
        # Native TRF glyphs are ~18*DPI pixels tall. Large coloured
        # control panels BELOW the Data Bar cannot be trace icons.
        # Keep selected-row glyphs up to 29*DPI, but reject footer blocks.
        if not (round(16*sy)<=c-a<=round(29*sy)):
            continue
        cols=np.flatnonzero(colorful[a:c].any(axis=0))
        bx0,bx1=x0+int(cols.min()),x0+int(cols.max())+1
        # Session Data's folder starts at the far-left gutter and ends before
        # the trace document core. A selected trace may also start at x=20,
        # but its row highlight spans beyond the full core, so retain it.
        if bx0<round(24*sx) and bx1<round(41*sx):
            continue
        # Never identify a Session Data folder by colour alone. Smaart 8
        # permits orange/yellow/red saved TRF icons; the previous heuristic
        # removed valid OFF files at 125% (indices 1 and 6).
        # Folder/document distinction is based on glyph dimensions and
        # verified TRF inventory count, not an RGB threshold.
        # V8.167: a selected Data Bar row highlights the ENTIRE 20..50px
        # gutter and grows its row bbox from 14x18 to ~30x22. Passing that
        # highlight to the shared X classifier dilutes a real white cross
        # (0.11 inside the glyph -> 0.05 across the highlighted row), making
        # an OFF trace permanently 'unknown'. Verify the native 14px icon
        # core, never the user's row-selection highlight. Unexpected icon
        # displacement still fails closed, instead of guessing ON/OFF.
        core_x0,core_x1=round(27*sx),round(41*sx)
        state=(scan_icon_white_cross(image,(core_x0,y0+a,
                                            core_x1,y0+c))
               if bx0<=core_x0 and core_x1<=bx1 else "unknown")
        out.append((t+y0+a,t+y0+c,state))
    return out
