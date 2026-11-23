"""V8.34 speed native tracker: while Y gesture active only poll that axis."""
from pathlib import Path
a=Path(__file__).with_name('native_dual_y_v82.py')
b=Path(__file__).with_name('overlay_v7.py')
s=a.read_text(encoding='utf-8-sig')
old='''    def poll(self,key,phase_rect,mag_rect):
        # A single worker thread owns both GDI captures; reuse DC to avoid
        # creating a second expensive display capture context.
        phase=self.phase.poll((key,"phase"),phase_rect)
        if self.mag.dc is None and self.phase.dc is not None:
            self.mag.dc=self.phase.dc
        mag=self.mag.poll((key,"mag"),mag_rect)
        return DualPanResult(phase,mag)
'''
new='''    def poll(self,key,phase_rect,mag_rect,active_kind=None):
        # An active Smaart ruler needs only its own plot pixels. Avoid a
        # second unnecessary screenshot/correlation inside fast gesture.
        import time
        inactive=lambda:PanFrame(0.,0.,False,"Inactive plot",0.,time.monotonic())
        phase=(self.phase.poll((key,"phase"),phase_rect)
               if active_kind in (None,"phase") else inactive())
        if self.mag.dc is None and self.phase.dc is not None:
            self.mag.dc=self.phase.dc
        mag=(self.mag.poll((key,"mag"),mag_rect)
             if active_kind in (None,"mag") else inactive())
        return DualPanResult(phase,mag)
'''
if s.count(old)!=1:raise RuntimeError('NativeDual old function changed')
a.write_text(s.replace(old,new),encoding='utf-8')
t=b.read_text(encoding='utf-8')
old='''        self.pan_future=self.pan_pool.submit(
            self.pan_tracker.poll,key,self.plot_layout.phase,
            self.plot_layout.mag)
'''
new='''        active_kind=("phase" if getattr(self,"axis_drag",None) is not None
                     else "mag" if getattr(self,"mag_axis_drag",None) is not None
                     else None)
        self.pan_future=self.pan_pool.submit(
            self.pan_tracker.poll,key,self.plot_layout.phase,
            self.plot_layout.mag,active_kind)
'''
if t.count(old)!=1:raise RuntimeError('Fast pan call changed')
t=t.replace(old,new,1)
old='''        self._check_phase_axis_drag(target)
        self._check_mag_axis_drag(target)

    def _check_mag_axis_drag'''
new='''        self._check_phase_axis_drag(target)
        self._check_mag_axis_drag(target)
        if (getattr(self,"axis_drag",None) is not None or
            getattr(self,"mag_axis_drag",None) is not None):
            self._schedule_fast_pan(target)

    def _check_mag_axis_drag'''
if t.count(old)!=1:raise RuntimeError('Fast drag tick changed')
t=t.replace(old,new,1)
b.write_text(t,encoding='utf-8')
print('V834_SINGLE_ACTIVE_NATIVE_POLL_APPLIED',flush=True)
