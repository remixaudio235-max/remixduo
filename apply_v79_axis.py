from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
needle='from passive_phase_y_v78 import NativeAxisFollower'
assert s.count(needle)==1
s=s.replace(needle,needle+'\nfrom phase_axis_absolute_v79 import capture_fit,AxisFit')
s=s.replace('RemiX Auto Align V7.8 - Windows QA','RemiX Auto Align V7.9 - Windows QA').replace('RemiX  AUTO ALIGN  V7.8','RemiX  AUTO ALIGN  V7.9')
s=s.replace('self.events.axis_snapshot.connect(self.on_passive_axis_snapshot)',
            'self.events.axis_snapshot.connect(self.on_absolute_phase_axis)')
a=s.index('    def on_passive_axis_snapshot(self,payload):')
b=s.index('    def _check_phase_axis_drag(self,target):',a)
new='''    def on_absolute_phase_axis(self,payload):
        """Authoritative *absolute* display Y fit; never add delta pans."""
        key,fit=payload
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected or fit is None:
            return
        if not fit.accepted:
            self.phase_axis_note.setText("Phase Y AUTO: chưa khớp REF • "+
                                         fit.reason[:60])
            return
        previous=self.graph_phase.y_max
        if abs(float(fit.top_deg)-previous)<2.0:
            return
        lo,hi=fit.bottom_deg,fit.top_deg
        self.phase_min.blockSignals(True)
        self.phase_max.blockSignals(True)
        try:
            self.phase_min.setValue(lo)
            self.phase_max.setValue(hi)
        finally:
            self.phase_min.blockSignals(False)
            self.phase_max.blockSignals(False)
        # Always use the EXACT fit, never quantized widget value.
        self.graph_phase.y_min=lo
        self.graph_phase.y_max=hi
        self.graph_phase.update()
        self.phase_axis_note.setText(
            f"Phase Y AUTO REF{self._reference_index()+1}: "
            f"{lo:.0f}°..{hi:.0f}° | khớp {fit.hit_fraction:.0%}")
        print("V79_ABSOLUTE_PHASE_Y_CAL",
              key[3],lo,hi,fit.hit_fraction,fit.alternate_fraction,
              flush=True)

    def _schedule_absolute_axis_calibration(self,target):
        if not self.current_sum or not self.plot_layout or not self.current_traces:
            return
        now=time.monotonic()
        if now-self.axis_requested<.48:
            return
        if self.axis_future is not None and not self.axis_future.done():
            return
        ref,other=self._ordered_traces()
        key=(target.hwnd,self.plot_layout.phase,
             tuple(self.current_pair or ()),self._reference_index())
        current_top=float(self.graph_phase.y_max)
        self.axis_requested=now
        self.axis_future=self.axis_pool.submit(
            capture_fit,target.hwnd,self.plot_layout.phase,
            ref,other,current_top)
        def callback(task,k=key):
            try:
                self.events.axis_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V79_PHASE_AXIS_CAPTURE_ERROR",str(exc)[:130],flush=True)
        self.axis_future.add_done_callback(callback)

'''
s=s[:a]+new+s[b:]
needle='self._schedule_passive_axis_poll(target)'
assert s.count(needle)==1
s=s.replace(needle,'self._schedule_absolute_axis_calibration(target)')
needle='''        self.phase_axis_note=QLabel('''
assert s.count(needle)==1
start=s.index(needle)
end=s.index('\n        self.phase_axis_note.setStyleSheet',start)
s=s[:start]+'''        self.phase_axis_note=QLabel(
            "Phase Y AUTO: khớp trực tiếp REF với nét Phase Smaart")'''+s[end:]
# Ensure source data scene change cannot carry over a previous ref calibrated range
# until a newly validated native REF fit arrives.
p.write_text(s,encoding='utf-8')
print("V79_ABSOLUTE_PHASE_VIEWPORT_PATCH_PASS")
