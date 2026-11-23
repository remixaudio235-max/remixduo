"""Native Smaart V9 108-row read verification after old duplicate processes stop.

Do not start Generator, touch audio devices or write TRF files.
The initial full scan scrolls Data Bar briefly and restores its scroll.
"""
import sys,time
from pathlib import Path
from win_databar_v7 import locate_smaart
from live_sync_v7 import LiveDataBarV7
import win32gui
target=locate_smaart()
assert target and win32gui.IsWindow(target.hwnd) and not win32gui.IsIconic(target.hwnd), "Smaart must be visible and not minimized"
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
reader=LiveDataBarV7(data)
for i in range(3):
    result=reader.poll(target.hwnd)
    print("LIVE_POLL",i,repr(result.status),
          "VERIFIED",result.verified,"TOTAL",result.rows,
          "PAIR",tuple(Path(x).name for x in result.pair) if result.pair else None,
          flush=True)
    if i==0:
        assert result.rows>=100 and result.verified==result.rows
        assert result.pair and len(result.pair)==2,("Expected exactly 2 checked traces",result)
        assert set(Path(x).name for x in result.pair)=={
            "4,8 ms delay-1.trf","0 delay-1.trf"}, "Live ticks differ from the previously validated pair"
    else:
        assert result.pair==initial
        assert result.verified==result.rows
    initial=result.pair
    time.sleep(.23)
print("V823_NATIVE_SMAART_108_ROW_PAIR_AND_POLL_PASS",flush=True)
