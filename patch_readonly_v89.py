from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_9_TRACE_READONLY_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert 'RemiX Signal V8.8 - Windows QA' in s
s=s.replace('RemiX Signal V8.8 - Windows QA','RemiX Signal V8.9 - Windows QA')
s=s.replace('WINDOWS V8.8','WINDOWS V8.9')
needle='''        self.trace_grid.addWidget(self.delay,1,2)
        self.trace_grid.addWidget(self.invert,1,3)'''
assert s.count(needle)==1
s=s.replace(needle,'''        # V8.9: the solver still owns these values, but no user-editable
        # spinbox or checkbox is shown in any Trace row.
        self.delay.setParent(self)
        self.invert.setParent(self)
        self.delay.hide()
        self.invert.hide()''')
start=s.index('    def _update_delay_route_label(self,*_):')
end=s.index('    def on_ref_changed(self,*_):',start)
new='''    def _update_delay_route_label(self,*_):
        """Present both Trace decisions as read-only text, updated by solver."""
        ref=self._reference_index()
        target=1-ref
        names=tuple(self.current_pair or ())
        for i,label in enumerate(self.trace_name_labels):
            full=Path(names[i]).stem if len(names)==2 else "—"
            short=full if len(full)<=12 else full[:11]+"…"
            label.setText(f"{i+1:02d}  {short}")
            label.setToolTip(f"Trace {i+1}: {full}")
            value=self.delay.value() if i==target else 0.0
            inverted=(i==target and self.invert.isChecked())
            self.trace_delay_static[i].setText(f"{value:.2f} ms")
            self.trace_polarity_static[i].setText(
                "Đảo pha" if inverted else "Không đảo")
            self.trace_delay_static[i].setToolTip(
                "Kết quả Auto Align (chỉ đọc); không sửa trực tiếp ở đây.")
            self.trace_polarity_static[i].setToolTip(
                "Trạng thái Auto Align (chỉ đọc); không có checkbox.")
            self.trace_polarity_static[i].setStyleSheet(
                "color:#FFA86F;font:11px 'Segoe UI';"
                if inverted else
                "color:#A8C9D2;font:11px 'Segoe UI';")
        if hasattr(self,"delay_route_label"):
            self.delay_route_label.setText(
                f"Delay Trace {target+1}: +{self.delay.value():.2f} ms | "
                f"{'Đảo pha' if self.invert.isChecked() else 'Không đảo'} "
                f"| giữ Trace {ref+1}")
        if hasattr(self,"correction_target_label"):
            self.correction_target_label.setText(
                f"TRACE {ref+1} GIỮ NGUYÊN | TRỄ TRACE {target+1}")

'''
s=s[:start]+new+s[end:]
needle='''        self.invert.stateChanged.connect(self._update_delay_route_label)
        # V8.9:'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.invert.stateChanged.connect(self._update_delay_route_label)
        # V8.9:''')
# Original label inline placement already installed at both rows, preserve them.
assert 'self.trace_grid.addWidget(value,idx,2)' in s
assert 'self.trace_grid.addWidget(polarity,idx,3)' in s
assert 'self.trace_grid.addWidget(self.delay,1,2)' not in s
p.write_text(s,encoding="utf-8")
print("V89_READ_ONLY_TRACE_RESULT_PATCHED")
