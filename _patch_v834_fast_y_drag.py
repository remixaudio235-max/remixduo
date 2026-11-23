"""V8.34 fast signed Y preview on BOTH native Smaart rulers; stale frame veto."""
from pathlib import Path
p=Path(__file__).with_name('overlay_v7.py')
s=p.read_text(encoding='utf-8')
def sub(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError(f"Unsafe V834 patch: {n} occurrences of {old[:85]!r}")
    s=s.replace(old,new)
sub('import argparse,concurrent.futures,sys,time,os',
    'import argparse,concurrent.futures,sys,time,os\nfrom types import SimpleNamespace')
sub('        self.events.mag_anchor_ready.connect(self.on_mag_ref_anchor)\n'
    '        self.axis_drag=None\n        self._axis_was_pressed=False\n',
    '        self.events.mag_anchor_ready.connect(self.on_mag_ref_anchor)\n'
    '        self.axis_drag=None\n        self._axis_was_pressed=False\n'
    '        self.mag_axis_drag=None\n        self._mag_was_pressed=False\n'
    '        self._viewport_epoch=0\n'
    '        self._drag_spin_tick=0.0\n')
sub('        self.timer.start(33)\n        self._update_delay_route_label()',
    '        self.timer.start(33)\n'
    '        # Dedicated 60Hz lightweight cursor path: no GDI, TRF or FFT on Qt.\n'
    '        self.drag_timer=QTimer(self)\n'
    '        self.drag_timer.timeout.connect(self._fast_y_drag_tick)\n'
    '        self.drag_timer.start(16)\n'
    '        self._update_delay_route_label()')
sub('        if time.monotonic()-self.pan_last_move < .28:',
    '        if (getattr(self,"mag_axis_drag",None) is not None or\n'
    '            time.monotonic()-self.pan_last_move < .65):')
sub('        if now-self.pan_last_move<.28:return',
    '        if now-self.pan_last_move<.65:return')
sub('        if time.monotonic()-self.mag_pan_last_move<.42:return',
    '        if (getattr(self,"mag_axis_drag",None) is not None or\n'
    '            time.monotonic()-self.mag_pan_last_move<.65):return')
sub('        if now-self.mag_pan_last_move<.42:return',
    '        if now-self.mag_pan_last_move<.65:return')
sub('        expected=(self.plot_hwnd,self.plot_layout.phase,\n'
    '                  self.plot_layout.mag,tuple(self.current_pair or ()),\n'
    '                  self._reference_index())\n'
    '        if key!=expected:',
    '        expected=(self.plot_hwnd,self.plot_layout.phase,\n'
    '                  self.plot_layout.mag,tuple(self.current_pair or ()),\n'
    '                  self._reference_index())\n'
    '        # Worker captured before/during a 160+ px mouse drag MUST NOT\n'
    '        # apply its stale delta once the pointer is released.\n'
    '        if len(key)==6 and key[5]!=getattr(self,"_viewport_epoch",0):return\n'
    '        if key[:5]!=expected:')
sub('        threshold=.90 if is_mag else .85\n',
    '        if (getattr(self,"axis_drag",None) is not None or\n'
    '            getattr(self,"mag_axis_drag",None) is not None):return\n'
    '        threshold=.90 if is_mag else .85\n')
sub('        if not self.current_sum or not self.plot_layout:\n'
    '            return\n'
    '        now=time.monotonic()\n'
    '        # One worker, both charts;',
    '        if not self.current_sum or not self.plot_layout:\n'
    '            return\n'
    '        if (getattr(self,"axis_drag",None) is not None or\n'
    '            getattr(self,"mag_axis_drag",None) is not None):return\n'
    '        now=time.monotonic()\n'
    '        # One worker, both charts;')
sub('        key=(target.hwnd,self.plot_layout.phase,self.plot_layout.mag,\n'
    '             tuple(self.current_pair or ()),self._reference_index())\n',
    '        key=(target.hwnd,self.plot_layout.phase,self.plot_layout.mag,\n'
    '             tuple(self.current_pair or ()),self._reference_index(),\n'
    '             getattr(self,"_viewport_epoch",0))\n')
sub('        key=(target.hwnd,self.plot_layout.phase,\n'
    '             tuple(self.current_pair or ()),self._reference_index(),\n'
    '             self._phase_axis_generation)\n',
    '        key=(target.hwnd,self.plot_layout.phase,\n'
    '             tuple(self.current_pair or ()),self._reference_index(),\n'
    '             self._phase_axis_generation)\n') if False else None
# Phase gesture already exists. Make it invalidate old dual-axis captures and
# throttle costly hidden spinbox writes while maintaining immediate Qt repaint.
sub('            self._phase_axis_generation+=1\n'
    '            self._phase_pan_last_frame=time.monotonic()\n'
    '            print("V829_PHASE_GESTURE_BEGIN"',
    '            self._phase_axis_generation+=1\n'
    '            self._viewport_epoch+=1\n'
    '            self._phase_pan_last_frame=time.monotonic()\n'
    '            print("V829_PHASE_GESTURE_BEGIN"')
sub('        self._phase_axis_generation+=1\n'
    '        self._phase_pan_last_frame=time.monotonic()\n'
    '        self.pan_last_move=time.monotonic()\n'
    '        self.axis_requested=0.\n',
    '        self._phase_axis_generation+=1\n'
    '        self._viewport_epoch+=1\n'
    '        self._phase_pan_last_frame=time.monotonic()\n'
    '        self.pan_last_move=time.monotonic()\n'
    '        self.axis_requested=0.\n')
# Screen drag does not touch DSP or H(f). While dragging a large amplitude,
# update drawable viewport directly and postpone expensive controls.
sub('        self.phase_min.blockSignals(True)\n'
    '        self.phase_max.blockSignals(True)\n'
    '        try:\n'
    '            self.phase_min.setValue(lo)\n'
    '            self.phase_max.setValue(hi)\n'
    '        finally:\n'
    '            self.phase_min.blockSignals(False)\n'
    '            self.phase_max.blockSignals(False)\n'
    '        self.graph_phase.y_min=lo',
    '        now=time.monotonic()\n'
    '        if now-getattr(self,"_drag_spin_tick",0.)>.15:\n'
    '            self._drag_spin_tick=now\n'
    '            self.phase_min.blockSignals(True)\n'
    '            self.phase_max.blockSignals(True)\n'
    '            try:\n'
    '                self.phase_min.setValue(lo)\n'
    '                self.phase_max.setValue(hi)\n'
    '            finally:\n'
    '                self.phase_min.blockSignals(False)\n'
    '                self.phase_max.blockSignals(False)\n'
    '        self.graph_phase.y_min=lo')
# Place other ruler follow in same App just ahead of old phase handler.
anchor='    def _check_phase_axis_drag(self,target):\n'
if s.count(anchor)!=1:raise RuntimeError('Missing phase drag handler')
insert='''    def _fast_y_drag_tick(self):
        # Only pointer/Qt work on the GUI thread. Capture and native fitting
        # remain on their own workers and cannot block the 16ms fast lane.
        if not getattr(self,"plot_layout",None) or not self.current_sum:return
        hwnd=getattr(self,"plot_hwnd",None)
        if not hwnd or not self._target_is_foreground(hwnd):return
        target=SimpleNamespace(hwnd=hwnd)
        self._check_phase_axis_drag(target)
        self._check_mag_axis_drag(target)

    def _check_mag_axis_drag(self,target):
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            self.mag_axis_drag=None
            return
        x,y,w,h=self.plot_layout.mag
        try:
            px,py=win32api.GetCursorPos()
            held=bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON)&0x8000)
        except Exception:return
        state=getattr(self,"mag_axis_drag",None)
        if state is None:
            if not held:
                self._mag_was_pressed=False
                return
            if getattr(self,"_mag_was_pressed",False):return
            self._mag_was_pressed=True
            if getattr(self,"axis_drag",None) is not None:return
            if not (x-72<=px<=x+6 and y+10<=py<=y+h-10):return
            if not getattr(self,"_mag_anchor_verified",False):return
            self.mag_axis_drag={"start":(px,py),"lo":self.graph_mag.y_min,
                                "hi":self.graph_mag.y_max,
                                "rect":self.plot_layout.mag,"preview_shift":0.}
            self._viewport_epoch+=1
            self._mag_axis_generation+=1
            self._mag_pan_last_frame=time.monotonic()
            print("V834_MAG_GESTURE_BEGIN",px,py,flush=True)
            return
        if held:
            movement=float(py-state["start"][1])
            if abs(movement-state["preview_shift"])<1.:return
            state["preview_shift"]=movement
            # No 89px limit: position comes from the full mouse excursion
            # relative to the initial Mag viewport, never from a stale frame.
            lo,hi=shifted_y_range(state["lo"],state["hi"],
                                  state["rect"][3],movement)
            self.graph_mag.y_min=lo
            self.graph_mag.y_max=hi
            self.graph_mag.update()
            self.mag_pan_last_move=time.monotonic()
            if self.mag_pan_last_move-getattr(self,"_drag_spin_tick",0.)>.15:
                self._drag_spin_tick=self.mag_pan_last_move
                self.mag_min.blockSignals(True);self.mag_max.blockSignals(True)
                try:
                    self.mag_min.setValue(lo);self.mag_max.setValue(hi)
                finally:
                    self.mag_min.blockSignals(False);self.mag_max.blockSignals(False)
            return
        self.mag_axis_drag=None
        self._mag_was_pressed=False
        self._viewport_epoch+=1
        self._mag_axis_generation+=1
        self._mag_pan_last_frame=time.monotonic()
        self.mag_pan_last_move=time.monotonic()
        self.mag_anchor_requested=0.
        print("V834_MAG_GESTURE_RELEASE",
              round(state["preview_shift"],1),flush=True)

'''
s=s.replace(anchor,insert+anchor)
sub('        self._check_phase_axis_drag(target)\n'
    '        self._schedule_fast_pan(target)\n',
    '        self._check_phase_axis_drag(target)\n'
    '        self._check_mag_axis_drag(target)\n'
    '        self._schedule_fast_pan(target)\n')
# Restore stale callback state on session loss and close timer on exit.
sub('            self.axis_drag=None\n'
    '            self._axis_was_pressed=False\n'
    '            self.overlay_positioned=False;',
    '            self.axis_drag=None\n'
    '            self._axis_was_pressed=False\n'
    '            self.mag_axis_drag=None\n'
    '            self._mag_was_pressed=False\n'
    '            self._viewport_epoch+=1\n'
    '            self.overlay_positioned=False;')
sub('        self.axis_pool.shutdown(wait=False,cancel_futures=True)',
    '        self.drag_timer.stop()\n'
    '        self.axis_pool.shutdown(wait=False,cancel_futures=True)')
p.write_text(s,encoding='utf-8')
print('V834_PATCH_APPLIED',p,flush=True)
