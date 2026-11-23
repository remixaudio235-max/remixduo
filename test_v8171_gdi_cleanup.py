"""V8.171 regression: GDI ownership/ReleaseDC even when cleanup fails."""
from types import SimpleNamespace
import pytest
import full_scan_v7 as scan
import smaart_native_mag_fit as mag

@pytest.mark.parametrize("module", [scan,mag],ids=["databar","native_magnitude"])
def test_window_dc_release_on_failed_print_and_delete_dc(monkeypatch,module):
    events=[]
    old_bitmap=object()
    class BMP:
        def CreateCompatibleBitmap(self,dc,w,h): events.append("makebitmap")
        def GetHandle(self):return 789
    class MEM:
        def SelectObject(self,bitmap):
            events.append("select-old" if bitmap is old_bitmap else "select-bitmap")
            return old_bitmap
        def GetSafeHdc(self):return 456
        def DeleteDC(self):
            events.append("delete-memory-dc")
            raise RuntimeError("DeleteDC failed")
    class DC:
        def CreateCompatibleDC(self):return MEM()
        def DeleteDC(self):raise AssertionError("must not DeleteDC an acquired window DC")
    monkeypatch.setattr(module.win32gui,"GetWindowRect",lambda hwnd:(0,0,1920,1080))
    monkeypatch.setattr(module.win32gui,"GetWindowDC",lambda hwnd:123)
    monkeypatch.setattr(module.win32gui,"DeleteObject",lambda bmp:events.append("delete-bitmap"))
    monkeypatch.setattr(module.win32gui,"ReleaseDC",
                        lambda hwnd,hdc:events.append("release-window-dc"))
    monkeypatch.setattr(module.win32ui,"CreateDCFromHandle",lambda raw:DC())
    monkeypatch.setattr(module.win32ui,"CreateBitmap",lambda:BMP())
    monkeypatch.setattr(module,"ctypes",SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(PrintWindow=lambda *args:0))))
    with pytest.raises(Exception) as caught: 
        module.printwindow_image(777) if module is scan else module.capture_native_window(777)
    assert "PrintWindow" in str(caught.value)
    assert events.count("select-bitmap")==1
    assert events.count("select-old")==1
    assert events.index("select-old")<events.index("delete-bitmap")
    assert events[-1]=="release-window-dc"
