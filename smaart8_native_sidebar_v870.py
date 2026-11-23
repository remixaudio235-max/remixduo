"""Smaart 8: place RemiX Duo LIKE V9, without covering native TF controls.

Read-only window geometry; Smaart 8 API3 does not expose screen rectangles.
The TF control stack ends below its Tab/Track row; the previous V8.69
+310px anchor overlapped that row. This V8-specific slot starts 380/1040
of the host height and ends before the Signal Generator section.
"""
from dataclasses import dataclass, field
from dock_geometry_v815 import DockRects
from dock_tiers_v8122 import choose_dock_tier,FULL_PAGE_H


@dataclass(frozen=True)
class V8Slot:
    """Free area inside Smaart 8's TF sidebar panel (screen coordinates)."""
    top:int
    bottom:int
    # V8.122: bottom border of TF engine 1 (screen y); -1 = not measured.
    engine1_bottom:int=-1
    # R5.9: top of verified first native TF engine in screen pixels.
    # Avoid estimating the engine's position from screen scaling.
    engine1_top:int=field(default=-1,compare=False)


def _slot_from_engines(band,boxes,t,y0,sy):
    """V8.122: free slot from the measured engine-box chain.

    Below the last engine the panel background must run plainly until the
    thin separator line above Signal Generator. Anything else there is
    unknown content -> None (fail closed, never cover it).
    """
    import numpy as np
    from dock_tiers_v8122 import leading_chain
    chain=leading_chain(boxes,max_gap=round(16*sy))
    if not chain:
        return None
    last=chain[-1].bottom
    probe=last+3
    if probe>=y0+band.shape[0]:
        return None
    bg=band[probe-y0].mean(axis=0)
    i=probe-y0
    while i<band.shape[0]:
        row=band[i]
        if np.abs(row.mean(axis=0)-bg).max()>6 or row.std()>12:
            break
        i+=1
    if i>=band.shape[0]:
        return None
    sep=i
    while sep<band.shape[0] and (np.abs(band[sep].mean(axis=0)-bg).max()>6
                                 or band[sep].std()>12):
        sep+=1
    if sep-i>round(14*sy):
        return None          # not a thin separator line: unknown content
    gen_top=y0+i
    return V8Slot(t+last+round(8*sy),t+gen_top-round(6*sy),
                  t+chain[0].bottom,t+chain[0].top)


def detect_v8_slot(image,host):
    """V8.120: measure where Smaart 8's native TF controls really end.

    Smaart 8 exposes no UIA tree (one Pane), and each TF engine adds a box
    below the Tab/Track row, so a fixed 380/1040 anchor covered the engine
    box (live: Duo dock over "TUNNING"). Scan the sidebar column of a
    PrintWindow frame: the panel background is uniform; the first long
    uniform run after the controls is the free slot, ending at the dark
    separator above Signal Generator. Returns None when not unambiguous.
    """
    import numpy as np
    l,t,r,b=map(int,host)
    w,h=r-l,b-t
    sx,sy=w/1920.,h/1040.
    arr=np.asarray(image.convert("RGB"),dtype=np.int16)
    # V8.181: native Smaart 8 sidebar retains about 195 physical pixels at
    # 1366x768; blindly multiplying 185 by window_width/1920 samples
    # the plot edge instead of the sidebar on a different PC / DPI.
    sidebar_probe_w=max(185,round(185*sx))
    x0,x1=w-sidebar_probe_w,w-max(15,round(15*sx))
    y0,y1=round(160*sy),h-round(150*sy)
    if x1-x0<60 or y1-y0<200 or arr.shape[0]<y1 or arr.shape[1]<x1:
        return None
    band=arr[y0:y1,x0:x1]
    from dock_tiers_v8122 import detect_engine_boxes
    boxes=detect_engine_boxes(image,x0,x1,y0,y1,sy)
    if boxes:
        # V8.122: coloured engine boxes measured -> exact slot + engine 1.
        return _slot_from_engines(band,boxes,t,y0,sy)
    means=band.mean(axis=1)
    stds=band.std(axis=(1,2))
    bg=np.median(means,axis=0)
    plain=(np.abs(means-bg).max(axis=1)<=6)&(stds<=12)
    need=max(40,round(40*sy))
    seen_content=False;run_start=None
    for i,is_plain in enumerate(plain):
        if not is_plain:
            if run_start is not None and i-run_start>=need and seen_content:
                top=t+y0+run_start+round(8*sy)
                bottom=t+y0+i-round(6*sy)
                return V8Slot(top,bottom) if bottom-top>=115 else None
            seen_content=True;run_start=None
        elif run_start is None:
            run_start=i
    return None


def read_v8_slot(hwnd):
    import win32gui
    from full_scan_v7 import printwindow_image
    host=win32gui.GetWindowRect(hwnd)
    return detect_v8_slot(printwindow_image(hwnd),host)


