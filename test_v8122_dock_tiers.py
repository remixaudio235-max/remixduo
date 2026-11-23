"""V8.122: 3-tier automatic dock when Smaart has many TF engines.

User-approved 2026-11-12. Free height below the LAST engine box:
>= 400 dock below it; 200..400 compact page; < 200 overlap engines 2..N
starting right after TF engine 1.

Real frames (user's live screenshots 2026-11-12, plot left of x=1640
blanked): Smaart 8 with 3 engines (the Duo dock rectangle repainted with the
panel row above it, since a PrintWindow frame never contains Duo) and Smaart
Suite with 5 engines. Engine counts beyond the real frames are synthesized by
copying real engine-box rows.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image

from dock_tiers_v8122 import (choose_dock_tier,detect_engine_boxes,
                              FULL_PAGE_H)
from smaart8_native_sidebar_v870 import detect_v8_slot,v8_sidebar_rects,V8Slot
from dock_geometry_v815 import (SidebarAnchors,compute_dock_rects,
                                engine1_bottom_from_frame)

FIX=Path(__file__).with_name("fixtures")
HOST=(0,0,1920,1032)
S8_1=FIX/"smaart8_sidebar_1engine_1920x1032.png"
S8_3=FIX/"smaart8_sidebar_3engines_1920x1032.png"
S9_5=FIX/"smaart9_suite_sidebar_5engines_1920x1032.png"
SUITE_TF=(1730,639,1910,662)     # "+ TF Engine" button on the Suite frame


def _rows(path):
    return np.asarray(Image.open(path).convert("RGB")).copy()


def _s8_more_engines(extra):
    """Real 3-engine frame + `extra` copies of real engine 2 (54 rows, 7 gap)."""
    a=_rows(S8_3)
    box=a[423:477].copy()
    y=545
    for _ in range(extra):
        a[y:y+54]=box
        y+=61
    return Image.fromarray(a)


def _s8_taller(path,extra_rows):
    """Taller Smaart 8 window: insert plain panel rows in the free slot."""
    a=_rows(path)
    filler=np.repeat(a[600:601],extra_rows,axis=0)
    return Image.fromarray(np.vstack([a[:600],filler,a[600:]]))


# ---------------------------------------------------------------- tiers
def test_tier_thresholds():
    assert choose_dock_tier(560)=="dock"
    assert choose_dock_tier(400)=="dock"
    assert choose_dock_tier(399)=="compact"
    assert choose_dock_tier(200)=="compact"
    assert choose_dock_tier(199)=="overlap"
    assert choose_dock_tier(-20)=="overlap"


def test_engine_boxes_on_real_frames():
    s8=detect_engine_boxes(Image.open(S8_3),1735,1905,150,1000,1032/1040)
    assert [(b.top,b.bottom) for b in s8]==[(362,415),(423,476),(484,537)]
    s9=detect_engine_boxes(Image.open(S9_5),1740,1900,150,1000,1032/1040)
    assert [b.bottom for b in s9]==[387,448,509,570,631]
    # The coloured trace curves / meter box are never taken as engines.
    assert detect_engine_boxes(Image.open(S8_1),1735,1905,150,1000)[0].top==362


# ------------------------------------------------------------ Smaart 8
def test_smaart8_tier1_dock_below_last_engine():
    tall=_s8_taller(S8_1,160)
    host=(0,0,1920,1032+160)
    slot=detect_v8_slot(tall,host)
    assert slot is not None and slot.engine1_bottom>=0
    assert slot.bottom-slot.top>=400
    rects=v8_sidebar_rects(host,host,slot)
    assert rects.layout_tier=="dock" and rects.panel_mode=="v8-native-sidebar"
    assert rects.panel[1]==slot.top
    assert rects.panel[3]==FULL_PAGE_H         # full Auto Phase page fits


def test_smaart8_tier2_compact_real_3_engines():
    slot=detect_v8_slot(Image.open(S8_3),HOST)
    assert slot==V8Slot(545,801,415)
    rects=v8_sidebar_rects(HOST,HOST,slot)
    assert rects.layout_tier=="compact"
    px,py,pw,ph=rects.panel
    assert py==545 and py+ph<=801 and ph<FULL_PAGE_H
    assert py>537                               # below engine 3, no overlap


def test_smaart8_tier3_overlap_after_engine1():
    slot=detect_v8_slot(_s8_more_engines(2),HOST)      # 5 engines
    assert slot is not None and slot.engine1_bottom==415
    assert slot.bottom-slot.top<200
    rects=v8_sidebar_rects(HOST,HOST,slot)
    assert rects.layout_tier=="overlap" and rects.panel_mode=="v8-overlap"
    px,py,pw,ph=rects.panel
    assert 415<py<=425                          # right after TF engine 1
    assert py+ph<=slot.bottom                   # never over Signal Generator
    assert ph>=200


def test_smaart8_full_sidebar_still_overlaps_after_engine1():
    slot=detect_v8_slot(_s8_more_engines(4),HOST)      # 7 engines, no gap
    assert slot is not None and slot.engine1_bottom==415
    rects=v8_sidebar_rects(HOST,HOST,slot)
    assert rects.layout_tier=="overlap" and rects.anchors_valid


def test_smaart8_unknown_content_below_engines_fails_closed():
    a=_rows(S8_3)
    a[560:600,1735:1900]=(160,160,160)          # not an engine, not a separator
    assert detect_v8_slot(Image.fromarray(a),HOST) is None


# ---------------------------------------------------------------- Suite
def _suite_anchors(tf_bottom,view_top,engine1=-1,native=HOST):
    rt=(1500,64,1560,92);imp=(1562,64,1620,92);spl=(1622,64,1660,92)
    return SidebarAnchors(tf_bottom,view_top,1720,rt,imp,spl,native,engine1)


def test_suite_engine1_from_real_5_engine_frame():
    assert engine1_bottom_from_frame(Image.open(S9_5),HOST,SUITE_TF)==387
    # TF button not directly under the chain -> no guess.
    assert engine1_bottom_from_frame(Image.open(S9_5),HOST,
                                     (1730,760,1910,783))==-1


def test_suite_tier1_dock():
    r=compute_dock_rects(HOST,_suite_anchors(420,900),HOST)
    assert r.layout_tier=="dock" and r.panel_mode=="dock"
    assert r.panel[1]==424 and r.panel[3]>=400


def test_suite_tier2_compact():
    r=compute_dock_rects(HOST,_suite_anchors(560,900,engine1=387),HOST)
    assert r.layout_tier=="compact"
    assert r.panel[1]==564 and 200<=r.panel[3]<400   # still below last engine


def test_suite_tier3_overlap_real_live_geometry():
    # Live 5-engine Suite: "+ TF Engine" bottom 662; dock had ~190 px.
    engine1=engine1_bottom_from_frame(Image.open(S9_5),HOST,SUITE_TF)
    r=compute_dock_rects(HOST,_suite_anchors(662,862,engine1),HOST)
    assert r.layout_tier=="overlap" and r.panel_mode=="overlap"
    px,py,pw,ph=r.panel
    assert py==387+4                            # right after TF engine 1
    assert py+ph<=862-5                         # above the View row
    assert ph>=FULL_PAGE_H


def test_suite_overlap_needs_measured_engine1():
    r=compute_dock_rects(HOST,_suite_anchors(662,862,-1),HOST)
    assert r.layout_tier=="compact" and r.panel[1]==666   # never guesses


def test_suite_overlap_follows_window_move():
    moved=(0,40,1920,1072)
    r=compute_dock_rects(moved,_suite_anchors(662,862,387),(0,0,1920,1080))
    assert r.layout_tier=="overlap" and r.panel[1]==387+40+4


# --------------------------------------------------------- Qt dock page
def _hub():
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    hub.select("phase")
    return app,engine,hub


def _place(hub,app,host,edition,anchors):
    hub._last_hwnd=123
    hub._last_host_edition=edition
    hub._last_host_rect=host
    hub._anchors=anchors
    with patch.object(hub,"_screen_rect",return_value=host):
        assert hub._update_placements(host)
    hub.dock.show()
    app.processEvents()


def test_qt_compact_page_shows_button_traces_and_top3_row():
    app,engine,hub=_hub()
    try:
        engine._set_tick_presentation(True)
        slot=detect_v8_slot(Image.open(S8_3),HOST)
        _place(hub,app,HOST,8,slot)
        assert hub._layout_tier=="compact"
        assert engine._compact_layout
        assert hub.dock.geometry().getRect()==v8_sidebar_rects(HOST,HOST,slot).panel
        assert engine.height()==engine.COMPACT_PAGE_H
        engine.layout().activate();app.processEvents()
        tops={b.mapTo(engine,b.rect().topLeft()).y() for b in engine.candidates}
        assert len(tops)==1                     # Top 3 on ONE row
        bottom=max(b.mapTo(engine,b.rect().bottomLeft()).y()
                   for b in engine.candidates)
        assert bottom<=engine.height()          # nothing cut off
        assert bottom+24<=hub.dock.height()     # visible without scrolling
        assert engine.solve.isVisible()
        assert all(w.isVisible() for w in engine.trace_name_labels)
    finally:
        hub.close();app.processEvents()


def test_qt_back_to_full_page_restores_column_and_400px():
    app,engine,hub=_hub()
    try:
        engine._set_tick_presentation(True)
        _place(hub,app,HOST,8,detect_v8_slot(Image.open(S8_3),HOST))
        assert engine._compact_layout
        tall=(0,0,1920,1032+160)
        _place(hub,app,tall,8,detect_v8_slot(_s8_taller(S8_1,160),tall))
        assert hub._layout_tier=="dock" and not engine._compact_layout
        assert engine.height()==400 and hub.dock.page_heights["phase"]==400
        col=engine.candidate_col
        assert all(col.indexOf(b)>=0 for b in engine.candidates)
        assert [col.indexOf(b) for b in engine.candidates]==sorted(
            col.indexOf(b) for b in engine.candidates)
        assert engine.candidate_row.count()==0
        assert engine.candidate_card.height()==167
        assert engine.trace_card.height()==138
    finally:
        hub.close();app.processEvents()


def test_qt_suite_overlap_places_dock_after_engine1():
    app,engine,hub=_hub()
    try:
        _place(hub,app,HOST,9,_suite_anchors(662,862,387))
        assert hub._panel_mode=="overlap" and hub._layout_tier=="overlap"
        assert hub.dock.heading.text()=="AUTO PHASE"
        assert hub.dock.y()==391
        # Overlap region is tall enough for the full page here.
        assert not engine._compact_layout
    finally:
        hub.close();app.processEvents()


def test_qt_compact_candidate_text_fits():
    from PyQt6.QtGui import QFontMetrics
    app,engine,hub=_hub()
    try:
        engine._set_tick_presentation(True)
        _place(hub,app,HOST,8,detect_v8_slot(Image.open(S8_3),HOST))
        button=engine.candidates[0]
        button.ensurePolished()
        assert button.font().pixelSize()==9     # compact stylesheet applied
        # 190 px page, card margins and 2x3 px spacing -> ~55 px per button.
        assert min(b.width() for b in engine.candidates)>=54
        if app.platformName()!="offscreen":
            # Offscreen Qt has no real font database (measures 81 px);
            # native Windows Segoe UI bold 9 px measured 40 px (2026-11-12).
            fm=QFontMetrics(button.font())
            assert max(fm.horizontalAdvance(t)
                       for t in ("#1 T2 INV","12.35 ms"))<=50
    finally:
        hub.close();app.processEvents()
