"""Smaart v8 plot-role adapter for 3-panel Lin / Phase / Magnitude layouts.

Reference glyph masks were taken from the user-supplied 1920x1080 Smaart 8
screenshot on 2026-11-01; this is *not* an API geometry feature.
When DPI, theme, title or window layout fails verification, return None and
hide overlays instead of placing MagEq/FIR over Lin or the wrong graph.
"""
from __future__ import annotations
from dataclasses import dataclass
import base64,zlib,time
import numpy as np
from PIL import Image
import win32gui
from plot_geometry_v7 import locate_plots,Plots
from full_scan_v7 import printwindow_image
from smaart8_api3_readonly_v868 import process_smaart_major,cached_probe

# Binary text/glyph templates: (height,width, zlib(packbits(uint8 mask))).
_TEMPLATES={
 "LIN":(20,42,"eNpjYEAFAgIM8g/YGBjYfzA28jH8YUjwP2DPICFswN7AxsLC+ICxUZHBgKHOwYGHQb5BgIEEAACTewm8"),
 "PHASE":(22,63,"eNpjYMAO7EEE+w+GOgUgzf+B4VhFwcMD/AcYe35+fn5AvoH5o1AaR4McA/sh9fPzGWwYeFh82hUYDBgkOCab5TAkMCgw2NlUMFAdAAByuBRf"),
 "MAG":(23,112,"eNpjYBhIwCbBwMAEYtQ3AAl2EE+BQQHGS7zwqID5cYM9SAGrxsfPjwrUnx8A81g0hIWNFNRSHOTAvBWfhYQUVNQPQHidkwWElFRUGHjAvJMTPwgpp6UdgPBO/PwgZPz4cQPMAQLIrmH8gMJ7QJwfACKEHcQ="),
}
def title_template(role):
    h,w,compressed=_TEMPLATES[role]
    raw=zlib.decompress(base64.b64decode(compressed))
    return np.unpackbits(np.frombuffer(raw,dtype=np.uint8))[:h*w].reshape(h,w).astype(bool)

def _native_header_theme(image,rect):
    """Determine glyph polarity from the actual plot TITLE background.

    Black/dark titles use the original white glyph templates; white/light
    titles use dark neutral glyphs. Unknown/gray headers fail CLOSED.
    Theme is presentation metadata, never a source/tick identity shortcut.
    """
    x,y,w,h=map(int,rect)
    x0=max(0,x+16);x1=min(image.width,x+136)
    y0=max(0,y+4);y1=min(image.height,y+19)
    if x1<=x0 or y1<=y0:
        return None
    a=np.asarray(image.crop((x0,y0,x1,y1)).convert("RGB"),dtype=np.int16)
    low=float(np.median(a.min(axis=2)))
    if low>=175:
        return "light"
    if low<=125:
        return "dark"
    return None


def glyph_mask(image,theme="dark"):
    a=np.asarray(image.convert("RGB"),dtype=np.int16)
    hi=a.max(axis=2);lo=a.min(axis=2)
    if theme=="dark":
        return (lo>130)&((hi-lo)<45)
    if theme=="light":
        return (hi<135)&((hi-lo)<65)
    return np.zeros(lo.shape,dtype=bool)

def score_mask(template,observed):
    a=float(np.count_nonzero(template&observed))
    denom=np.sqrt(float(template.sum()*max(1,int(observed.sum()))))
    return a/denom if denom else 0.

