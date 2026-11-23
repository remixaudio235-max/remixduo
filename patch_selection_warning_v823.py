"""V8.23 UX: show verified number of selected Smaart Data Bar traces.

This does not uncheck any Trace or guess which two user intended.
"""
from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_23_TRACE_SYNC_GUARD_QA\overlay_v7.py")
s=p.read_text(encoding="utf8")
needle="        trace.addLayout(self.trace_grid)"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        self.selection_warning=QLabel("")
        self.selection_warning.setObjectName("selectionWarning")
        self.selection_warning.setWordWrap(True)
        self.selection_warning.setStyleSheet(
            "color:#FFD1A1;background:#352418;border:1px solid #A36A25;"
            "font:bold 10px 'Segoe UI';border-radius:5px;padding:4px;")
        trace.addWidget(self.selection_warning)
        self.selection_warning.hide()''')
needle='''        if not isinstance(result,SyncResult):
            self._selection_verified=False
            self._selection_last_status="Invalid scanner result"
            self.status.setText(self._selection_last_status)
            self.refresh_visibility()
            return'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not isinstance(result,SyncResult):
            self._selection_verified=False
            self._selection_last_status="Invalid scanner result"
            self.selection_warning.setText("Chưa xác minh được Trace")
            self.selection_warning.show()
            self.status.setText(self._selection_last_status)
            self.refresh_visibility()
            return''')
needle='''        if not confirmed:
            self.status.setText("Dang x�c minh Trace: "+status[:100])
            self.refresh_visibility()
            return
        if result.pair is None:
            if self.controller.last_pair:'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not confirmed:
            self.selection_warning.setText("Đang xác minh tick Data Bar...")
            self.selection_warning.show()
            self.status.setText("Dang xac minh Trace: "+status[:100])
            self.refresh_visibility()
            return
        active=[
            self.observer.order[i].name
            for i,v in sorted(self.observer.states.items())
            if v=="on" and 0<=i<len(self.observer.order)
        ] if getattr(self.observer,"order",None) else []
        if result.pair is None:
            count=len(active)
            text=(f"Đang bật {count} Trace — cần đúng 2"
                  if count else "Hãy bật đúng 2 Trace trong Data Bar")
            self.selection_warning.setText(text)
            self.selection_warning.setToolTip(
                "Trace bật: "+", ".join(active) if active else status)
            self.selection_warning.show()
            if self.controller.last_pair:''')
needle='''        else:
            self.controller.apply(result.pair,"Win UIA tick verified")
            if self.current_traces:self.status.setText(status)
        self.refresh_visibility()'''
assert s.count(needle)==1
s=s.replace(needle,'''        else:
            self.selection_warning.hide()
            self.controller.apply(result.pair,"Win UIA tick verified")
            if self.current_traces:self.status.setText(status)
        self.refresh_visibility()''')
p.write_text(s,encoding="utf8")
print("V823_USER_VISIBLE_6_TRACES_WARNING_PASS")
