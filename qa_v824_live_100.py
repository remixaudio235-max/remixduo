"""V8.24 controlled native Smaart V9 100-poll stability audit.

Does NOT enable generator, audio I/O, measurement or TF Engine.
Smaart is temporarily restored if minimized, then its original minimized
state is reinstated. The Data Bar scan scrolls and restores its scrollbar.
Run only when all older RemiX Signal pollers are stopped.
"""
from pathlib import Path
from time import perf_counter,sleep
from collections import Counter
import json,win32gui
from win_databar_v7 import locate_smaart
from live_sync_v7 import LiveDataBarV7
from stable_ticks_v824 import StableTickGate

root=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd and win32gui.IsWindow(hwnd), "Smaart Suite not running"
was_minimized=bool(win32gui.IsIconic(hwnd))
start=perf_counter()
rows_seen=[]
latencies=[]
states=[]
try:
    if was_minimized:
        print("SMAART_TEMPORARY_RESTORE_FOR_READ_ONLY_QA",flush=True)
        win32gui.ShowWindow(hwnd,9)  # SW_RESTORE
        sleep(.4)
    target=locate_smaart()
    assert target and target.hwnd==hwnd, "Smaart not available after restore"
    directory=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
    scanner=LiveDataBarV7(directory)
    gate=StableTickGate(required=3,capacity=150)
    previous=None
    for i in range(100):
        t0=perf_counter()
        snapshot=scanner.poll(hwnd)
        latencies.append((perf_counter()-t0)*1000)
        names=snapshot.active_names
        if names is None:
            names=()
        d=gate.evaluate(snapshot,names,snapshot.ambiguous)
        rows_seen.append((snapshot.verified,snapshot.rows))
        states.append(d.state)
        if i==0:
            print("INITIAL_REAL_TICKS",snapshot.status,
                  "ON",list(Path(x).stem for x in names),flush=True)
            assert snapshot.rows>=100 and snapshot.verified==snapshot.rows
        if i%20==0:
            print("REAL_POLL",i,"COUNT",len(names),"STATE",d.state,
                  "STABLE",d.stable,"VERIFIED",snapshot.verified,"/",snapshot.rows,
                  "LATENCY_MS",round(latencies[-1],1),flush=True)
        if snapshot.rows<100 or snapshot.verified!=snapshot.rows:
            print("TRANSIENT_NATIVE_FRAME",i,snapshot.status,
                  "GATE",d.state,flush=True)
            assert d.state=="transient"
        if d.state=="valid":
            assert len(names)==2 and d.pair==tuple(names)
        if d.state=="invalid":
            assert len(names)!=2 and d.pair is None
        if d.state=="transient":
            assert d.pair is None
        # No silent file-name mismatches or invalid row indexes accepted.
        sleep(.07)
    verified_ok=sum(state in ("pending","valid","invalid") for state in states)
    print("NATIVE_VERIFIED_RATE",verified_ok,"/",len(rows_seen),flush=True)
    assert verified_ok>=95, f"Unreliable new viewport reads: {verified_ok}/100"
    report={
        "verified_ok":verified_ok,
        "polls":len(rows_seen),
        "verified_counts":Counter(f"{a}/{b}" for a,b in rows_seen),
        "states":Counter(states),
        "latency_ms_p95":sorted(latencies)[94],
        "latency_ms_max":max(latencies),
        "wall_seconds":perf_counter()-start,
        "active_names":list(names),
        "last_gate":gate.history[-1],
        "source_note":"Only visible rows are re-read between full scans; other rows use cached initial 108-row proof.",
    }
    # JSON serialize counters as dict (stdlib Counter already a dict).
    (root/"V824_REAL_100_POLL_QA.json").write_text(
         json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
    print("V824_REAL_100_POLL_PASS",json.dumps(
         {"states":dict(report["states"]),
          "verified":dict(report["verified_counts"]),
          "p95_ms":round(report["latency_ms_p95"],2),
          "max_ms":round(report["latency_ms_max"],2)},
         ensure_ascii=False),flush=True)
finally:
    if was_minimized and win32gui.IsWindow(hwnd):
        win32gui.ShowWindow(hwnd,6) # SW_MINIMIZE
        print("SMAART_MINIMIZED_STATE_RESTORED",flush=True)
