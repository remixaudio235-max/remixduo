"""V8.108: Data Bar trace-list read is slow and scrolls up/down repeatedly.

Root causes (code): a failed initial full scan was retried on EVERY 0.16 s
poll (scroll storm); every page/poll queried the UIA rectangle of ALL rows;
initialize() walked the UIA tree twice; pages overlapped by 32 %.
Simulated Smaart Data Bar (no real window, no scrolling of Smaart).
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace as NS
import pytest

import full_scan_v7 as scanner
import live_sync_v7 as live
from full_scan_v7 import ScanError

N=108;PITCH=22;TOP=100;BOTTOM=430;WIN=(0,0,1920,1040)


class Sim:
    def __init__(self,states,start=440.):
        self.states=states
        self.value=float(start)
        self.maximum=float(N*PITCH-(BOTTOM-TOP))
        self.rect_calls=0
        self.setvalues=[]
        self.uia_walks=0
        sim=self
        class Rng:
            CurrentIsReadOnly=False
            @property
            def CurrentValue(s):return sim.value
            @property
            def CurrentMaximum(s):return sim.maximum
            def SetValue(s,v):
                sim.setvalues.append(v);sim.value=max(0.,min(sim.maximum,float(v)))
        self.bar=NS(iface_range_value=Rng(),
                    rectangle=lambda:NS(top=TOP,bottom=BOTTOM,left=10,
                                        height=lambda:BOTTOM-TOP))
        def item(i):
            def rect():
                sim.rect_calls+=1
                return NS(top=TOP+i*PITCH-sim.value,left=10)
            return NS(rectangle=rect)
        self.rows={i:item(i) for i in range(N)}

    def uia(self,hwnd):
        self.uia_walks+=1
        return object(),self.bar,self.rows

    def image(self,hwnd):
        # rowy -> state for rows inside the viewport at the current scroll
        return {TOP+i*PITCH-self.value:s for i,s in enumerate(self.states)}


@pytest.fixture
def sim(monkeypatch,tmp_path):
    states=["off"]*N;states[22]="on";states[30]="on"  # visible at scroll 440
    s=Sim(states)
    order=[tmp_path/f"{i:03d}.trf" for i in range(N)]
    for p in order:p.touch()
    for mod in (scanner,live):
        monkeypatch.setattr(mod,"_uia",s.uia,raising=False)
        monkeypatch.setattr(mod,"printwindow_image",s.image,raising=False)
        monkeypatch.setattr(mod,"archive_order",lambda folder:list(order),raising=False)
    monkeypatch.setattr(live,"fresh_unindexed_imports",lambda folder:())
    monkeypatch.setattr(scanner,"scan_icon_white_cross",
                        lambda img,box:img.get(box[1]-3,"unknown"))
    monkeypatch.setattr(scanner.win32gui,"GetWindowRect",lambda h:WIN)
    monkeypatch.setattr(live.win32gui,"GetWindowRect",lambda h:WIN)
    import smaart8_api3_readonly_v868 as api
    monkeypatch.setattr(api,"process_smaart_major",lambda h:9)
    s.order=order;s.folder=tmp_path
    return s


def test_full_scan_is_complete_and_restores_scroll(sim):
    result=scanner.full_scan(77,sim.folder,uia=sim.uia(77))
    assert result.covered==N
    assert result.states==tuple(sim.states)
    assert sim.value==440.


def test_full_scan_uses_fewer_pages_and_only_visible_row_queries(sim):
    result=scanner.full_scan(77,sim.folder,uia=sim.uia(77))
    visible=(BOTTOM-TOP)//PITCH+1
    # old: 11 pages x 108 UIA rect queries (~1190); new: ~visible per page
    assert result.captures<=9
    assert sim.rect_calls<=result.captures*(visible+6)+8, sim.rect_calls


def test_initialize_walks_uia_tree_once(sim):
    obs=live.LiveDataBarV7(sim.folder)
    result=obs.initialize(77)
    assert result.status.startswith("FULL SCAN ")
    assert sim.uia_walks==1
    assert obs.states[22]=="on" and obs.states[30]=="on" and obs.states[97]=="off"


def test_viewport_poll_queries_only_visible_rows(sim):
    obs=live.LiveDataBarV7(sim.folder)
    obs.initialize(77)
    sim.rect_calls=0
    result=obs.poll(77)
    assert result.status.startswith("Verified viewport")
    assert sim.rect_calls<=(BOTTOM-TOP)//PITCH+8, sim.rect_calls


def test_failed_full_scan_backs_off_instead_of_scrolling_every_poll(sim,monkeypatch):
    calls=[]
    clock={"t":100.}
    monkeypatch.setattr(live,"_backoff_now",lambda:clock["t"])
    def failing(hwnd,folder,**k):
        calls.append(clock["t"])
        raise ScanError("Visible tick icon ambiguous; no cached selection accepted")
    monkeypatch.setattr(live,"full_scan",failing)
    obs=live.LiveDataBarV7(sim.folder)
    for _ in range(20):            # 20 polls at 0.16 s = 3.2 s
        r=obs.poll(77)
        assert r.pair is None and not r.status.startswith(("Verified","FULL SCAN"))
        clock["t"]+=.16
    # old behaviour: 20 full scroll scans; new: first try + 1.5 s retry (+3 s)
    assert 2<=len(calls)<=3, calls
    assert calls[1]-calls[0]>=1.5


def test_backoff_resets_on_new_window_and_after_success(sim,monkeypatch):
    clock={"t":100.}
    monkeypatch.setattr(live,"_backoff_now",lambda:clock["t"])
    real=live.full_scan
    mode={"fail":True};calls=[]
    def maybe(hwnd,folder,**k):
        calls.append(hwnd)
        if mode["fail"]:raise ScanError("ambiguous")
        return real(hwnd,folder,**k)
    monkeypatch.setattr(live,"full_scan",maybe)
    obs=live.LiveDataBarV7(sim.folder)
    obs.poll(77);obs.poll(77)
    assert calls==[77]
    obs.poll(78)                   # different Smaart window: retry at once
    assert calls==[77,78]
    mode["fail"]=False
    clock["t"]+=2.
    r=obs.poll(78)
    assert r.status.startswith("FULL SCAN ") and obs.ready
    assert obs._init_failures==0
