"""Read-only visible-page sampling. Never full_scan, scroll or tick anything."""
from collections import Counter
import json,time,statistics,sys
from pathlib import Path
import win32gui,win32process,psutil
from full_scan_v7 import _uia,_page,printwindow_image
from selection_v7 import archive_order
from smaart_runtime_paths_v868 import trace_directory

hwnd=986302
for pid in (30288,25288):
    p=psutil.Process(pid)
    print(json.dumps(dict(pid=pid,cwd=p.cwd(),exe=p.exe())),flush=True)
windows=[]
def visit(h,_):
    _,pid=win32process.GetWindowThreadProcessId(h)
    if pid==25288: windows.append(dict(hwnd=h,title=win32gui.GetWindowText(h),
                                     visible=bool(win32gui.IsWindowVisible(h))))
win32gui.EnumWindows(visit,None)
print('DUO_WINDOWS',json.dumps(windows),flush=True)
print('START_UIA',flush=True)
root,bar,rows=_uia(hwnd)
order=archive_order(trace_directory(9))
print('UIA_ROWS',len(rows),'FILES',len(order),flush=True)
if len(rows)!=len(order): raise RuntimeError('ROW_FILE_COUNT_MISMATCH')
samples=[]
for index in range(int(sys.argv[1]) if len(sys.argv)>1 else 20):
    start=time.perf_counter()
    l,t,r,b=win32gui.GetWindowRect(hwnd)
    br=bar.rectangle()
    offset0=float(bar.iface_range_value.CurrentValue)
    frame=printwindow_image(hwnd)
    offset1=float(bar.iface_range_value.CurrentValue)
    states=_page(frame,order,offset1,0,br.top-t,br.bottom-t,0,
                 uia_rows=rows,window_origin=(l,t))
    ticks=[str(order[i].name) for i,v in states.items() if v=='on']
    row=dict(sample=index,ms=round((time.perf_counter()-start)*1000,2),
             visible_rows=len(states),unknown=sum(v=='unknown' for v in states.values()),
             visible_ticks=ticks,scroll_stable=abs(offset0-offset1)<=.5,
             global_selection_verified=len(states)==len(order) and all(v in ('on','off') for v in states.values()))
    samples.append(row)
    print(json.dumps(row,ensure_ascii=True),flush=True)
    if index==0:
        frame.save(str(Path(__file__).with_name('V882_NATIVE_TICK_READONLY.png')))
    time.sleep(.2)
print('SUMMARY',json.dumps(dict(samples=len(samples),
    patterns=dict(Counter(tuple(s['visible_ticks']) for s in samples)) if False else
    [dict(ticks=list(k),count=v) for k,v in Counter(tuple(s['visible_ticks']) for s in samples).items()],
    median_ms=statistics.median(s['ms'] for s in samples),
    max_ms=max(s['ms'] for s in samples),
    verified_global=sum(s['global_selection_verified'] for s in samples))),flush=True)
