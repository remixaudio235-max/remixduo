from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
needle='''        if not active:
            self.native_eq.hide()
            # AUTO: hide model overlays when Smaart loses foreground.'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not active:
            self.native_eq.hide()
            # A previously verified pair must NOT be displayed immediately
            # on return from a minimized/background Smaart. Re-arm 3/3
            # native viewport snapshots before SUM and Auto Phase reappear.
            if self._was_target:
                self.engine.tick_gate.signature=None
                self.engine.tick_gate.stable=0
                self.engine._selection_quality="transient"
                self.engine._set_tick_presentation(False)
                self.engine.selection_warning.setText(
                    "Đang xác minh Trace sau khi trở lại Smaart")
                self.engine.selection_warning.show()
            # AUTO: hide model overlays when Smaart loses foreground.''',1)
p.write_text(s,encoding="utf8")
print("V824_FOREGROUND_REENTRY_REQUIRES_3_NEW_POLLS")
