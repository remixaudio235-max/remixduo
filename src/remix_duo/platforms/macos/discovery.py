"""Public AppKit + Quartz window discovery; no process/window mutations."""
import math
import os
from ..contracts import WindowRef,WindowState

def select_windows(apps, windows, front_pid, companion_pid=None):
    known={a['pid']:a for a in apps if
           a.get('bundle')=='com.rationalacoustics.smaart' and
           a.get('started') and str(a.get('version','')).split('.')[0] in ('8','9')}
    result=[]
    for w in windows:
        app=known.get(w.get('pid'));rect=w.get('rect',())
        if (app is None or w.get('layer')!=0 or not w.get('id') or len(rect)!=4 or
            not all(math.isfinite(x) for x in rect) or rect[2]<300 or rect[3]<200):
            continue
        result.append(WindowState(WindowRef('darwin',w['pid'],str(app['started']),str(w['id'])),
            tuple(map(float,rect)),str(w.get('title','')),w['pid']==front_pid,
            bool(w.get('onscreen')),str(app['version']),
            companion_pid is not None and companion_pid>0 and front_pid==companion_pid))
    return sorted(result,key=lambda w:(not w.foreground,not w.on_screen,-w.rect[2]*w.rect[3]))

def list_windows():
    import AppKit
    import Quartz as Q
    workspace=AppKit.NSWorkspace.sharedWorkspace()
    front=workspace.frontmostApplication()
    front_pid=int(front.processIdentifier()) if front else -1
    apps=[]
    for app in workspace.runningApplications():
        if str(app.bundleIdentifier())!='com.rationalacoustics.smaart':continue
        date=app.launchDate();url=app.bundleURL()
        bundle=AppKit.NSBundle.bundleWithURL_(url) if url else None
        info=bundle.infoDictionary() if bundle else {}
        apps.append(dict(pid=int(app.processIdentifier()),
            started=str(date.timeIntervalSince1970()) if date else '',
            bundle=str(app.bundleIdentifier()),version=str(info.get('CFBundleShortVersionString',''))))
    rows=[]
    for item in Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionAll,Q.kCGNullWindowID) or []:
        bounds=item.get(Q.kCGWindowBounds,{})
        rows.append(dict(pid=int(item.get(Q.kCGWindowOwnerPID,-1)),id=int(item.get(Q.kCGWindowNumber,0)),
            layer=int(item.get(Q.kCGWindowLayer,-1)),onscreen=bool(item.get(Q.kCGWindowIsOnscreen,False)),
            title=str(item.get(Q.kCGWindowName,'')),
            rect=tuple(float(bounds.get(k,0)) for k in ('X','Y','Width','Height'))))
    return select_windows(apps,rows,front_pid,os.getpid())

def current_window(ref):
    return next((w for w in list_windows() if w.ref==ref),None)
