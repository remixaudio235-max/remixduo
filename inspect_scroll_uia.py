import time
from pywinauto import Desktop
import win32gui
try:
    ds=Desktop(backend="uia").windows()
    found=[w for w in ds if "Smaart" in (w.window_text() or "")]
    print("WINDOWS",[(x.handle,x.window_text()) for x in found[:4]])
    if found:
        w=found[0]
        bars=w.descendants(control_type="ScrollBar")
        print("SCROLLBARS",len(bars))
        for i,b in enumerate(bars[:6]):
            print("BAR",i,"rect",b.rectangle(),"value",b.legacy_properties(),"patterns",b.get_properties())
            try:
                iface=b.iface_range_value
                print("RANGE",iface.CurrentValue,iface.Minimum,iface.Maximum,iface.SmallChange,iface.LargeChange,iface.IsReadOnly)
            except Exception as exc:print("NO_RANGE",type(exc).__name__,str(exc)[:150])
except Exception as e:
    print("ERROR",repr(e))
