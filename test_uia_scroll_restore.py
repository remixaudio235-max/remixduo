import time
from pywinauto import Desktop
w=Desktop(backend="uia").window(title="Smaart Suite")
b=w.descendants(control_type="ScrollBar")[0]
range_=b.iface_range_value
start=float(range_.CurrentValue)
print("START_SCROLL",start,"MAX",range_.CurrentMaximum,"READ_ONLY",range_.CurrentIsReadOnly,flush=True)
try:
    r=range_.SetValue(min(start+220,range_.CurrentMaximum))
    time.sleep(.14)
    after=float(range_.CurrentValue)
    print("SET_SCROLL",r,"ACTUAL",after,flush=True)
finally:
    range_.SetValue(start)
    time.sleep(.12)
    print("RESTORE",range_.CurrentValue,flush=True)
