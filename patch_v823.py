"""V8.23: selection continuity, focus-safe Smaart poll, single GUI owner."""
from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_23_TRACE_SYNC_GUARD_QA")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
needle="from live_sync_v7 import LiveDataBarV7"
assert s.count(needle)==1
s=s.replace(needle,"from live_sync_v7 import LiveDataBarV7, SyncResult")
needle="    found=pyqtSignal(object,str)"
assert s.count(needle)==1
s=s.replace(needle,"    found=pyqtSignal(object)")
needle='''        self.controller=SelectionController(self.on_selection)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.controller=SelectionController(self.on_selection)
        # Unknown or transient PrintWindow captures must NOT erase the
        # selected pair. Hide model overlays until a complete verified
        # tick snapshot has been received.
        self._selection_verified=bool(self.demo)
        self._selection_last_status="Awaiting verified Data Bar ticks"''')
needle='''        phase_active=(workspace and mode=="phase" and
                      (not self.managed_mode or self.ui_tool_enabled))'''
assert s.count(needle)==1
s=s.replace(needle,'''        phase_active=(workspace and mode=="phase" and
                      getattr(self,"_selection_verified",True) and
                      (not self.managed_mode or self.ui_tool_enabled))''')
needle='''        eq_active=(workspace and self.managed_mode and mode=="eq"
                   and not self.ui_tool_enabled and
                   self.graph_mag.mageq_source is not None and'''
assert s.count(needle)==1
s=s.replace(needle,'''        eq_active=(workspace and self.managed_mode and mode=="eq"
                   and getattr(self,"_selection_verified",True)
                   and not self.ui_tool_enabled and
                   self.graph_mag.mageq_source is not None and''')
start=s.index("    def found(self,pair,status):")
end=s.index("    def _clear_phase_match",start)
new='''    def found(self,result):
        """Only fully verified snapshots may replace/invalidate a pair.

        Transient READ ERROR, changing viewport or failed full scans
        hide overlays but retain the last confirmed pair so the app
        can restore the correct traces without unnecessary reload.
        A complete and verified scan with not-exactly-two ticks
        DOES invalidate the old pair immediately.
        """
        if not isinstance(result,SyncResult):
            self._selection_verified=False
            self._selection_last_status="Invalid scanner result"
            self.status.setText(self._selection_last_status)
            self.refresh_visibility()
            return
        status=str(result.status)
        confirmed=(result.rows>=2 and result.verified==result.rows
                   and status.startswith(("Verified ","FULL SCAN ")))
        self._selection_last_status=status
        self._selection_verified=bool(confirmed)
        if not confirmed:
            self.status.setText("Đang xác minh Trace: "+status[:100])
            self.refresh_visibility()
            return
        if result.pair is None:
            if self.controller.last_pair:
                self.controller.invalidate(
                    "Đã xác minh toàn bộ Data Bar: không có đúng 2 Trace bật")
            self.status.setText(status)
        else:
            self.controller.apply(result.pair,"Win UIA tick verified")
            if self.current_traces:self.status.setText(status)
        self.refresh_visibility()

    def should_poll_selection(self,target):
        # The companion popup may have focus while Smaart still hosts
        # the native Data Bar. A second application cannot poll.
        return bool(target and self._target_is_foreground(target.hwnd))

    def _handle_scan_future(self,task):
        try:
            result=task.result()
        except Exception as exc:
            result=SyncResult(None,"READ ERROR: "+str(exc)[:120],
                              0,max(0,len(self.observer.order)),
                              True,time.perf_counter())
        self.events.found.emit(result)

'''
s=s[:start]+new+s[end:]
needle='''        if target.foreground and now-self.last_poll>.16 and (self.poll_future is None or self.poll_future.done()):
            self.last_poll=now
            self.poll_future=self.pool.submit(self.observer.poll,target.hwnd)
            self.poll_future.add_done_callback(
                lambda task:self.events.found.emit(task.result().pair,task.result().status)
                if not task.exception() else self.events.found.emit(None,
                     "Smaart Data Bar scan error: "+str(task.exception())[:100]))'''
assert s.count(needle)==1
s=s.replace(needle,'''        if (self.should_poll_selection(target) and
            now-self.last_poll>.16 and
            (self.poll_future is None or self.poll_future.done())):
            self.last_poll=now
            self.poll_future=self.pool.submit(self.observer.poll,target.hwnd)
            self.poll_future.add_done_callback(self._handle_scan_future)''')
needle='''if __name__=="__main__":
    parser=argparse.ArgumentParser()'''
assert s.count(needle)==1
s=s.replace(needle,'''if __name__=="__main__":
    from single_instance_v823 import acquire_instance
    _single_instance=acquire_instance()
    if _single_instance is None:
        print("V823_ALREADY_RUNNING: only one RemiX Signal may read Smaart Data Bar",flush=True)
        raise SystemExit(21)
    parser=argparse.ArgumentParser()''')
s=s.replace("V8.22","V8.23")
p.write_text(s,encoding="utf-8")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8").replace("V8.22","V8.23")
p.write_text(s,encoding="utf-8")
print("V823_SYNC_GUARD_AND_FOCUS_PATCHED")
