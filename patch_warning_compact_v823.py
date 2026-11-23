from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_23_TRACE_SYNC_GUARD_QA\overlay_v7.py")
s=p.read_text(encoding="utf8")
needle='''        if not isinstance(result,SyncResult):
            self._selection_verified=False'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not isinstance(result,SyncResult):
            for widget in (*self.trace_name_labels,*self.trace_compact_result):
                widget.hide()
            self._selection_verified=False''')
needle='''        if not confirmed:
            self.selection_warning.setText'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not confirmed:
            for widget in (*self.trace_name_labels,*self.trace_compact_result):
                widget.hide()
            self.selection_warning.setText''')
needle='''        if result.pair is None:
            count=len(active)'''
assert s.count(needle)==1
s=s.replace(needle,'''        if result.pair is None:
            for widget in (*self.trace_name_labels,*self.trace_compact_result):
                widget.hide()
            count=len(active)''')
needle='''        else:
            self.selection_warning.hide()
            self.controller.apply(result.pair'''
assert s.count(needle)==1
s=s.replace(needle,'''        else:
            self.selection_warning.hide()
            for widget in (*self.trace_name_labels,*self.trace_compact_result):
                widget.show()
            self.controller.apply(result.pair''')
p.write_text(s,encoding="utf8")
print("V823_WARNING_REPLACES_BLANK_TRACE_ROWS_PASS")
