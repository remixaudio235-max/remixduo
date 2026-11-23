from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_7_PHASE_AXIS_FOLLOW_QA')
p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('import win32gui,win32con,win32process','import win32gui,win32con,win32process,win32api')
s=s.replace('from roi_markers_v73 import ROIMarker, hz_to_x, x_to_hz, bound_drag',
'''from roi_markers_v73 import ROIMarker, hz_to_x, x_to_hz, bound_drag
from phase_axis_follow_v77 import (capture_native_phase,
    detect_vertical_shift,shifted_y_range)''')
s=s.replace('RemiX Auto Align V7.6 - Windows QA','RemiX Auto Align V7.7 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.6','RemiX  AUTO ALIGN  V7.7')
s=s.replace('self.setFixedSize(354,666)','self.setFixedSize(354,692)')
needle='''        self.events.layout_ready.connect(self.on_plot_layout)
        # Initial UIA map not verified: fail-closed rather than mislabel.'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.events.layout_ready.connect(self.on_plot_layout)
        self.axis_drag=None
        self._axis_was_pressed=False
        self.phase_axis_note=QLabel(
            "Phase Y: kéo trục Y của Smaart → SUM theo trục (không chạy lại TF)")
        self.phase_axis_note.setStyleSheet("color:#9cd3f2;font:10px 'Segoe UI'")
        layout.insertWidget(layout.indexOf(self.axis_note),self.phase_axis_note)
        # Initial UIA map not verified: fail-closed rather than mislabel.''')
needle='''    def update_y_ranges(self,*_):
        if not hasattr(self,"graph_mag"):return
        if self.mag_max.value()>self.mag_min.value():
            self.graph_mag.y_min=self.mag_min.value()
            self.graph_mag.y_max=self.mag_max.value()
        if self.phase_max.value()>self.phase_min.value():
            self.graph_phase.y_min=self.phase_min.value()
            self.graph_phase.y_max=self.phase_max.value()
        if self.current_traces:self.recalc()
        else:self.graph_mag.update();self.graph_phase.update()'''
assert s.count(needle)==1
s=s.replace(needle,'''    def update_y_ranges(self,*_):
        """Pure viewport transform: NEVER rerun complex SUM or Auto Align."""
        if not hasattr(self,"graph_mag"):return
        if self.mag_max.value()>self.mag_min.value():
            self.graph_mag.y_min=self.mag_min.value()
            self.graph_mag.y_max=self.mag_max.value()
        if self.phase_max.value()>self.phase_min.value():
            self.graph_phase.y_min=self.phase_min.value()
            self.graph_phase.y_max=self.phase_max.value()
        self.graph_mag.update()
        self.graph_phase.update()

    def _apply_phase_pan(self,shift_px,drag_state,verified=False,confidence=0.):
        if not getattr(self,"plot_layout",None):
            return
        _,_,_,height=self.plot_layout.phase
        if height<=0:
            return
        lo,hi=shifted_y_range(drag_state["lo"],drag_state["hi"],
                             height,shift_px)
        self.phase_min.blockSignals(True)
        self.phase_max.blockSignals(True)
        try:
            self.phase_min.setValue(lo)
            self.phase_max.setValue(hi)
        finally:
            self.phase_min.blockSignals(False)
            self.phase_max.blockSignals(False)
        self.graph_phase.y_min=lo
        self.graph_phase.y_max=hi
        self.graph_phase.update()
        label=("Native-trace verified" if verified else
               "Mouse-motion preview (Y cần kiểm tra)")
        self.phase_axis_note.setText(
            f"Phase Y sync {label}: shift {shift_px:+.0f}px"
            + (f" | confidence {confidence:.2f}" if verified else ""))

    def _check_phase_axis_drag(self,target):
        """Track Smaart Phase Y-ruler drag; all graph and TF data are read-only."""
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            self.axis_drag=None
            return
        x,y,w,h=self.plot_layout.phase
        # The scale ruler is immediately left of the Phase canvas (roughly
        # x=200..252 in the original Smaart layout).
        try:
            px,py=win32api.GetCursorPos()
            held=bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON)&0x8000)
        except Exception:
            return
        if self.axis_drag is None:
            if not held or self._axis_was_pressed:
                self._axis_was_pressed=held
                return
            self._axis_was_pressed=True
            if not(x-72<=px<=x+6 and y+10<=py<=y+h-10):
                return
            try:
                before=capture_native_phase(target.hwnd,self.plot_layout.phase)
            except Exception as exc:
                self.phase_axis_note.setText(
                    "Phase Y read-only capture unavailable: "+str(exc)[:65])
                return
            self.axis_drag={
                "hwnd":target.hwnd,
                "start":(px,py),
                "lo":self.graph_phase.y_min,"hi":self.graph_phase.y_max,
                "before":before,
                "rect":self.plot_layout.phase,
                "preview_shift":0.}
            print("V77_PHASE_AXIS_DRAG_START",px,py,flush=True)
            return
        current=self.axis_drag
        if held:
            # Live preview follows physical pointer; pixel-correlation on
            # release corrects pan direction/amount if Smaart differs.
            pixel_shift=float(py-current["start"][1])
            if abs(pixel_shift-current["preview_shift"])>=1:
                current["preview_shift"]=pixel_shift
                self._apply_phase_pan(pixel_shift,current)
            return
        self._axis_was_pressed=False
        self.axis_drag=None
        try:
            if current["hwnd"]!=target.hwnd or current["rect"]!=self.plot_layout.phase:
                raise ValueError("Smaart chart geometry changed")
            after=capture_native_phase(target.hwnd,self.plot_layout.phase)
            observed=detect_vertical_shift(current["before"],after)
            if observed.valid:
                self._apply_phase_pan(observed.shift_px,current,True,
                                      observed.confidence)
                print("V77_PHASE_Y_FOLLOW_CONFIRMED",
                      observed.shift_px,observed.confidence,flush=True)
            else:
                # No numerical Y-axis data is exposed; retain the approximate
                # mouse-motion preview and explicitly label it unverified.
                self.phase_axis_note.setText(
                    "Phase Y motion estimate; "+observed.explanation+
                    " • chỉnh Y min/max nếu cần")
                print("V77_PHASE_Y_FOLLOW_UNVERIFIED",
                      observed.explanation,flush=True)
        except Exception as exc:
            self.phase_axis_note.setText(
                "Phase Y follow cannot confirm: "+str(exc)[:65])
            print("V77_PHASE_Y_CAPTURE_ERROR",str(exc),flush=True)''')
needle='''        if not self.isVisible():self.show()
        l,t,r,b=target.rect'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not self.isVisible():self.show()
        self._check_phase_axis_drag(target)
        l,t,r,b=target.rect''')
needle='''        if target is None or not self._target_is_foreground(target.hwnd):
            self.overlay_positioned=False;self.refresh_visibility()'''
assert s.count(needle)==1
s=s.replace(needle,'''        if target is None or not self._target_is_foreground(target.hwnd):
            self.axis_drag=None
            self._axis_was_pressed=False
            self.overlay_positioned=False;self.refresh_visibility()''')
p.write_text(s,encoding='utf-8')
print('V77_OVERLAY_AXIS_FOLLOW_PATCH_OK')
