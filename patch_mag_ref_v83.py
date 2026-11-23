from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_3_MAG_REF_ANCHOR_QA')
p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('from native_dual_y_v82 import NativeDualFastPan,DualPanResult',
            'from native_dual_y_v82 import NativeDualFastPan,DualPanResult\nfrom mag_ref_anchor_v83 import capture_mag_ref,MagAnchor')
s=s.replace('RemiX Auto Align V8.2 - Windows QA','RemiX Auto Align V8.3 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V8.2','RemiX  AUTO ALIGN  V8.3')
needle='''    pan_snapshot=pyqtSignal(object)'''
assert s.count(needle)==1
s=s.replace(needle,'''    pan_snapshot=pyqtSignal(object)
    mag_anchor_ready=pyqtSignal(object)''')
needle='''        self.axis_previous_fit=0.0'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.axis_previous_fit=0.0
        self.mag_anchor_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.mag_anchor_future=None
        self.mag_anchor_requested=0.0
        self.mag_anchor_accepted=0
        self.mag_anchor_failed=0''')
needle='''        self.events.pan_snapshot.connect(self.on_native_dual_pan)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.events.pan_snapshot.connect(self.on_native_dual_pan)
        self.events.mag_anchor_ready.connect(self.on_mag_ref_anchor)''')
needle='''        self._mag_offset_key=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._mag_offset_key=None
        self._mag_anchor_verified=False''')
# Remove previous wrong sum-median centering, but use reference magnitude median
# as temporary only until native source curve correlation provides ground truth.
start=s.index('        mag_fit_key=(tuple(self.current_pair or self.current_sum.sources),')
end=s.index('        if self.graph_mag.display_offset_db:',start)
new='''        mag_fit_key=(tuple(self.current_pair or self.current_sum.sources),
                     bool(self.mag_fit.isChecked()))
        if mag_fit_key!=self._mag_offset_key:
            self._mag_offset_key=mag_fit_key
            self._mag_anchor_verified=False
            self.graph_mag.display_offset_db=0.0
            if self.mag_fit.isChecked():
                ref,other=self._ordered_traces()
                # Provisional preview centering by REF rather than SUM.
                # This does not invent +6dB or change H. Native correlation
                # will replace the provisional offset as soon as verified.
                try:
                    from trf_core import matched
                    f,href,_,coh=matched(ref,other)
                    valid=(f>=60)&(f<=1800)&(coh>=.6)&(np.abs(href)>1e-12)
                    if np.count_nonzero(valid)>=20:
                        ref_db=20*np.log10(np.abs(href[valid]))
                        midpoint=(self.graph_mag.y_min+self.graph_mag.y_max)*.5
                        self.graph_mag.display_offset_db=float(
                            midpoint-np.median(ref_db))
                except (ValueError,FloatingPointError):
                    pass
'''
s=s[:start]+new+s[end:]
# Ensure a selected new pair resets cached key before recalc, if pair reselected.
needle='''        self.current_pair=None;self.current_sum=None;self.current_traces=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.current_pair=None;self.current_sum=None;self.current_traces=None
        self._mag_offset_key=None
        self._mag_anchor_verified=False''')
needle='''    def on_native_dual_pan(self,payload):'''
assert s.count(needle)==1
handlers='''    def on_mag_ref_anchor(self,payload):
        """A validated native cyan REF fit anchors SUM's MAG display only."""
        key,fit=payload
        if not self.current_sum or not self.current_traces or not self.plot_layout:
            return
        if not self.mag_fit.isChecked() or not isinstance(fit,MagAnchor):
            return
        now=time.monotonic()
        if now-self.mag_pan_last_move<.42:
            return
        lo,hi=self.graph_mag.y_min,self.graph_mag.y_max
        expected=(self.plot_hwnd,self.plot_layout.mag,
                  tuple(self.current_pair or ()),self._reference_index(),
                  float(self.mag_smooth.currentData() or 0),
                  round(lo,2),round(hi,2))
        if key!=expected:return
        if not fit.accepted:
            self.mag_anchor_failed+=1
            if self.mag_anchor_failed<=2:
                print("V83_MAG_REF_ANCHOR_REJECT",fit.reason[:120],flush=True)
            return
        self.mag_anchor_accepted+=1
        self._mag_anchor_verified=True
        old=self.graph_mag.display_offset_db
        new=float(fit.offset_db)
        if abs(new-old)>.06:
            self.graph_mag.display_offset_db=new
            self.graph_mag.update()
        # Independent native Y axis pan continues to work as before.
        if self.mag_anchor_accepted==1 or abs(new-old)>.5:
            self.axis_note.setText(
                f"MAG REF native {fit.score:.0%} | offset {new:+.2f}dB "
                "(DISPLAY ONLY, no DSP gain)")
            print("V83_MAG_REF_ANCHORED",
                  round(old,2),round(new,2),round(fit.score,3),
                  fit.bins,flush=True)

    def _schedule_mag_ref_anchor(self,target):
        if not self.current_sum or not self.current_traces or not self.plot_layout:
            return
        if not self.mag_fit.isChecked():return
        now=time.monotonic()
        if now-self.mag_anchor_requested<1.15:return
        if now-self.mag_pan_last_move<.42:return
        if self.mag_anchor_future is not None and not self.mag_anchor_future.done():
            return
        ref,other=self._ordered_traces()
        lo,hi=self.graph_mag.y_min,self.graph_mag.y_max
        smoothing=float(self.mag_smooth.currentData() or 0.)
        smoothing=(1.0/smoothing if smoothing>=1 else smoothing)
        key=(target.hwnd,self.plot_layout.mag,
             tuple(self.current_pair or ()),self._reference_index(),
             float(self.mag_smooth.currentData() or 0),
             round(lo,2),round(hi,2))
        self.mag_anchor_requested=now
        self.mag_anchor_future=self.mag_anchor_pool.submit(
            capture_mag_ref,target.hwnd,self.plot_layout.mag,ref,other,
            lo,hi,smoothing)
        def on_finished(task,k=key):
            try:
                self.events.mag_anchor_ready.emit((k,task.result()))
            except Exception as exc:
                print("V83_MAG_ANCHOR_READ_ERROR",str(exc)[:140],flush=True)
        self.mag_anchor_future.add_done_callback(on_finished)

'''
s=s.replace(needle,handlers+needle)
needle='''        self._schedule_fast_pan(target)
        self._schedule_absolute_axis_calibration(target)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._schedule_fast_pan(target)
        self._schedule_absolute_axis_calibration(target)
        self._schedule_mag_ref_anchor(target)''')
needle='''        self.pan_pool.shutdown(wait=False,cancel_futures=True)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pan_pool.shutdown(wait=False,cancel_futures=True)
        self.mag_anchor_pool.shutdown(wait=False,cancel_futures=True)''')
p.write_text(s,encoding='utf-8')
print('V83_NATIVE_MAG_REF_ANCHOR_INTEGRATED')
