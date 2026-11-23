from pathlib import Path
path=Path(__file__).with_name('overlay_v7.py')
s=path.read_text(encoding='utf-8')
def once(a,b):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError('Expected exactly one match, got %d: %r'%(n,a[:90]))
 s=s.replace(a,b)
# Keep native-only updates while GUI is not actively dragging.
once('''            if now-result.frame_time>0.18:
                return''','''            if now-result.frame_time>0.55:
                return''')
once('''        if now-frame.frame_time>.18:return
        if not frame.valid:''','''        if self.axis_drag is not None:return
        if now-frame.frame_time>.55:return
        if not frame.valid:''') if False else None
# Shared pan callback: ignore native Phase pan during the manual gesture to avoid double applying pixels.
once('''    def on_native_fast_pan(self,payload):
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,''','''    def on_native_fast_pan(self,payload):
        key,frame=payload
        if self.axis_drag is not None:return
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,''')
# Guard absolute callback from out-of-date drag readings.
once('''    def on_absolute_phase_axis(self,payload):
        """Idle-only absolute Y anchor; never fight live gesture tracking."""
        key,result=payload
        if time.monotonic()-self.pan_last_move < .28:''','''    def on_absolute_phase_axis(self,payload):
        """Idle-only absolute Y anchor; never fight live gesture tracking."""
        key,result=payload
        if self.axis_drag is not None:return
        if time.monotonic()-self.pan_last_move < .28:''')
# Existing handler never called; replace with lightweight, nonblocking Smaart axis follow.
start=s.index('    def _check_phase_axis_drag(self,target):')
end=s.index('    def on_plot_layout(self,payload):',start)
new='''    def _check_phase_axis_drag(self,target):
        """Follow real Smaart Phase ruler while mouse held; settle to native REF."""
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            self.axis_drag=None
            return
        x,y,w,h=self.plot_layout.phase
        try:
            px,py=win32api.GetCursorPos()
            held=bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON)&0x8000)
        except Exception:
            return
        if self.axis_drag is None:
            if not held:
                self._axis_was_pressed=False
                return
            if self._axis_was_pressed:return
            self._axis_was_pressed=True
            if not(x-72<=px<=x+6 and y+10<=py<=y+h-10):
                return
            self.axis_drag={
                "hwnd":target.hwnd,
                "start":(px,py),
                "lo":self.graph_phase.y_min,
                "hi":self.graph_phase.y_max,
                "rect":self.plot_layout.phase,
                "preview_shift":0.}
            # Invalidate all already-captured absolute and relative frames.
            self._phase_axis_generation+=1
            self._phase_pan_last_frame=time.monotonic()
            print("V829_PHASE_GESTURE_BEGIN",px,py,
                  round(self.graph_phase.y_max,1),flush=True)
            return
        state=self.axis_drag
        if held:
            move=float(py-state["start"][1])
            if abs(move-state["preview_shift"])>=1.:
                state["preview_shift"]=move
                self._apply_phase_pan(move,state)
            return
        # Native Smaart can defer the actual axis repaint until release.
        # Fast pointer movement gives immediate preview; a fresh worker
        # absolutely registers the real REF phase after release.
        self.axis_drag=None
        self._axis_was_pressed=False
        self._phase_axis_generation+=1
        self._phase_pan_last_frame=time.monotonic()
        self.pan_last_move=time.monotonic()
        self.axis_requested=0.
        print("V829_PHASE_GESTURE_RELEASE",
              round(state["preview_shift"],1),
              round(self.graph_phase.y_max,1),flush=True)

'''
s=s[:start]+new+s[end:]
once('''        self._schedule_fast_pan(target)
        self._schedule_absolute_axis_calibration(target)
        self._schedule_mag_ref_anchor(target)''','''        self._check_phase_axis_drag(target)
        self._schedule_fast_pan(target)
        if self.axis_drag is None:
            self._schedule_absolute_axis_calibration(target)
        self._schedule_mag_ref_anchor(target)''')
path.write_text(s,encoding='utf-8')
print('V829_PHASE_GESTURE_WIRED',path)
