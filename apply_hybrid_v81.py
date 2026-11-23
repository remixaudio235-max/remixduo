from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_1_HYBRID_PHASE_Y_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
assert 'NativeFastPan' not in s
s=s.replace('from fast_phase_y_v80 import capture_fit_fast,FastFitResult',
            'from fast_phase_y_v80 import capture_fit_fast,FastFitResult\nfrom native_fast_pan_v81 import NativeFastPan,PanFrame')
s=s.replace('RemiX Auto Align V8.0 - Windows QA','RemiX Auto Align V8.1 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V8.0','RemiX  AUTO ALIGN  V8.1')
s=s.replace('    axis_snapshot=pyqtSignal(object)',
            '    axis_snapshot=pyqtSignal(object)\n    pan_snapshot=pyqtSignal(object)')
needle='''        self.axis_requested=0.0
        self.axis_last_spin=0.0'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.axis_requested=0.0
        self.pan_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.pan_tracker=NativeFastPan()
        self.pan_future=None
        self.pan_requested=0.0
        self.pan_last_move=0.0
        self.pan_accepted=0
        self.pan_rejected=0
        self.axis_last_spin=0.0''')
needle='''        self.events.axis_snapshot.connect(self.on_absolute_phase_axis)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.events.axis_snapshot.connect(self.on_absolute_phase_axis)
        self.events.pan_snapshot.connect(self.on_native_fast_pan)''')
needle='''    def on_absolute_phase_axis(self,payload):
        """Immediate latest absolute fit drives SUM. UI labels are throttled."""
        key,result=payload'''
assert s.count(needle)==1
s=s.replace(needle,'''    def on_absolute_phase_axis(self,payload):
        """Idle-only absolute Y anchor; never fight live gesture tracking."""
        key,result=payload
        if time.monotonic()-self.pan_last_move < .28:
            return''')
needle='''        if now-self.axis_requested<.033:return'''
assert s.count(needle)==1
s=s.replace(needle,'''        if now-self.axis_requested<.85:return
        if now-self.pan_last_move<.28:return''')
needle='''    def _check_phase_axis_drag(self,target):'''
assert s.count(needle)==1
new='''    def on_native_fast_pan(self,payload):
        """Render signed actual pixel displacement on the next Qt update."""
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        now=time.monotonic()
        if now-frame.frame_time>.16:return
        if not frame.valid:
            self.pan_rejected+=1
            return
        dy=float(frame.delta_px)
        if abs(dy)<.75:return
        x,y,w,h=self.plot_layout.phase
        # Pure viewport adjustment; don't mutate source H, optimizer or SUM.
        offset=dy*(self.graph_phase.y_max-self.graph_phase.y_min)/h
        self.graph_phase.y_min+=offset
        self.graph_phase.y_max+=offset
        self.graph_phase.update()
        self.pan_last_move=now
        self.pan_accepted+=1
        if now-self.axis_last_spin>.12:
            self.axis_last_spin=now
            self.phase_min.blockSignals(True)
            self.phase_max.blockSignals(True)
            try:
                self.phase_min.setValue(self.graph_phase.y_min)
                self.phase_max.setValue(self.graph_phase.y_max)
            finally:
                self.phase_min.blockSignals(False)
                self.phase_max.blockSignals(False)
        if now-self.axis_last_status>.22:
            self.axis_last_status=now
            self.phase_axis_note.setText(
                f"Phase FAST tracking: {dy:+.0f}px | "
                f"{frame.confidence:.0%} | {frame.capture_ms:.0f}ms")
        print("V81_PAN_FAST",dy,round(frame.confidence,3),
              round(frame.capture_ms,1),
              round(self.graph_phase.y_max,1),flush=True)

    def _schedule_fast_pan(self,target):
        if not self.current_sum or not self.plot_layout:
            return
        now=time.monotonic()
        if now-self.pan_requested < .025:return
        if self.pan_future is not None and not self.pan_future.done():return
        key=(target.hwnd,self.plot_layout.phase,
             tuple(self.current_pair or ()),self._reference_index())
        self.pan_requested=now
        self.pan_future=self.pan_pool.submit(
            self.pan_tracker.poll,key,self.plot_layout.phase)
        def done(task,k=key):
            try:
                self.events.pan_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V81_PAN_WORKER_ERROR",str(exc)[:130],flush=True)
        self.pan_future.add_done_callback(done)

'''
s=s.replace(needle,new+needle)
needle='''        self._schedule_absolute_axis_calibration(target)
        l,t,r,b=target.rect'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._schedule_fast_pan(target)
        self._schedule_absolute_axis_calibration(target)
        l,t,r,b=target.rect''')
needle='''        self.axis_pool.shutdown(wait=False,cancel_futures=True)
        if self.host:self.host.close()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.axis_pool.shutdown(wait=False,cancel_futures=True)
        self.pan_pool.shutdown(wait=False,cancel_futures=True)
        if self.host:self.host.close()''')
p.write_text(s,encoding="utf-8")
print("V81_HYBRID_PAN_RENDER_INTEGRATED")
