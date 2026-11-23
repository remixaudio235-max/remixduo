"""Smaart Windows 9.6.4 read-only Data Bar capture and optional full-scan.

Uses documented Win32 PrintWindow and UI Automation RangeValue scroll.
Changes only *temporary UI scroll*, restores in finally. Does NOT tick
traces, modify data files, call signal generator, patch or inject Smaart.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import ctypes,time,win32gui,win32ui
import numpy as np
from PIL import Image
from pywinauto import Desktop
from selection_v7 import archive_order,scan_icon_white_cross,icon_color
from uia_serial_v8152 import serialized_uia

class ScanError(RuntimeError):pass

@dataclass(frozen=True)
class Scanned:
    active:tuple[str,...]
    total:int
    covered:int
    captures:int
    scroll_start:float
    scroll_end:float
    elapsed_s:float
    states:tuple[str,...]=()

def _image_looks_blank(image)->bool:
    """V8.113: blank-frame test on a sparse 1/64 sample.

    std() over the full frame allocated a ~45 MB float64 array on every
    0.16 s poll; under low commit memory that raised MemoryError and turned
    tick scans transient. A blank/black PrintWindow frame is uniform, so a
    sparse grid detects it equally well.
    """
    small=image.reduce(8) if hasattr(image,"reduce") else image
    return float(np.asarray(small,dtype=np.uint8).std())<3.0

def printwindow_image(hwnd):
    l,t,r,b=win32gui.GetWindowRect(hwnd)
    width,height=r-l,b-t
    if not(600<width<10000 and 400<height<10000):raise ScanError("bad Smaart bounds")
    hdc=win32gui.GetWindowDC(hwnd)
    dc=win32ui.CreateDCFromHandle(hdc)
    mem=dc.CreateCompatibleDC()
    bmp=win32ui.CreateBitmap()
    old_bitmap=None
    try:
        bmp.CreateCompatibleBitmap(dc,width,height)
        old_bitmap=mem.SelectObject(bmp)
        result=ctypes.windll.user32.PrintWindow(hwnd,mem.GetSafeHdc(),2)
        if not result:raise ScanError("PrintWindow did not draw Smaart")
        raw=bmp.GetBitmapBits(True)
        image=Image.frombuffer("RGB",(width,height),raw,"raw","BGRX",0,1).copy()
        if _image_looks_blank(image):
            raise ScanError("Smaart window image appears blank")
        return image
    finally:
        # A bitmap still selected in mem DC cannot be deleted. Re-select
        # the original handle BEFORE DeleteObject, including on PrintWindow errors.
        try:
            if old_bitmap is not None:mem.SelectObject(old_bitmap)
        except Exception:pass
        try:win32gui.DeleteObject(bmp.GetHandle())
        except Exception:pass
        try:mem.DeleteDC()
        except Exception:pass
        finally:
            # GetWindowDC is owned by ReleaseDC, NOT DeleteDC.
            # Always release even if CreateBitmap/PrintWindow/cleanup fails.
            win32gui.ReleaseDC(hwnd,hdc)

def _uia(hwnd):
    root=Desktop(backend="uia").window(handle=hwnd)
    bars=root.descendants(control_type="ScrollBar")
    # Scrollbar gutter moves with Smaart's DPI scaling. The old 260px
    # threshold silently misses the *real* Data Bar scrollbar at 150%,
    # then invents a static viewport beyond the bottom of the window.
    dpi=int(ctypes.windll.user32.GetDpiForWindow(hwnd))
    # Follow the host's real per-monitor DPI.  Capping this at 150% made a
    # clean launch on 175-400% displays search the unscaled left gutter and
    # silently fall back to a fake non-scrollable Data Bar.
    dpi_scale=(dpi/96.0) if 72<=dpi<=384 else 1.0
    root_rect=root.rectangle()
    limit_x=root_rect.left+int(round(260*dpi_scale))
    min_height=int(round(180*dpi_scale))
    bar=next((b for b in bars if
              b.rectangle().height()>min_height and
              root_rect.left<=b.rectangle().left<limit_x),None)
    rows=root.descendants(control_type="TreeItem")
    m={}
    for el in rows:
        title=el.element_info.name or ""
        if "Level 0 row " not in title:continue
        try:n=int(title.split("row ")[1].split()[0])
        except (ValueError,IndexError):continue
        m[n]=el
    # Never guess a -1 shift. Accept only a complete zero- or one-based sequence.
    labels=sorted(m)
    if labels==list(range(len(m))):
        pass
    elif labels==list(range(1,len(m)+1)):
        m={k-1:v for k,v in m.items()}
    else:
        raise ScanError(f"UIA row indices are not contiguous: {labels[:5]}")
    if bar is None:
        # V8.112: a short Data Bar (all rows fit) exposes no ScrollBar.
        # Use the rows' own Tree as a fixed viewport; scrolling is impossible.
        if not m:raise ScanError("Smaart Data Bar scrollbar missing")
        try:tree=m[0].parent().rectangle()
        except Exception as exc:
            raise ScanError("Smaart Data Bar list missing") from exc
        if tree.bottom>root.rectangle().bottom+2:
            raise ScanError("Data Bar scrollbar not found: tree extends beyond host")
        bar=_StaticDataBar(tree)
    return root,bar,m


class _StaticRange:
    """UIA RangeValue stand-in for a Data Bar without scrollbar: fixed at 0."""
    CurrentValue=0.
    CurrentMaximum=0.
    CurrentIsReadOnly=False
    def SetValue(self,value):
        if abs(float(value))>.5:
            raise ScanError("Data Bar has no scrollbar; refusing to fake a scroll")


class _StaticDataBar:
    def __init__(self,rect):
        self._rect=rect
        self.iface_range_value=_StaticRange()
    def rectangle(self):
        return self._rect

def _visible_uia_window(uia_rows,count,top,bottom,window_origin,guess,row_height=22):
    """V8.108: rows fully inside [top,bottom] by their OWN UIA rectangles.

    Level-0 Data Bar rows are ordered top->bottom by index, so starting at an
    estimated index and walking outward until a row leaves the viewport visits
    only ~visible rows (+2) instead of querying every row's rectangle (each a
    cross-process UIA call). Returns None -> caller falls back to the full loop
    (missing indices, UIA error, or non-monotonic geometry).
    """
    if count<=0 or any(i not in uia_rows for i in range(count)):return None
    ox,oy=window_origin
    cache={}
    def geo(i):
        if i not in cache:
            rect=uia_rows[i].rectangle()
            cache[i]=(rect.top-oy,rect.bottom-oy,
                      rect.left-ox+int(round(7*row_height/22.)))
        return cache[i]
    inside=lambda i:geo(i)[0]>=top-0.5 and geo(i)[1]<=bottom+0.5
    try:
        i=min(max(int(guess),0),count-1)
        while geo(i)[0]<top-0.5 and i<count-1:i+=1
        while geo(i)[1]>bottom+0.5 and i>0:
            i-=1
            if geo(i)[0]<top-0.5:break
        if not inside(i):return {}
        lo=hi=i
        while lo>0 and inside(lo-1):lo-=1
        while hi<count-1 and inside(hi+1):hi+=1
        ys=[geo(k)[0] for k in range(lo,hi+1)]
        if any(b<=a for a,b in zip(ys,ys[1:])):return None
    except Exception:
        return None
    return {k:(geo(k)[0],geo(k)[2]) for k in range(lo,hi+1)}

def _page(img,order,scroll,first_y,top,bottom,icon_left,
          row_height=22,*,uia_rows=None,window_origin=(0,0),colors=None):
    """Classify each trace using its *own* native UIA rectangle (not inferred rows).

    V8.123: when `colors` is a dict, colors[i] receives the icon colour.
    """
    found={}
    def classify(i,rect):
        if img is None:
            return 'unknown'
        if colors is not None:
            # Colour is cosmetic: it must never break tick classification.
            try:
                color=icon_color(img,rect)
            except Exception:
                color=None
            if color:colors[i]=color
        # A 15px direct crop clips a 28px glyph at 200% DPI and can
        # misread the folded white corner as an OFF cross. Use the full,
        # row-bounded adaptive glyph locator when UIA pitch is scaled.
        state=(scan_icon_white_cross(img,rect)
               if uia_rows is None or row_height<=25 else "unknown")
        if state=="unknown" and uia_rows is not None:
            # V8.181: on compact 1366x768 or mixed DPI, the UIA TreeItem
            # rectangle can be offset by a few logical pixels from the
            # PrintWindow file glyph. Search only its OWN row gutter.
            from databar_icon_geometry_v8181 import classify_uia_row_gutter
            row_y=int(rect[1])-3
            expected_x=int(rect[0])
            # UIA row text/top can be displaced 1-3 px relative to the
            # colored glyph after a DPI scaling change. Require agreement
            # of at least TWO shifted native crops before allowing a tick.
            # No match/contradiction -> UNKNOWN, never invent zero ticks.
            shifts=tuple(sorted({int(round(shift*max(.60,row_height/22.)))
                                 for shift in (0,1,2,3)}))
            candidates=[classify_uia_row_gutter(img,row_y+shift,
                                                  expected_x,row_height)
                        for shift in shifts]
            accepted=[x for x in candidates if x in ("on","off")]
            state=(accepted[0] if len(accepted)>=2 and
                   all(x==accepted[0] for x in accepted) else "unknown")
        return state
    if uia_rows is not None:
        # Actual row geometry is in native pixels. The scrollbar RangeValue
        # may use logical units, so never use it to guess a pixel row index.
        try:
            current_row0=uia_rows[0].rectangle().top-window_origin[1]
            guess=(top-current_row0)/max(1,row_height)
        except Exception:
            guess=0
        window=_visible_uia_window(uia_rows,len(order),top,bottom,window_origin,
                                   guess,row_height)
        if window is not None:
            for i,(rowy,x) in window.items():
                found[i]=classify(i,(x,rowy+3,x+15,rowy+18))
            return found
        for i,item in uia_rows.items():
            if not 0<=i<len(order): continue
            try:
                rect=item.rectangle()
                rowy=rect.top-window_origin[1]
                x=rect.left-window_origin[0]+int(round(7*row_height/22.))
            except Exception:
                continue
            if rowy < top-0.5 or rowy+18 > bottom+0.5: continue
            icon=classify(i,(x,rowy+3,x+15,rowy+18))
            found[i]=icon
        return found
    for i,_ in enumerate(order):
        rowy=first_y+i*row_height-scroll
        if rowy<top-0.5 or rowy+18>bottom+0.5:continue
        icon=classify(i,(icon_left,rowy+3,icon_left+15,rowy+18))
        found[i]=icon
    return found

@serialized_uia
def full_scan(hwnd,folder,*,max_pages=16,uia=None)->Scanned:
    st=time.perf_counter()
    # V8.108: initialize() passes its single UIA tree walk (was walked twice).
    root,bar,rows=_uia(hwnd) if uia is None else uia
    order=archive_order(Path(folder))
    if len(order)!=len(rows):
        raise ScanError(f"UIA rows {len(rows)} != stored TRF {len(order)}")
    if not len(order):raise ScanError("no stored traces")
    l,t,r,b=win32gui.GetWindowRect(hwnd)
    br=bar.rectangle()
    rng=bar.iface_range_value
    scroll_start=float(rng.CurrentValue)
    max_scroll=float(rng.CurrentMaximum)
    if rng.CurrentIsReadOnly:raise ScanError("UIA scrollbar is read-only")
    # Anchor each row to original index, not its position inside the viewport.
    row0=rows[0].rectangle()
    # Measure actual row pitch from UIA (do not assume 22px).
    if len(rows) >= 2:
        row_height = max(12, min(40, rows[1].rectangle().top - rows[0].rectangle().top))
    else:
        row_height = 22
    first_y=row0.top-t+scroll_start
    top=br.top-t;bottom=br.bottom-t
    icon_left=row0.left-l+int(round(7*row_height/22.))
    visited={}
    pages=0
    end=-1.
    try:
        # V8.108: rows are classified by their own UIA rects, so a 2-row
        # overlap suffices (was 32 % overlap -> ~25 % more scroll pages).
        # Coverage is still proven: every row must be seen or ScanError.
        step=max(120,int((bottom-top)-2*row_height))
        targets=list(range(0,int(max_scroll)+1,step))
        targets.append(int(max_scroll))
        if len(targets)>max_pages:raise ScanError("too many scan pages")
        # Window resizes / DPI reflow can leave ScrollBar.RangeValue and
        # TreeItem rectangles momentarily inconsistent. Verify visibility of
        # the actual *boundary* row before recording each page. We never
        # treat stale pixels or cached tick values as a valid state.
        def capture_settled(goal, *, require_first=False, require_last=False):
            last_reason = "no stable frame"
            for attempt in range(5):
                rng.SetValue(float(goal))
                stable = 0
                previous = None
                for _ in range(15):
                    time.sleep(.06)
                    pos = float(rng.CurrentValue)
                    actual = rows[0].rectangle().top-t
                    sample=(round(pos,1),round(actual,1))
                    if sample==previous:
                        stable+=1
                        if stable>=2:
                            break
                    else:
                        stable=0
                    previous=sample
                if stable<2:
                    last_reason="scroll/row0 have not stabilized"
                    continue
                # A 'SetValue(0)' which leaves row0 above the list is not
                # sufficient just because CurrentValue is stable.
                def inside(index):
                    rect = rows[index].rectangle()
                    return rect.top-t >= top-2 and rect.bottom-t <= bottom+2
                if require_first and not inside(0):
                    last_reason = "first row not scrolled into viewport"
                    continue
                if require_last and not inside(len(order)-1):
                    last_reason = "last row not scrolled into viewport"
                    continue
                time.sleep(.08)
                image = printwindow_image(hwnd)
                page = _page(image,order,pos,first_y,top,bottom,icon_left,row_height,
                             uia_rows=rows,window_origin=(l,t))
                if not page or any(s not in ('on','off') for s in page.values()):
                    last_reason = "image icons incomplete/ambiguous"
                    continue
                conflicts = [idx for idx,state in page.items()
                             if idx in visited and visited[idx] != state]
                if conflicts:
                    last_reason = f"conflicting tick proof at rows {conflicts}"
                    continue
                return page
            raise ScanError(f"Data Bar did not settle at goal={goal}: {last_reason}")

        for goal in targets:
            page = capture_settled(goal,require_first=(goal==0),
                                   require_last=(goal==int(max_scroll) and
                                                 max_scroll>0))
            visited.update(page)
            pages += 1
        # A shrinking Data Bar may cause the original top-page request
        # to be clamped or not painted until another UIA layout pass.
        # Retry missing boundary coverage, never infer missing rows OFF.
        if len(visited)!=len(order):
            missing=set(range(len(order)))-set(visited)
            if min(missing)==0:
                page = capture_settled(0,require_first=True)
                visited.update(page)
                pages += 1
            if len(visited)!=len(order):
                missing=set(range(len(order)))-set(visited)
                if max(missing)==len(order)-1:
                    page = capture_settled(int(max_scroll),require_last=True)
                    visited.update(page)
                    pages += 1
        # Some Smaart scrollbar Max is beyond last row usable offset;
        # this is okay if every actual row has been seen with certainty.
        if len(visited)!=len(order):
            raise ScanError(f"Incomplete Data Bar: {len(visited)}/{len(order)} rows; missing={sorted(set(range(len(order)))-set(visited))}")
        active=tuple(str(order[i]) for i,v in sorted(visited.items()) if v=="on")
        # A complete scan can legitimately find zero, one or multiple ticks.
        # The caller must fail closed unless exactly two are active.
    finally:
        rng.SetValue(scroll_start)
        time.sleep(.09)
        end=float(rng.CurrentValue)
        if abs(end-scroll_start)>.25:
            raise ScanError(f"Restore scroll FAILED {scroll_start} -> {end}")
    return Scanned(active,len(order),len(visited),pages,scroll_start,end,
                   time.perf_counter()-st,tuple(visited[i] for i in range(len(order))))


