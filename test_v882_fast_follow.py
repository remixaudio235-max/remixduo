from types import SimpleNamespace
import signal_tools_gui_v813 as gui
import dock_geometry_v815 as geometry
import win32gui
import pywinauto
import pytest


@pytest.mark.parametrize('moving', [False, True])
def test_uia_anchor_snapshot_rejects_host_motion(monkeypatch, moving):
    host=(10,20,1210,820)
    calls=[]
    def rect(_):
        calls.append(1)
        return (30,40,1230,840) if moving and len(calls)>1 else host
    monkeypatch.setattr(win32gui,'IsWindow',lambda _:True)
    monkeypatch.setattr(win32gui,'IsIconic',lambda _:False)
    monkeypatch.setattr(win32gui,'GetWindowRect',rect)
    def control(name, box):
        return SimpleNamespace(window_text=lambda:name, rectangle=lambda:
            SimpleNamespace(left=box[0],top=box[1],right=box[2],bottom=box[3]))
    controls=[control('Real Time',(1000,70,1070,100)),
              control('Impulse',(1072,70,1140,100)),
              control('SPL',(1142,70,1190,100))]
    root=SimpleNamespace(descendants=lambda **_:controls)
    monkeypatch.setattr(pywinauto,'Desktop',lambda **_:SimpleNamespace(window=lambda **_:root))
    result=geometry.read_smaart_anchors(123)
    if moving:
        assert result is None, 'Mixed host/control coordinates must never replace coherent anchors'
    else:
        assert result.host_at_scan==host
        assert result.real_time==(1000,70,1070,100)


def test_fast_follow_uses_only_native_rect_and_preserves_size_projection(monkeypatch):
    calls=[]
    host=(40,50,1400,900)
    fake=SimpleNamespace(_last_hwnd=123,_last_host_rect=(0,0,1920,1040),
        engine=SimpleNamespace(_target_is_foreground=lambda _:True),
        _update_placements=lambda rect:calls.append(rect))
    monkeypatch.setattr(gui.win32gui,'IsWindow',lambda _:True)
    monkeypatch.setattr(gui.win32gui,'IsIconic',lambda _:False)
    monkeypatch.setattr(gui.win32gui,'GetWindowRect',lambda _:host)
    # Any UIA discovery/trace poll here would fail this deliberately tiny object.
    gui.ToolHub._fast_follow(fake)
    assert calls==[host]
    gui.ToolHub._fast_follow(fake)
    assert calls==[host], 'Unchanged geometry must not trigger relayout'


def test_fast_follow_hides_minimized_host_without_touching_traces(monkeypatch):
    hidden=[]
    fake=SimpleNamespace(_last_hwnd=123,
        isVisible=lambda:True,hide=lambda:hidden.append('hub'),
        dock=SimpleNamespace(isVisible=lambda:True,hide=lambda:hidden.append('dock')))
    monkeypatch.setattr(gui.win32gui,'IsWindow',lambda _:True)
    monkeypatch.setattr(gui.win32gui,'IsIconic',lambda _:True)
    gui.ToolHub._fast_follow(fake)
    assert hidden==['hub','dock']
