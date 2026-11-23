from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_0_FAST_PHASE_Y_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert 'capture_fit_fast' not in s
s=s.replace('from phase_axis_absolute_v79 import capture_fit,AxisFit',
            'from phase_axis_absolute_v79 import capture_fit,AxisFit\nfrom fast_phase_y_v80 import capture_fit_fast,FastFitResult')
s=s.replace('RemiX Auto Align V7.9 - Windows QA','RemiX Auto Align V8.0 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.9','RemiX  AUTO ALIGN  V8.0')
s=s.replace('        self.axis_requested=0.0',
'''        self.axis_requested=0.0
        self.axis_last_spin=0.0
        self.axis_last_status=0.0
        self.axis_accepted=0
        self.axis_rejected=0
        self.axis_render_ms=[]
        self.axis_task_ms=[]
        self.axis_previous_fit=0.0
''')
start=s.index('    def on_absolute_phase_axis(self,payload):')
end=s.index('    def _check_phase_axis_drag(self,target):',start)
replacement='''    def on_absolute_phase_axis(self,payload):
        """Immediate latest absolute fit drives SUM. UI labels are throttled."""
        key,result=payload
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected or result is None:return
        fit=result.fit if isinstance(result,FastFitResult) else result
        now=time.monotonic()
        if isinstance(result,FastFitResult):
            self.axis_task_ms.append(result.elapsed_ms)
            if len(self.axis_task_ms)>120:self.axis_task_ms.pop(0)
            # Never render a stale frame when Windows/PrintWindow stalls.
            if now-result.frame_time>0.18:
                return
        if not fit.accepted:
            self.axis_rejected+=1
            if now-self.axis_last_status>.8:
                self.axis_last_status=now
                self.phase_axis_note.setText(
                    "Phase Y fast: khong xac nhan ("+fit.reason[:55]+")")
            return
        self.axis_accepted+=1
        previous=float(self.graph_phase.y_max)
        if abs(float(fit.top_deg)-previous)<.7:
            return
        lo,hi=fit.bottom_deg,fit.top_deg
        # Fast paint only; changing 2 spinbox widgets every frame is costly.
        self.graph_phase.y_min=lo
        self.graph_phase.y_max=hi
        self.graph_phase.update()
        if now-self.axis_last_spin>.12:
            self.axis_last_spin=now
            self.phase_min.blockSignals(True)
            self.phase_max.blockSignals(True)
            try:
                self.phase_min.setValue(lo)
                self.phase_max.setValue(hi)
            finally:
                self.phase_min.blockSignals(False)
                self.phase_max.blockSignals(False)
        if now-self.axis_last_status>.22:
            self.axis_last_status=now
            mode=result.mode if isinstance(result,FastFitResult) else "native"
            ms=result.elapsed_ms if isinstance(result,FastFitResult) else 0
            self.phase_axis_note.setText(
                f"Phase Y FAST REF{self._reference_index()+1}: "
                f"{lo:.0f}..{hi:.0f} deg | {fit.hit_fraction:.0%} | "
                f"{mode} {ms:.0f}ms")
        print("V80_FAST_PHASE_Y_CAL",
              key[3],lo,hi,round(fit.hit_fraction,3),
              result.mode if isinstance(result,FastFitResult) else "test",
              round(result.elapsed_ms,1) if isinstance(result,FastFitResult) else 0,
              flush=True)

    def _schedule_absolute_axis_calibration(self,target):
        if not self.current_sum or not self.plot_layout or not self.current_traces:
            return
        now=time.monotonic()
        # Qt tick is 33ms. One worker, no backlog: newest native image wins.
        if now-self.axis_requested<.033:return
        if self.axis_future is not None and not self.axis_future.done():
            return
        ref,other=self._ordered_traces()
        key=(target.hwnd,self.plot_layout.phase,
             tuple(self.current_pair or ()),self._reference_index())
        current_top=float(self.graph_phase.y_max)
        self.axis_requested=now
        self.axis_future=self.axis_pool.submit(
            capture_fit_fast,target.hwnd,self.plot_layout.phase,
            ref,other,current_top)
        def callback(task,k=key):
            try:
                self.events.axis_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V80_FAST_AXIS_CAPTURE_ERROR",str(exc)[:130],flush=True)
        self.axis_future.add_done_callback(callback)

'''
s=s[:start]+replacement+s[end:]
needle='''        self.phase_axis_note=QLabel(
            "Phase Y AUTO: khớp trực tiếp REF với nét Phase Smaart")'''
# handle actual encoded text if source maybe encoding corrupted:
if needle not in s:
    a=s.index('        self.phase_axis_note=QLabel(')
    b=s.index('\n        self.phase_axis_note.setStyleSheet',a)
    s=s[:a]+'''        self.phase_axis_note=QLabel(
            "Phase Y FAST: native REF, redraw latest-wins")'''+s[b:]
else:
    s=s.replace(needle,'''        self.phase_axis_note=QLabel(
            "Phase Y FAST: native REF, redraw latest-wins")''')
p.write_text(s,encoding='utf-8')
print('V80_PATCH_SUCCESS')
