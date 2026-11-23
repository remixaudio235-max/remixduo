from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_2_DUAL_AXIS_FOLLOW_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
s=s.replace('from native_fast_pan_v81 import NativeFastPan,PanFrame',
'''from native_fast_pan_v81 import NativeFastPan,PanFrame
from native_dual_y_v82 import NativeDualFastPan,DualPanResult''')
assert 'NativeDualFastPan' in s
s=s.replace('RemiX Auto Align V8.1 - Windows QA',
            'RemiX Auto Align V8.2 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V8.1','RemiX  AUTO ALIGN  V8.2')
s=s.replace('self.setFixedSize(354,692)','self.setFixedSize(354,713)')
needle='''        self.mag_max=QDoubleSpinBox();self.mag_max.setRange(-150,150);self.mag_max.setValue(20)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.mag_max=QDoubleSpinBox();self.mag_max.setRange(-500,500);self.mag_max.setValue(20)''')
needle='''        self.mag_min=QDoubleSpinBox();self.mag_min.setRange(-150,150);self.mag_min.setValue(-80)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.mag_min=QDoubleSpinBox();self.mag_min.setRange(-500,500);self.mag_min.setValue(-80)''')
needle='''        self.phase_min.setDecimals(1)
        self.phase_max.setDecimals(1)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.phase_min.setDecimals(1)
        self.phase_max.setDecimals(1)
        self.mag_min.setDecimals(2)
        self.mag_max.setDecimals(2)''')
needle='''        self.pan_tracker=NativeFastPan()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pan_tracker=NativeDualFastPan()''')
needle='''        self.pan_rejected=0'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pan_rejected=0
        self.mag_pan_accepted=0
        self.mag_pan_rejected=0
        self.mag_pan_last_move=0.0
        self.mag_pan_last_status=0.0
        self.mag_pan_last_spin=0.0
        self.mag_pan_last_log=0.0''')
needle='''        self.events.pan_snapshot.connect(self.on_native_fast_pan)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.events.pan_snapshot.connect(self.on_native_dual_pan)''')
needle='''        layout.insertWidget(layout.indexOf(self.axis_note),self.phase_axis_note)'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.insertWidget(layout.indexOf(self.axis_note),self.phase_axis_note)
        self.mag_axis_note=QLabel(
            "Mag Y FAST: theo doi truc Y rieng, read-only")
        self.mag_axis_note.setStyleSheet("color:#b1e7a6;font:10px 'Segoe UI'")
        layout.insertWidget(layout.indexOf(self.axis_note),self.mag_axis_note)''')
needle='''    def on_native_fast_pan(self,payload):'''
assert s.count(needle)==1
methods='''    def on_native_dual_pan(self,payload):
        key,result=payload
        if not self.current_sum or not self.plot_layout or not isinstance(result,DualPanResult):
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  self.plot_layout.mag,tuple(self.current_pair or ()),
                  self._reference_index())
        if key!=expected:
            return
        phase_key=(key[0],key[1],key[3],key[4])
        mag_key=(key[0],key[2],key[3],key[4])
        self.on_native_fast_pan((phase_key,result.phase))
        self.on_native_mag_pan((mag_key,result.mag))

    def on_native_mag_pan(self,payload):
        """Move only the Magnitude viewport. Never change EQ, gain or TF."""
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.mag,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        now=time.monotonic()
        if now-frame.frame_time>.16:
            return
        if not frame.valid:
            self.mag_pan_rejected+=1
            if now-self.mag_pan_last_status>.75:
                self.mag_pan_last_status=now
                self.mag_axis_note.setText(
                    "Mag Y FAST: chua xac nhan - "+frame.reason[:45])
            return
        dy=float(frame.delta_px)
        if abs(dy)<.75:return
        height=float(self.plot_layout.mag[3])
        span=float(self.graph_mag.y_max-self.graph_mag.y_min)
        if not np.isfinite(span) or span<=0 or height<=0:
            return
        delta_db=dy*span/height
        self.graph_mag.y_min+=delta_db
        self.graph_mag.y_max+=delta_db
        self.graph_mag.update()
        self.mag_pan_last_move=now
        self.mag_pan_accepted+=1
        if now-self.mag_pan_last_spin>.12:
            self.mag_pan_last_spin=now
            self.mag_min.blockSignals(True)
            self.mag_max.blockSignals(True)
            try:
                self.mag_min.setValue(self.graph_mag.y_min)
                self.mag_max.setValue(self.graph_mag.y_max)
            finally:
                self.mag_min.blockSignals(False)
                self.mag_max.blockSignals(False)
        if now-self.mag_pan_last_status>.22:
            self.mag_pan_last_status=now
            self.mag_axis_note.setText(
                f"Mag Y FAST: {dy:+.0f}px / {delta_db:+.2f}dB | "
                f"{frame.confidence:.0%} | {frame.capture_ms:.0f}ms")
        if now-self.mag_pan_last_log>.3:
            self.mag_pan_last_log=now
            print("V82_MAG_Y_FAST",dy,round(delta_db,3),
                  round(frame.confidence,3),round(frame.capture_ms,1),
                  round(self.graph_mag.y_max,2),flush=True)

'''
s=s.replace(needle,methods+needle)
start=s.index('    def _schedule_fast_pan(self,target):')
end=s.index('    def _check_phase_axis_drag(self,target):',start)
schedule='''    def _schedule_fast_pan(self,target):
        if not self.current_sum or not self.plot_layout:
            return
        now=time.monotonic()
        # One worker, both charts; no independent GDI threads or backlog.
        if now-self.pan_requested < .025:return
        if self.pan_future is not None and not self.pan_future.done():return
        key=(target.hwnd,self.plot_layout.phase,self.plot_layout.mag,
             tuple(self.current_pair or ()),self._reference_index())
        self.pan_requested=now
        self.pan_future=self.pan_pool.submit(
            self.pan_tracker.poll,key,self.plot_layout.phase,
            self.plot_layout.mag)
        def done(task,k=key):
            try:
                self.events.pan_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V82_DUAL_PAN_WORKER_ERROR",str(exc)[:130],flush=True)
        self.pan_future.add_done_callback(done)

'''
s=s[:start]+schedule+s[end:]
p.write_text(s,encoding='utf-8')
print("V82_BOTH_Y_AXES_PATCHED")