def v8_sidebar_rects(host,screen,slot=None):
    l,t,r,b=map(int,host)
    sl,st,sr,sb=map(int,screen)
    w,h=r-l,b-t
    # Width scaling keeps proportions of the native Smaart 8 right sidebar.
    sx=w/1920.
    sy=h/1040.
    # Smaart's right TF native controls are not guaranteed to scale with
    # *window width*. At 1366x768 they remain ~195px wide. Preserve a
    # minimum native sidebar width while staying within the host.
    sidebar_left=r-max(201,round(201*sx))
    toolbar_h=max(24,round(30*sy))
    toolbar_y=t+round(65*sy)
    full_x=sidebar_left-205-8
    full_possible=(w>=1250 and h>=720 and
                   full_x>=max(l+160,sl+3) and full_x+205<sidebar_left)
    if full_possible:
        toolbar=(full_x,toolbar_y,205,toolbar_h)
        tmode="full"
    else:
        toolbar=(max(l+4,sidebar_left-72),toolbar_y,68,toolbar_h)
        tmode="menu"

    # Native Smaart 8 controls: TF title through Tab/Track row (~350px
    # from top at 1920x1040). Reserve 30px after native controls.
    panel_top=t+round(380*sy)
    # V8.181: on a 1366x768 host the native TF engine spans roughly
    # y=362..415 (screenshot). The old y=281 dock overlays the engine.
    # Reserve the first TF engine on short screens. If a measured native
    # slot is supplied below, it takes precedence over this fallback.
    if w<=1440 and h<=800:
        panel_top=max(panel_top,t+round(570*sy))
    generator_top=b-round(244*sy)
    panel_bottom=generator_top-round(22*sy)
    tier="dock"
    if isinstance(slot,V8Slot):
        # V8.120: measured free slot below the real engine boxes.
        panel_top,panel_bottom=slot.top,slot.bottom
        # V8.122: 3-tier layout. < 200 px free -> overlap engines 2..N,
        # starting right after TF engine 1 (user-approved 2026-11-12).
        tier=choose_dock_tier(panel_bottom-panel_top)
        if tier=="overlap":
            if slot.engine1_bottom>=0:
                panel_top=slot.engine1_bottom+round(6*sy)
            else:
                tier="compact"
    # A 1366-wide host previously produced 139px here, then tripped the
    # >=145px safe gate: toolbar visible, ALL Auto Phase/EQ/FIR docks hidden.
    # Minimum 160px yields 156px after window border margins, while
    # staying inside the native TF sidebar on 1366x768.
    native_width=max(160,round(195*sx))
    panel_left=r-native_width-5
    panel_width=min(native_width,sr-panel_left-4,r-panel_left-3)
    safe=(
        w>=1100 and h>=690 and
        panel_left>=sidebar_left and
        panel_left>=sl+3 and panel_width>=145 and
        panel_top>=st+4 and panel_bottom<=sb-4 and
        panel_bottom-panel_top>=115
    )
    # R5.9: the R5.7 floating fallback at X=sidebar_left-213 covered the
    # measured Magnitude plot at 1366x768 and 1376x760. On a compact Smaart
    # 8 host the user specifically wants the tools at the TOP-RIGHT in the
    # Smaart sidebar column (like their screenshot), never on the TF plots.
    #
    # The vertical portion ends BEFORE the first verified native TF engine.
    # Native TF settings beneath the tools are temporarily obscured, but
    # Smaart's generator, first engine, Phase/Mag plots remain visible.
    # HIDE restores access to all original TF settings immediately.
    # This function ONLY places visual widgets: no change to tick/Export
    # or the independent pixel authorization.
    compact_host=(w>=1100 and h>=620 and
                  (w<1800 or h<980 or not safe))
    if compact_host:
        right_col_left=sidebar_left+2
        right_col_end=min(r-3,sr-3)
        right_col_width=right_col_end-right_col_left
        top=max(t+round(78*sy),st+4)
        if isinstance(slot,V8Slot) and slot.engine1_top>=0:
            engine_top=slot.engine1_top
            anchor_verified=True
        elif isinstance(slot,V8Slot) and slot.engine1_bottom>=0:
            # Historical slot objects have only the engine bottom. Subtract
            # the maximum native box height, not an optimistic average.
            engine_top=slot.engine1_bottom-max(45,round(90*sy))
            anchor_verified=False
        else:
            # No verified engine: a short top dock instead of a floating
            # panel on Magnitude, bounded well above the generator.
            engine_top=t+round(420*sy)
            anchor_verified=False
        bottom=min(engine_top-8,sb-6,b-8)
        panel_h=bottom-top
        if (right_col_width>=180 and panel_h>=195 and
                right_col_left>=sidebar_left and
                right_col_end<=r-2 and top>=st+4):
            return DockRects(
                toolbar,(right_col_left,top,right_col_width,panel_h),
                tmode,"v8-top-right-compact",anchor_verified,"compact")
        # If the native column itself cannot hold a usable panel, preserve
        # fail-closed behavior instead of drawing on Phase/Magnitude.
        return DockRects(toolbar,(0,0,0,0),tmode,
                         "no-native-space",False,"compact")

    if not safe:
        # Never fall back to R5.7's floating-on-Magnitude branch.
        # If no safe top-right column exists, leave the native plots visible
        # and keep the RemiX toolbar accessible instead.
        return DockRects(toolbar,(0,0,0,0),tmode,
                         "no-native-space",False,tier)
    # V8.122: up to the full Auto Phase page; shorter docks use the
    # compact page (RightToolDock) instead of cutting Top 3.
    panel_height=min(FULL_PAGE_H,panel_bottom-panel_top)
    panel=(panel_left,panel_top,panel_width,panel_height)
    mode="v8-overlap" if tier=="overlap" else "v8-native-sidebar"
    return DockRects(toolbar,panel,tmode,mode,True,tier)
