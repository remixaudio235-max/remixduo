"""V8.18 responsive UI QA; no Smaart resize/click or audio I/O."""
from dataclasses import replace
from pathlib import Path
import win32gui
from PyQt6.QtWidgets import QApplication
from dock_geometry_v815 import *
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf
app=QApplication([])
out=Path(__file__).resolve().parent
screen=(0,0,1920,1040)
host=(0,0,1920,1000)
anchor=SidebarAnchors(
    tf_bottom=520,view_top=860,sidebar_left=1730,
    real_time=(1755,66,1820,96),impulse=(1822,66,1870,96),
    spl=(1872,66,1910,96),host_at_scan=host)
real=compute_dock_rects(host,anchor,screen)
assert real and real.toolbar_mode=="full"
assert real.toolbar[1]==anchor.real_time[1]
assert real.toolbar[0]+real.toolbar[2]+3==anchor.real_time[0]
print("ANCHOR_NATIVE_FULL_PASS",real,flush=True)
engine=App(False);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop()
h=win32gui.FindWindow(None,"Smaart Suite")
native=read_smaart_anchors(h)
print("NATIVE_SMAART_ANCHOR",native,flush=True)
if native and native.real_time:
    r=win32gui.GetWindowRect(h)
    measured=compute_dock_rects(r,native,screen)
    print("LIVE_LAYOUT",r,measured,flush=True)
    assert measured is not None

samples=[
    ("full",920,"full"),
    ("compact",360,"compact"),
    ("mini",300,"mini"),
    ("menu",250,"menu"),
    ("tiny",190,"menu"),
]
for label,w,expected in samples:
    host2=(100,80,100+w,720)
    rt_left=host2[2]-165
    ac=SidebarAnchors(
        tf_bottom=490,view_top=625,sidebar_left=rt_left-4,
        real_time=(rt_left,145,rt_left+65,175),
        impulse=(rt_left+67,145,rt_left+115,175),
        spl=(rt_left+117,145,rt_left+155,175),host_at_scan=host2)
    rr=compute_dock_rects(host2,ac,screen)
    assert rr is not None,(label,w)
    assert rr.toolbar_mode==expected,(label,rr)
    assert rr.panel is not None
    assert rr.toolbar[1]==ac.real_time[1]
    assert rr.panel[1]+rr.panel[3]<=screen[3]
    hub._anchors=ac
    hub._last_host_rect=host2
    assert hub._update_placements(host2)
    app.processEvents()
    assert hub._toolbar_mode==expected,(label,hub._toolbar_mode)
    assert hub.width()==rr.toolbar[2]
    assert hub.isVisible() and hub.dock.isVisible()
    assert hub.dock.scroll.verticalScrollBarPolicy().name=="ScrollBarAsNeeded"
    assert hub.dock.scroll.horizontalScrollBarPolicy().name=="ScrollBarAsNeeded"
    if expected=="menu":
        assert hub.menu_button.isVisible()
        assert all(not b.isVisible() for b in hub.buttons.values())
        assert len(hub.menu_button.menu().actions())==3
        for i,expected_mode in enumerate(("phase","eq","fir")):
            hub.menu_button.menu().actions()[i].trigger()
            assert hub.active==expected_mode
        hub.select("phase")
    else:
        assert not hub.menu_button.isVisible()
        assert all(b.isVisible() for b in hub.buttons.values())
    if label in ("full","mini","menu","tiny"):
        assert hub.grab().save(str(out/f"V818_TOOLBAR_{label}.png"))
        assert hub.dock.grab().save(str(out/f"V818_PANEL_{label}.png"))
    for mode in ("eq","fir","phase"):
        hub.select(mode);app.processEvents()
        assert hub.active==mode and hub.dock.stack.currentWidget() is hub.pages[mode]
        assert hub.isVisible() and hub.dock.isVisible()
    print("RESPONSIVE_MODE_PASS",label,w,expected,rr.panel_mode,flush=True)
# Same host rect while TF Engine shrinks/collapses, tiny tool + workspace live.
host2=(320,125,900,650)
ac=SidebarAnchors(-1,-1,725,
    (735,188,800,218),(802,188,850,218),(852,188,890,218),host2)
rr=compute_dock_rects(host2,ac,screen)
assert rr and rr.panel is not None
print("MISSING_TF_VIEW_STILL_VISIBLE_PASS",rr,flush=True)
# Transient native UIA outage must leave a usable menu and workspace.
rr=compute_dock_rects(host2,None,screen)
assert rr and rr.panel is not None and rr.toolbar_mode=="menu"
print("MISSING_NATIVE_ANCHORS_FALLBACK_PASS",rr,flush=True)
# Specific small portrait-ish window where native TF/View gap <90px:
host3=(200,60,620,400)
ac=SidebarAnchors(310,360,455,
    (455,120,520,150),(522,120,570,150),(572,120,610,150),host3)
rr=compute_dock_rects(host3,ac,screen)
assert rr and rr.panel is not None and rr.panel_mode=="floating"
assert rr.panel[1]+rr.panel[3]<=screen[3]
print("SHORT_HEIGHT_FLOATING_PANEL_PASS",rr,flush=True)
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(data/n) for n in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(a.path),str(b.path))
engine.current_traces=(a,b)
engine.recalc();engine.align()
assert abs(engine.delay.value()-13.2)<.2
hub.select("eq");hub.eq.compute()
assert hub.eq.result is not None
hub.select("fir");hub.fir.compute()
assert hub.fir.result is not None
hub.select("phase")
assert abs(engine.delay.value()-13.2)<.2
print("AUTO_PHASE_EQ_FIR_DATA_PRESERVED_PASS",flush=True)
hub.close()
app.processEvents()
print("V818_RESPONSIVE_QA_ALL_PASS",flush=True)
