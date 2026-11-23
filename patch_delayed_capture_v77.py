from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_7_PHASE_AXIS_FOLLOW_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
start=s.index('        self._axis_was_pressed=False\n        self.axis_drag=None\n        try:\n            if current["hwnd"]!=target.hwnd')
end=s.index('\n    def on_plot_layout(',start)
print("PATCH_FOUND",start,end)
replacement='''        self._axis_was_pressed=False
        self.axis_drag=None
        # Smaart must finish native paint after drag before we correlate
        # original Smaart trace pixels. No TF recomputation.
        QTimer.singleShot(130,lambda state=current:self._finish_phase_pan(state))

    def _finish_phase_pan(self,current):
        if self.axis_drag is not None or not getattr(self,"plot_layout",None):
            return
        try:
            target=locate_smaart()
            if target is None or not self._target_is_foreground(target.hwnd):
                return
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
                self.phase_axis_note.setText(
                    "Phase Y motion estimate; "+observed.explanation+
                    " • chỉnh Y min/max nếu cần")
                print("V77_PHASE_Y_FOLLOW_UNVERIFIED",
                      observed.explanation,flush=True)
        except Exception as exc:
            self.phase_axis_note.setText(
                "Phase Y follow cannot confirm: "+str(exc)[:65])
            print("V77_PHASE_Y_CAPTURE_ERROR",str(exc),flush=True)
'''
s=s[:start]+replacement+s[end:]
p.write_text(s,encoding='utf-8')
print("V77_DEFERRED_CAPTURE_PATCH_PASS")
