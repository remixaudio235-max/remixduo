from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
import threading
import time
import smaart_live_tf_reader_v873 as native
from test_v880_reader_stability import binding, packet


def test_validation_releases_lock_and_rebind_invalidates_inflight_frame(monkeypatch):
    reader=native.NativeTFReader()
    reader.bind(binding())
    entered, release=threading.Event(),threading.Event()
    original=native.validate_frame
    def slow_validate(p,b):
        entered.set()
        assert release.wait(2)
        original(p,b)
    monkeypatch.setattr(native,'validate_frame',slow_validate)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(reader.ingest,packet())
        try:
            assert entered.wait(2)
            acquired=reader._lock.acquire(timeout=.1)
            assert acquired, 'Large TF validation still holds reader lock'
            reader._lock.release()
            reader.unbind(8,'test-engine','test-trace')
            reader.bind(binding())
        finally:
            release.set()
        assert future.result(timeout=2) is False
    assert reader.latest(8,'test-engine','test-trace') is None
    assert reader.last_rejection=='BINDING_CHANGED_DURING_VALIDATION'


def test_page_reports_visible_ambiguous_icon_instead_of_reusing_cache(monkeypatch):
    import full_scan_v7 as scanner
    monkeypatch.setattr(scanner,'scan_icon_white_cross',lambda *_:'unknown')
    row=SimpleNamespace(rectangle=lambda:SimpleNamespace(top=20,left=10))
    result=scanner._page(None,['trace'],0,20,0,100,0,uia_rows={0:row})
    assert result=={0:'unknown'}


def test_single_token_rejected_immediately_when_checked_row_changes(tmp_path):
    from live_sync_v7 import LiveDataBarV7
    first=tmp_path/'first.trf';first.touch()
    second=tmp_path/'second.trf';second.touch()
    observer=LiveDataBarV7(tmp_path)
    observer.ready=True;observer.order=[first,second]
    observer.states={0:'on',1:'off'}
    for _ in range(3): observer.observe_single(time.perf_counter())
    assert observer.current_single() is not None
    observer.states={0:'off',1:'on'}
    assert observer.current_single() is None
    observer.states={0:'unknown',1:'off'}
    assert observer.current_single() is None
