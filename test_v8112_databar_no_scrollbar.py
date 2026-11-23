"""V8.112: short Data Bar (all rows fit) has NO UIA ScrollBar.

Observed live 2026-11-11 (Smaart Suite 9, 7 traces): UIA exposes Tree
(L9,T163,R189,B317) with 7 'Level 0 row N' items and zero ScrollBar, so
_uia raised "Smaart Data Bar scrollbar missing" and ticks never verified.
Without a scrollbar the rows' own Tree is the viewport and scroll is fixed 0;
nothing is ever scrolled.
"""
from types import SimpleNamespace as NS
import pytest
import full_scan_v7 as scanner
from full_scan_v7 import ScanError


def rect(l,t,r,b):
    return NS(left=l,top=t,right=r,bottom=b,height=lambda:b-t,width=lambda:r-l)


def fake_root(with_bar,n=7,bar_left=180,bar_bottom=900):
    tree=NS(rectangle=lambda:rect(9,163,189,163+22*n),
            element_info=NS(control_type="Tree"))
    rows=[]
    for i in range(n):
        r=rect(9,163+22*i,231,185+22*i)
        rows.append(NS(element_info=NS(name=f"Level 0 row {i}"),
                       rectangle=(lambda r=r:r),parent=lambda:tree))
    bars=[NS(rectangle=lambda:rect(bar_left,160,bar_left+9,bar_bottom))] if with_bar else []
    def descendants(control_type):
        return {"ScrollBar":bars,"TreeItem":rows,"Tree":[tree]}.get(control_type,[])
    return NS(descendants=descendants,rectangle=lambda:rect(0,0,1920,1032))


def patch_root(monkeypatch,root):
    monkeypatch.setattr(scanner,"Desktop",
        lambda backend:NS(window=lambda handle:root))


def test_no_scrollbar_uses_row_tree_as_static_viewport(monkeypatch):
    patch_root(monkeypatch,fake_root(False))
    _,bar,rows=scanner._uia(1)
    assert len(rows)==7
    br=bar.rectangle()
    assert (br.top,br.bottom)==(163,163+22*7)
    rng=bar.iface_range_value
    assert rng.CurrentValue==0 and rng.CurrentMaximum==0
    assert not rng.CurrentIsReadOnly
    rng.SetValue(0)                       # restore/first page: harmless no-op
    with pytest.raises(ScanError):rng.SetValue(120)   # never fake a scroll


def test_scrollbar_path_unchanged(monkeypatch):
    root=fake_root(True)
    patch_root(monkeypatch,root)
    _,bar,_=scanner._uia(1)
    assert bar.rectangle().bottom==900


def test_scrollbar_search_follows_per_monitor_200_percent_dpi(monkeypatch):
    """A clean launch on a 200% laptop must not keep the old 150% cap."""
    root=fake_root(True,bar_left=450,bar_bottom=880)
    patch_root(monkeypatch,root)
    monkeypatch.setattr(scanner.ctypes.windll.user32,"GetDpiForWindow",
                        lambda hwnd:192)
    _,bar,_=scanner._uia(1)
    assert bar.rectangle().left==450


def test_no_rows_and_no_scrollbar_still_fails_closed(monkeypatch):
    patch_root(monkeypatch,fake_root(False,n=0))
    with pytest.raises(ScanError):scanner._uia(1)