def search_role(image,rect,role,*,theme=None):
    """Exact same inclusive search and mask score, vectorized over windows.

    The matching role and both original score/margin thresholds are unchanged.
    """
    if theme is None:
        theme=_native_header_theme(image,rect)
    if theme not in ("dark","light"):
        return 0.
    x,y,w,h=rect
    tpl=title_template(role)
    th,tw=tpl.shape
    iw,ih=image.size
    ymin=max(0,y-6)
    ymax=min(ih-th,y+28)
    xmin=max(0,x-6)
    xmax=min(iw-tw,x+38)
    if ymax<ymin or xmax<xmin:
        return 0.
    # Native title verification only needs this narrow ROI, not the full 1920x1032 frame.
    sub=glyph_mask(image.crop((xmin,ymin,xmax+tw,ymax+th)),theme)
    from scipy.signal import fftconvolve
    # Binary template correlation; rounded FFT integer hits stay identical
    # to the original exhaustive bitwise AND count.
    hits=np.rint(fftconvolve(sub.astype(np.float32),
                            tpl[::-1,::-1].astype(np.float32),mode="valid"))
    integral=np.pad(sub.astype(np.int32),((1,0),(1,0))).cumsum(0).cumsum(1)
    seen=(integral[th:,tw:]-integral[:-th,tw:]-
          integral[th:,:-tw]+integral[:-th,:-tw])
    denom=np.sqrt(float(tpl.sum())*np.maximum(1,seen))
    return float(np.max(hits/denom))

def detect_v8_roles(image,top,bottom):
    # Top and bottom must be real, identically sized frequency charts.
    if abs(top[0]-bottom[0])>15 or abs(top[2]-bottom[2])>15:
        return None
    if bottom[1] <= top[1]+top[3]:
        return None
    theme_top=_native_header_theme(image,top)
    theme_bottom=_native_header_theme(image,bottom)
    # Both native plot headers must independently agree on one theme.
    if theme_top is None or theme_top!=theme_bottom:
        return None
    a_phase=search_role(image,top,"PHASE",theme=theme_top)
    a_mag=search_role(image,top,"MAG",theme=theme_top)
    b_phase=search_role(image,bottom,"PHASE",theme=theme_top)
    b_mag=search_role(image,bottom,"MAG",theme=theme_top)
    if a_phase>=.68 and b_mag>=.68 and a_phase-a_mag>=.16 and b_mag-b_phase>=.16:
        return "PHASE_TOP"
    if a_mag>=.68 and b_phase>=.68 and a_mag-a_phase>=.16 and b_phase-b_mag>=.16:
        return "MAG_TOP"
    return None

def _compact_native_profile_candidates(width,height):
    """Smaart 8 compact geometry: FIXED native sidebars, flexible charts.

    The original 1920x1080 template scaled X positions by window width,
    but native Smaart 8 leaves its left 215px and right 231px margins
    effectively fixed. On 1366x720 the scaled guess wrongly started at
    x153 with width1048, while native plots are x215 width920.
    Return only geometry HYPOTHESES. Each must independently pass native
    Phase/Magnitude glyph roles and theme checks before use.
    """
    if not (1100<=width<=1800 and 620<=height<=970):
        return ()
    left=215
    width_plot=width-left-231
    if width_plot<640:
        return ()
    results=[]
    # Two observed Smaart 8 TF graph-stack modes. Footer Y margins stay
    # ~95px in the alternate profile and ~93px in the maximized profile.
    for top,base in ((87,206),(114,232)):
        chart_height=round((height-base)/2)
        bottom=top+chart_height+24
        if chart_height<210 or bottom+chart_height>height-40:
            continue
        results.append(((left,top,width_plot,chart_height),
                        (left,bottom,width_plot,chart_height)))
    return tuple(results)


