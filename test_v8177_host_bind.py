"""Regression: Smaart 8/Suite HWND provenance must not change when the Qt toolbox has focus."""
from pathlib import Path
import win_databar_v7 as w
def _win(hwnd,foreground=False):
    return w.MainWindow(hwnd,(0,0,1920,1032),foreground)
def test_foreground_smaart_always_wins_over_bound_other_host():
    assert w.choose_smaart_host([_win(8),_win(9,True)],8).hwnd==9
    assert w.choose_smaart_host([_win(8,True),_win(9)],9).hwnd==8
def test_companion_focus_keeps_edition_binding():
    # Neither host is Windows foreground when native RemiX toolbar has focus.
    assert w.choose_smaart_host([_win(9),_win(8)],8).hwnd==8
    assert w.choose_smaart_host([_win(8),_win(9)],9).hwnd==9
def test_removed_or_foreign_hwnd_fails_closed():
    assert w.choose_smaart_host([_win(8),_win(9)],777).hwnd==8
    assert w.choose_smaart_host([_win(8),_win(9)],"9").hwnd==8
    assert w.choose_smaart_host([],9) is None
def test_window_enumeration_and_pid_identity_still_required(monkeypatch):
    import win32gui,win32process
    hwnds=(80,90,700)
    names={80:"Smaart",90:"Smaart Suite",700:"RemiX Duo"}
    pids={80:100,90:200,700:300}
    monkeypatch.setattr(win32gui,"EnumWindows",lambda cb,payload:[cb(h,payload) for h in hwnds])
    monkeypatch.setattr(win32gui,"IsWindowVisible",lambda h:True)
    monkeypatch.setattr(win32gui,"GetWindowText",lambda h:names[h])
    monkeypatch.setattr(win32gui,"GetWindowRect",lambda h:(0,0,1920,1032))
    monkeypatch.setattr(win32gui,"GetForegroundWindow",lambda:700)
    monkeypatch.setattr(win32process,"GetWindowThreadProcessId",lambda h:(1,pids[h]))
    monkeypatch.setattr(w,"_process_binary_name",lambda pid: {100:"smaart.exe",200:"smaart.exe",300:"remixduo.exe"}[pid])
    assert w.locate_smaart(prefer_hwnd=90).hwnd==90
    monkeypatch.setattr(win32gui,"GetForegroundWindow",lambda:80)
    assert w.locate_smaart(prefer_hwnd=90).hwnd==80
    monkeypatch.setattr(w,"_process_binary_name",lambda pid:"unknown.exe")
    assert w.locate_smaart(prefer_hwnd=90) is None
def test_both_view_and_hub_supply_verified_hwnd():
    source=Path(__file__).resolve().parent
    a=(source/"overlay_v7.py").read_text(encoding="utf-8")
    b=(source/"signal_tools_gui_v813.py").read_text(encoding="utf-8")
    assert a.count("locate_smaart(prefer_hwnd=")==2
    assert b.count("locate_smaart(prefer_hwnd=")==1
