from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_8_PASSIVE_Y_QA')
p=base/'passive_phase_y_v78.py'
s=p.read_text(encoding='utf-8')
s+='''
class NativeAxisFollower:
    """Runs on one dedicated worker: stores baseline per plot/Trace identity."""
    def __init__(self):
        self.key=None
        self.previous=None
        self.captures=0

    def sample(self,key,hwnd,phase_rect):
        current=capture_native_phase(hwnd,phase_rect)
        self.captures+=1
        if key!=self.key or self.previous is None:
            self.key=key
            self.previous=current
            return None
        result=infer_native_pan(self.previous,current)
        # Always advance to newest observed native Smaart state, but only
        # propagate strong, agreed translational movement to Qt.
        self.previous=current
        return result
'''
p.write_text(s,encoding='utf-8')

p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('from phase_axis_follow_v77 import (capture_native_phase,\n    detect_vertical_shift,shifted_y_range)',
'''from phase_axis_follow_v77 import (capture_native_phase,
    detect_vertical_shift,shifted_y_range)
from passive_phase_y_v78 import NativeAxisFollower''')
s=s.replace('RemiX Auto Align V7.7 - Windows QA','RemiX Auto Align V7.8 - Windows QA').replace('RemiX  AUTO ALIGN  V7.7','RemiX  AUTO ALIGN  V7.8')
s=s.replace('    layout_ready=pyqtSignal(object)', '    layout_ready=pyqtSignal(object)\n    axis_snapshot=pyqtSignal(object)')
needle='''        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
        # Dedicated worker avoids stalling Qt/AutoAlign while native
        # PrintWindow + multi-region correlation is running.
        self.axis_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.axis_follower=NativeAxisFollower()
        self.axis_future=None
        self.axis_requested=0.0''')
needle='''        self.events.layout_ready.connect(self.on_plot_layout)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.events.layout_ready.connect(self.on_plot_layout)
        self.events.axis_snapshot.connect(self.on_passive_axis_snapshot)''')
needle='''        self.phase_axis_note=QLabel(
            "Phase Y: kéo trục Y của Smaart → SUM theo trục (không chạy lại TF)")'''
if needle not in s:
    import re
    m=re.search(r'        self\.phase_axis_note=QLabel\(\n.*?\)\n',s)
    assert m,m
    s=s[:m.start()]+'''        self.phase_axis_note=QLabel(
            "Phase Y: tự theo dõi TRACE gốc (không phụ thuộc kéo chuột)")
'''+s[m.end():]
else:
    s=s.replace(needle,'''        self.phase_axis_note=QLabel(
            "Phase Y: tự theo dõi TRACE gốc (không phụ thuộc kéo chuột)")''')
needle='''    def _check_phase_axis_drag(self,target):'''
assert s.count(needle)==1
# Passive callback and schedule triggered irrespective of cursor gesture.
methods='''    def on_passive_axis_snapshot(self,payload):
        key,result=payload
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,tuple(self.current_pair or ()))
        if key!=expected or result is None:
            return
        if not result.valid:
            if result.explanation != "No significant viewport movement":
                self.phase_axis_note.setText(
                    "Phase Y chưa đồng bộ: "+result.explanation[:80])
            return
        if abs(result.shift_px)<2:
            return
        initial={"lo":self.graph_phase.y_min,"hi":self.graph_phase.y_max}
        self._apply_phase_pan(result.shift_px,initial,verified=True,
                              confidence=result.confidence)
        print("V78_PASSIVE_PHASE_Y_SYNC",
              result.shift_px,result.confidence,
              self.graph_phase.y_min,self.graph_phase.y_max,flush=True)

    def _schedule_passive_axis_poll(self,target):
        if not self.current_sum or not self.plot_layout:
            return
        now=time.monotonic()
        if now-self.axis_requested<.32:
            return
        if self.axis_future is not None and not self.axis_future.done():
            return
        key=(target.hwnd,self.plot_layout.phase,tuple(self.current_pair or ()))
        self.axis_requested=now
        self.axis_future=self.axis_pool.submit(
            self.axis_follower.sample,key,target.hwnd,self.plot_layout.phase)
        def completed(task,k=key):
            try:
                self.events.axis_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V78_NATIVE_PHASE_Y_READ_ERROR",str(exc)[:130],flush=True)
        self.axis_future.add_done_callback(completed)

'''
s=s.replace(needle,methods+needle)
needle='''        self._check_phase_axis_drag(target)
        l,t,r,b=target.rect'''
assert s.count(needle)==1
s=s.replace(needle,'''        # Passive native-plot watcher: works for wheel, gestures, and
        # mouse interactions irrespective of how the Y-axis was changed.
        self._schedule_passive_axis_poll(target)
        l,t,r,b=target.rect''')
needle='''        self.pool.shutdown(wait=False,cancel_futures=True)
        if self.host:self.host.close()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pool.shutdown(wait=False,cancel_futures=True)
        self.axis_pool.shutdown(wait=False,cancel_futures=True)
        if self.host:self.host.close()''')
p.write_text(s,encoding='utf-8')
print("V78_PASSIVE_WATCHER_PATCH_PASS")
