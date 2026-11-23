"""Read-only Smaart plot type detection from original native title glyphs.

The v7 UIA geometry provided two real plot boxes but assumed Phase above Mag.
Smaart supports reversed order; detect both chart *roles* by the white
header text pattern, not their screen order. No OCR, API mutation, or sound
generator control. Unknown or altered labels fail closed to avoid drawing
the wrong type of SUM data on Smaart.

Templates derived 2026-10-29 from the actual Admin-PC Smaart 9.6.4
Magnitude/Phase title masks. If Smaart theme/DPI changes, recalibrate.
"""
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from PIL import Image
import win32gui
from full_scan_v7 import printwindow_image
from plot_geometry_v7 import locate_plots,Plots
import time

ROOT=Path(__file__).resolve().parent
MAG_TEMPLATE=ROOT/"V812_MAG_TITLE_TEMPLATE.png"
PHASE_TEMPLATE=ROOT/"V812_PHASE_TITLE_TEMPLATE.png"

@dataclass(frozen=True)
class RoleScores:
    upper_mag:float
    upper_phase:float
    lower_mag:float
    lower_phase:float
    role:str
    confidence:float

def _mask(rgb,width):
    """Native title ink, independent of Smaart Suite dark/light palette.

    Templates are binary TITLE GLYPHS, not Smaart white backgrounds. Use
    median of the same small header crop to select ink polarity, and reject
    mid-tone/unknown backgrounds rather than guessing plot roles.
    """
    patch=np.asarray(rgb)
    if patch.ndim!=3 or patch.shape[2]<3:
        raise ValueError("Expected RGB chart capture")
    hi=np.max(patch[:,:,:3],axis=2)
    lo=np.min(patch[:,:,:3],axis=2)
    bg=float(np.median(lo))
    if bg>=175.:
        # Light Suite: black/dark near-neutral glyphs on a white header.
        ink=(hi<135)&((hi-lo)<65)
    elif bg<=125.:
        # Dark Suite: original white glyph template calibrated 2026-10-29.
        ink=(lo>150)&((hi-lo)<35)
    else:
        ink=np.zeros(lo.shape,dtype=bool)  # fail closed on unknown theme
    return ink.astype(float)

def _score_mask(template,candidate):
    mag=float(np.sum(template*candidate))
    denom=float(np.sqrt(np.sum(template*template)*np.sum(candidate*candidate)))
    return mag/denom if denom>0 else 0.

def _read_mask(png):
    im=np.asarray(Image.open(png).convert("L"),dtype=np.float64)
    return (im>128).astype(float)

def _capture_image_area(image,rect,width):
    x,y,w,h=rect
    if x+13+width>image.width or y+19>image.height:return None
    # Same relative header coordinates regardless of top/bottom placement.
    crop=image.crop((x+13,y+5,x+13+width,y+19)).convert("RGB")
    return _mask(np.asarray(crop),width)

def detect_plot_roles(image,top_rect,bottom_rect,mag_template=None,phase_template=None):
    """Returns recognized roles or None on uncertainty / missing headers."""
    if mag_template is None:mag_template=_read_mask(MAG_TEMPLATE)
    if phase_template is None:phase_template=_read_mask(PHASE_TEMPLATE)
    results=[]
    for r in (top_rect,bottom_rect):
        masks=[]
        for tpl in (mag_template,phase_template):
            region=_capture_image_area(image,r,tpl.shape[1])
            masks.append(_score_mask(tpl,region) if region is not None else 0.)
        results.append(masks)
    a,b=results
    # Require correct independent glyph matches on both panels, and rule
    # out duplicated labels or overlay artifact matches. Fail closed.
    topmag=a[0]+b[1]
    topphase=a[1]+b[0]
    if topmag>topphase and a[0]>=0.72 and b[1]>=0.72 and (topmag-topphase)>=0.40:
        return RoleScores(a[0],a[1],b[0],b[1],"MAG_TOP",round(topmag/2,3))
    if topphase>topmag and a[1]>=0.72 and b[0]>=0.72 and (topphase-topmag)>=0.40:
        return RoleScores(a[0],a[1],b[0],b[1],"PHASE_TOP",round(topphase/2,3))
    return RoleScores(a[0],a[1],b[0],b[1],"UNKNOWN",max(topmag,topphase)/2)

def locate_role_plots(hwnd):
    """Select verified Smaart 8/API3 profile or unchanged Smaart 9 raster path."""
    from smaart8_api3_readonly_v868 import process_smaart_major
    version=process_smaart_major(hwnd)
    if version==8:
        from smaart8_plot_profile_v868 import locate_v8_role_plots_with_probe
        return locate_v8_role_plots_with_probe(hwnd)
    if version!=9:
        return None  # Never infer plot geometry for unknown Smaart editions.
    base=locate_plots(hwnd)
    if base is None:return None
    # locate_plots() historically assumes 'phase top, mag bottom';
    # use only its two *geometrical rectangles*, not those incorrect roles.
    top,bottom=base.phase,base.mag
    try:
        # Capture the exact Smaart HWND rather than the desktop, where
        # tooltips, terminals, or other windows can obscure title glyphs.
        # PrintWindow uses HWND-local pixels; UIA plot rectangles are in
        # screen coordinates and MUST be translated by the native origin.
        im=printwindow_image(hwnd)
        left,upper,_,_=win32gui.GetWindowRect(hwnd)
        def local(r):
            return (r[0]-left,r[1]-upper,r[2],r[3])
        scores=detect_plot_roles(im,local(top),local(bottom))
    except Exception:
        return None
    if scores.role=="UNKNOWN":
        return None
    # Contrast for SUM line is presentation-only; NEVER changes source
    # identity, 3/3 native tick, role validation or Y-axis provenance.
    x,y,_,_=local(top)
    header=np.asarray(im.crop((x+14,y+5,x+96,y+19)).convert("RGB"))
    theme="light" if float(np.median(header))>=175. else "dark"
    return (Plots(top,bottom,time.perf_counter(),theme) if scores.role=="PHASE_TOP"
            else Plots(bottom,top,time.perf_counter(),theme))
