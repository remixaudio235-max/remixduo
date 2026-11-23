"""V8.107 READ-ONLY live blink monitor for the RemiX Duo overlay.

Samples, every ~15 ms, the visibility of the overlay's Mag/Phase QWidget
windows (the two top-level windows of the overlay PID whose rects sit on
Smaart's plots) and logs every hidden gap with its duration. It sends NO
input, never focuses, moves or captures any window, never touches Smaart.

Usage (while the user runs Auto Phase / Auto EQ / Auto FIR in Smaart):
  python qa_v8107_blink_monitor.py --seconds 180 --out blink_log.txt
A "blink" = a graph window that was visible, became hidden for < 2 s and
became visible again while Smaart stayed the foreground process.
"""
from __future__ import annotations
import argparse,time
import psutil,win32gui,win32process


def overlay_pids():
    pids=set()
    for p in psutil.process_iter(["name","cmdline"]):
        try:
            if any("overlay_v7" in a for a in (p.info["cmdline"] or [])):
                pids.add(p.pid)
        except (psutil.Error,OSError):
            continue
    return pids


def graph_windows(pids):
    found=[]
    def cb(h,_):
        _,pid=win32process.GetWindowThreadProcessId(h)
        if pid in pids and win32gui.GetClassName(h).startswith("Qt"):
            l,t,r,b=win32gui.GetWindowRect(h)
            if r-l>=600 and b-t>=250:   # plot-sized: graph_mag / graph_phase
                found.append(h)
    win32gui.EnumWindows(cb,None)
    return found


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seconds",type=float,default=180)
    ap.add_argument("--out",default="blink_log.txt")
    a=ap.parse_args()
    pids=overlay_pids()
    windows=graph_windows(pids)
    start=time.perf_counter();state={};hidden_at={};gaps=[];samples=0
    with open(a.out,"w",encoding="utf-8") as log:
        log.write(f"pids={sorted(pids)} windows={windows}\n")
        while time.perf_counter()-start<a.seconds:
            now=time.perf_counter()-start
            front=win32gui.GetForegroundWindow()
            try:fpid=win32process.GetWindowThreadProcessId(front)[1]
            except Exception:fpid=0
            for h in windows:
                vis=bool(win32gui.IsWindow(h) and win32gui.IsWindowVisible(h))
                prev=state.get(h)
                if prev is True and not vis:
                    hidden_at[h]=(now,fpid)
                elif prev is False and vis and h in hidden_at:
                    t0,f0=hidden_at.pop(h)
                    gap=now-t0
                    rect=win32gui.GetWindowRect(h)
                    gaps.append((h,t0,gap))
                    log.write(f"GAP hwnd={h} rect={rect} at={t0:.3f}s "
                              f"hidden={gap*1000:.0f}ms fg_pid={f0}->{fpid}\n")
                    log.flush()
                state[h]=vis
            samples+=1
            time.sleep(.015)
        short=[g for g in gaps if g[2]<2.0]
        log.write(f"SUMMARY samples={samples} gaps={len(gaps)} "
                  f"short_gaps_lt_2s={len(short)}\n")
    print(open(a.out,encoding="utf-8").read())


if __name__=="__main__":
    main()
