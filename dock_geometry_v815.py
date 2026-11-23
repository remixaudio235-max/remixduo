"""RemiX Signal V8.18 — responsive Smaart row and workspace geometry.

Uses read-only UIAutomation anchors when available. Window moves/resizes
apply immediately by projecting last known anchors. Does not invoke Smaart
actions. Missing anchors/small windows fall back to a visible RemiX menu,
not to hiding the entire app. True minimized/hidden Smaart is managed by UI.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from dock_tiers_v8122 import (choose_dock_tier,detect_engine_boxes,
                              trailing_chain,TIER_COMPACT_MIN)
from uia_serial_v8152 import serialized_uia

Rect=tuple[int,int,int,int]

@dataclass(frozen=True)
class SidebarAnchors:
    tf_bottom:int
    view_top:int
    sidebar_left:int
    real_time:Optional[Rect]=None
    impulse:Optional[Rect]=None
    spl:Optional[Rect]=None
    host_at_scan:Optional[Rect]=None
    # V8.122: bottom border of TF engine 1 (screen y), -1 = not measured.
    engine1_bottom:int=-1

@dataclass(frozen=True)
class DockRects:
    toolbar:Rect                     # x,y,w,h
    panel:Rect                       # x,y,w,h -- always available
    toolbar_mode:str                 # full | compact | mini | menu
    panel_mode:str                   # dock | compact | floating | overlap
    anchors_valid:bool
    layout_tier:str="dock"           # V8.122: dock | compact | overlap


def engine1_bottom_from_frame(image,native,tf):
    """V8.122 Suite: bottom of TF engine 1 from a PrintWindow frame.

    Smaart 9 UIA has no engine-box rectangles. The engine boxes are the
    coloured-border chain stacked directly above "+ TF Engine" (live: 8 px
    gap). Returns a screen y, or -1 when the chain is not unambiguous.
    """
    l,t=native[0],native[1]
    scale=(native[3]-native[1])/1040.
    x0,x1=tf[0]-l+10,tf[2]-l-10
    tf_top=tf[1]-t
    boxes=detect_engine_boxes(image,x0,x1,0,tf_top,scale)
    chain=trailing_chain(boxes,tf_top,max_gap=round(16*scale))
    return t+chain[0].bottom if chain else -1

@serialized_uia
def read_smaart_anchors(hwnd)->Optional[SidebarAnchors]:
    """Never click native controls. Missing TF/View is not fatal."""
    try:
        import win32gui
        from pywinauto import Desktop
        if not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):return None
        native=win32gui.GetWindowRect(hwnd)
        root=Desktop(backend="uia").window(handle=hwnd)
        found={}
        for el in root.descendants(control_type="Button"):
            name=(el.window_text() or "").strip()
            if name not in {"+ TF Engine","- TF Engine","View",
                            "Real Time","Impulse","SPL"}:
                continue
            r=el.rectangle()
            found[name]=(r.left,r.top,r.right,r.bottom)
        # UIA traversal is not atomic: moving/resizing Smaart during it can
        # combine controls from the new position with the old host rectangle.
        # Retain the previous coherent anchors and project those immediately.
        if (not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd) or
                win32gui.GetWindowRect(hwnd)!=native):
            return None
        tf=found.get("+ TF Engine",found.get("- TF Engine"))
        view=found.get("View")
        rt=found.get("Real Time")
        impulse=found.get("Impulse")
        spl=found.get("SPL")
        row_ok=all((rt,impulse,spl))
        if row_ok:
            row_ok=(rt[0]<rt[2]<=impulse[0]<impulse[2]<=spl[0]<spl[2]
                    and max(rt[1],impulse[1],spl[1])-min(rt[1],impulse[1],spl[1])<=4
                    and max(rt[3],impulse[3],spl[3])-min(rt[3],impulse[3],spl[3])<=4
                    and 20<=rt[3]-rt[1]<=44)
        if not row_ok:
            # Retain window data for fallback. Do not invent a valid row.
            rt=impulse=spl=None
        engine1=-1
        if tf and view and view[1]-5-(tf[3]+4)<TIER_COMPACT_MIN:
            # V8.122: only when the dock is short (many engines) pay for a
            # PrintWindow frame to find TF engine 1 for the overlap tier.
            try:
                from full_scan_v7 import printwindow_image
                engine1=engine1_bottom_from_frame(
                    printwindow_image(hwnd),native,tf)
            except Exception:
                engine1=-1
        return SidebarAnchors(tf[3] if tf else -1,
                              view[1] if view else -1,
                              min(tf[0]-8,view[0]) if tf and view else -1,
                              rt,impulse,spl,native,engine1)
    except Exception:
        return None

def choose_toolbar_mode(available:int)->tuple[str,int]:
    if available>=205:return "full",205
    if available>=148:return "compact",148
    if available>=105:return "mini",105
    return "menu",68

def _screen_clamp(value,lo,hi):
    return max(lo,min(value,hi))

def compute_dock_rects(host:Rect,anchors:Optional[SidebarAnchors],
                       screen:Rect,width:int=205)->Optional[DockRects]:
    l,t,r,b=host
    sl,st,sr,sb=screen
    # A truly off-screen/minimized/degenerate host cannot meaningfully dock.
    if r-l<140 or b-t<150 or sr-sl<70 or sb-st<120 or b<=st or t>=sb:
        return None
    # V8.157: V8Slot belongs to a different Smaart 8 geometry reader.
    # Do not let a cross-edition stale anchor crash Qt placement.
    native=(anchors.host_at_scan
            if isinstance(anchors,SidebarAnchors) else None)
    valid=bool(native and anchors.real_time and anchors.impulse and anchors.spl)
    if valid:
        # Immediately track top/right Smaart border motions before next UIA poll.
        dx=r-native[2]
        dy=t-native[1]
        rx=anchors.real_time[0]+dx
        ry=anchors.real_time[1]+dy
        rh=anchors.real_time[3]-anchors.real_time[1]
    else:
        # Transient UIA failure: short fallback on Smaart's top-chrome row.
        # Visible RemiX menu rather than silently disappearing.
        rx=r-165
        ry=t+65
        rh=30
    toolbar_left_bound=max(sl+2,l+3)
    available=rx-3-toolbar_left_bound
    mode,tw=choose_toolbar_mode(available)
    if not valid:
        # UIA row missing: show safe menu until native buttons verified.
        mode,tw="menu",68
    toolbar_x=rx-tw-3
    if toolbar_x<sl+2:
        toolbar_x=sl+2
    if toolbar_x+tw>sr-2:
        toolbar_x=max(sl+2,sr-tw-2)
    if mode=="menu" and available<68:
        # When native row truly cannot hold even 68px, keep a visible
        # menu near its row as far left as screen permits. It may cover
        # a narrow piece of the plot, but never the native RT button.
        toolbar_x=max(sl+2,min(rx-tw-3,sr-tw-2))
    toolbar_y=_screen_clamp(ry,st+1,sb-max(rh,24)-2)
    toolbar_h=max(24,min(rh,36))
    toolbar=(int(toolbar_x),int(toolbar_y),int(tw),int(toolbar_h))

    # Determine panel dimensions. Always keep at least a compact scrolling
    # workspace (subject only to physical screen geometry).
    panel_width=min(width,max(125,sr-sl-8))
    if (r+panel_width+5<=sr-3):
        # Smaart resized narrow: float outside its right edge when possible.
        panel_x=r+5
        outside=True
    elif l-panel_width-5>=sl+3 and r-l<520:
        panel_x=l-panel_width-5
        outside=True
    else:
        panel_x=_screen_clamp(r-panel_width-3,sl+2,sr-panel_width-2)
        outside=False
    if native and anchors.tf_bottom>=0:
        dy=t-native[1]
        dock_y=anchors.tf_bottom+dy+4
    else:
        dock_y=toolbar_y+toolbar_h+6
    if native and anchors.view_top>=0:
        # View row is normally bottom-anchored, so use bottom displacement.
        view_y=anchors.view_top+(b-native[3])
    else:
        view_y=b-110
    dock_y=_screen_clamp(dock_y,st+2,sb-100)
    available_h=min(view_y-5,b-110,sb-3)-dock_y
    # V8.122: 3-tier layout by free height below the last engine.
    tier=choose_dock_tier(available_h)
    engine1=anchors.engine1_bottom if native else -1
    if tier=="overlap" and engine1>=0:
        # Not enough room: cover engines 2..N, starting after TF engine 1.
        dock_y=_screen_clamp(engine1+(t-native[1])+4,st+2,sb-100)
        available_h=min(view_y-5,b-110,sb-3)-dock_y
    elif tier=="overlap":
        tier="compact"    # engine 1 unknown: never cover unmeasured engines
    if tier=="overlap" and available_h>=90:
        mode_panel="overlap"
        panel_h=min(560,available_h)
    elif available_h>=190:
        mode_panel="dock"
        panel_h=min(560,available_h)
    elif available_h>=90:
        mode_panel="compact"
        panel_h=available_h
    else:
        mode_panel="floating"
        # Use a scrolling popout above the native generator controls when
        # available; otherwise float into visible monitor space.
        if outside:
            dock_y=_screen_clamp(toolbar_y+toolbar_h+8,st+2,sb-180)
        else:
            dock_y=_screen_clamp(max(t+100,toolbar_y+toolbar_h+8),
                                 st+2,sb-180)
        panel_h=min(305,sb-dock_y-3)
    panel_h=max(92,int(panel_h))
    panel=(int(panel_x),int(dock_y),int(panel_width),int(panel_h))
    return DockRects(toolbar,panel,mode,mode_panel,valid,tier)
