import json,time
from pathlib import Path
from types import SimpleNamespace as NS


def test_async_fs_cache_never_parses_on_caller_thread(tmp_path,monkeypatch):
    import smaart_fs_sync_v841 as fs
    p=tmp_path/"SmaartConfig.xml";p.write_text("x")
    calls=[]
    monkeypatch.setattr(fs,"read_saved_smaart_fs",
                        lambda path: calls.append(path) or "SNAP")
    cache=fs.AsyncSavedFsCache()
    try:
        assert cache.get(p) is None
        deadline=time.monotonic()+2
        while cache.get(p) is None and time.monotonic()<deadline:time.sleep(.01)
        assert cache.get(p)=="SNAP" and calls==[p]
    finally:cache.close()


def test_clean_marker_distinguishes_close_from_crash(tmp_path):
    import duo_lifecycle_v8142 as life
    p=tmp_path/"lifecycle.json"
    life.mark_started(p,123)
    assert life.previous_exit_unclean(p)
    life.mark_clean(p,123)
    assert not life.previous_exit_unclean(p)


def test_watcher_restarts_once_after_unclean_exit_only():
    import smaart_autostart_v875 as auto
    calls=[];unclean={"v":True};running={"v":False}
    w=auto.EpisodeWatcher(running=lambda:((9,1,1.),),
        is_duo_running=lambda:running["v"],launch=lambda:calls.append(1) or True,
        crashed=lambda:unclean["v"])
    assert w.poll()
    running["v"]=True;assert not w.poll()
    running["v"]=False;assert w.poll();assert not w.poll()
    assert calls==[1,1]


def test_trace_status_reports_count_and_stability():
    from signal_tools_gui_v813 import trace_recognition_text
    o=NS(single_stable=2,single_candidate=("c:/A.trf",1,2),states={0:"on"})
    assert "2/3" in trace_recognition_text(o,None,1)
    assert "2 Trace" in trace_recognition_text(o,None,2)


def test_anchor_debounce_requires_two_matching_samples():
    from signal_tools_gui_v813 import stable_anchor_sample
    old=NS(host_at_scan=(0,0,100,100));new=NS(host_at_scan=(0,0,200,200))
    accepted,pending=stable_anchor_sample(old,None,new)
    assert accepted is old and pending is new
    accepted,pending=stable_anchor_sample(old,pending,new)
    assert accepted is new and pending is None


def test_bounded_shutdown_returns_before_deadline():
    from concurrent.futures import ThreadPoolExecutor
    from worker_lifecycle_v8142 import bounded_shutdown
    pool=ThreadPoolExecutor(max_workers=1);pool.submit(time.sleep,.5)
    started=time.monotonic();bounded_shutdown(pool,.05)
    assert time.monotonic()-started<.20