def detect_v8_profile(image):
    """Return verified local Phase/Mag rectangles for known v8 layouts.

    Smaart 8 exposes no useful UIA descendants, so geometry cannot depend on
    ``locate_plots``.  Scale the two observed native profiles, then accept one
    only when the original Phase/Magnitude title glyphs independently verify
    both rectangles.  Unknown layouts remain fail-closed.
    """
    width,height=image.size
    # R64: physical 1680x1050 DISPLAY may expose a 1680x1002..1004
    # Smaart host bitmap when the Windows taskbar occupies the bottom.
    # The R62 test passed only the full-screen 1680x1050 screenshot and
    # missed this real work-area variant, falling through to a scaled
    # 1920-derived X=188 W=1290. Native LF source identity then rejected Y.
    #
    # Bind the verified fixed native plot geometry to viewport WIDTH and
    # a bounded taskbar/work-area height range. Geometry alone NEVER proves
    # the source: both Phase/Magnitude title glyphs must independently
    # verify before returning, and SUM Mag still separately requires actual
    # native source pixels, X-axis, fit score, coherency and complete tick.
    # Do not guess or loosen native Y, and do not affect other viewport widths.
    if width==1680 and 990<=height<=1060:
        r62_phase=(215,81,1234,405)
        r62_mag=(215,508,1234,405)
        role=detect_v8_roles(image,r62_phase,r62_mag)
        if role=="PHASE_TOP":return r62_phase,r62_mag
        if role=="MAG_TOP":return r62_mag,r62_phase
    # Try geometries following the native FIXED-width Smaart 8 sidebars
    # first. Unlike a 1920-based scale, they work with a short 1366 host.
    # A role is accepted ONLY after independent Phase/Mag title glyphs
    # corroborate BOTH candidate rectangles in this fresh native image.
    for upper,lower in _compact_native_profile_candidates(width,height):
        role=detect_v8_roles(image,upper,lower)
        if role=="PHASE_TOP":
            return upper,lower
        if role=="MAG_TOP":
            return lower,upper
    profiles=(
        # Native two-plot TF view (user frame 2026-11-15, 1920x1032).
        ((1920,1032),(215,114,1474,400),(215,538,1474,399)),
        # V8.159: native two-plot TF, Smaart 8 1920x1080 maximized.
        # Captured on 2026-11-16 HWND=2164554, actual source titles
        # scored Phase .925 / Magnitude .919 against independent glyphs.
        # Still fails closed if DPI, theme, or roles don't match.
        ((1920,1080),(215,87,1474,436),(215,548,1474,436)),
        # Native Lin + Phase + Mag view (calibration frame 1920x1080).
        ((1920,1080),(215,287,1470,313),(215,625,1470,315)),
    )
    for (rw,rh),upper,lower in profiles:
        sx,sy=width/rw,height/rh
        scale=lambda r:(round(r[0]*sx),round(r[1]*sy),
                        round(r[2]*sx),round(r[3]*sy))
        top,bottom=scale(upper),scale(lower)
        role=detect_v8_roles(image,top,bottom)
        if role=="PHASE_TOP":
            return top,bottom
        if role=="MAG_TOP":
            return bottom,top
    return None

def locate_v8_role_plots(hwnd):
    if process_smaart_major(hwnd)!=8:
        return None
    try:
        image=printwindow_image(hwnd)
        left,top,*_=win32gui.GetWindowRect(hwnd)
        # Prefer UIA if a future v8 build exposes verified canvases; current
        # v8.5 returns none and therefore uses the glyph-verified raster path.
        base=locate_plots(hwnd)
        if base is not None:
            def local(rect):
                return (rect[0]-left,rect[1]-top,rect[2],rect[3])
            top_rect,bottom_rect=base.phase,base.mag
            role=detect_v8_roles(image,local(top_rect),local(bottom_rect))
            if role=="PHASE_TOP":
                return Plots(base.phase,base.mag,time.perf_counter(),
                             _native_header_theme(image,local(top_rect)))
            if role=="MAG_TOP":
                return Plots(base.mag,base.phase,time.perf_counter(),
                             _native_header_theme(image,local(top_rect)))
        verified=detect_v8_profile(image)
    except (ValueError,TypeError,IndexError,OSError):
        return None
    if verified is None:return None
    phase,mag=verified
    theme=_native_header_theme(image,phase)
    if theme is None or _native_header_theme(image,mag)!=theme:
        return None
    screen=lambda r:(r[0]+left,r[1]+top,r[2],r[3])
    return Plots(screen(phase),screen(mag),time.perf_counter(),theme)

def locate_v8_role_plots_with_probe(hwnd):
    # The API does not locate plot rectangles. Probe read-only state but do not
    # make overlay depend on a disabled API for offline TRF display.
    result=locate_v8_role_plots(hwnd)
    if result is not None:
        cached_probe(hwnd)
    return result
