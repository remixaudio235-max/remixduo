from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_8_TRACE_INLINE_DELAY_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
a=s.index('        for i,name_label in enumerate(self.trace_name_labels):')
b=s.index('        self.invert.setText("Đảo pha" if',a)
new='''        # Remove static cells before reflow to avoid overlapping two
        # QWidgets in the same QGridLayout position when REF swaps.
        for i in range(2):
            self.trace_delay_static[i].hide()
            self.trace_polarity_static[i].hide()
            self.trace_grid.removeWidget(self.trace_delay_static[i])
            self.trace_grid.removeWidget(self.trace_polarity_static[i])
        for i,name_label in enumerate(self.trace_name_labels):
            full=Path(names[i]).stem if len(names)==2 else "—"
            shortened=full if len(full)<=12 else full[:11]+"…"
            name_label.setText(f"{i+1:02d}  {shortened}")
            name_label.setToolTip(f"Trace {i+1}: {full}")
        current_row=getattr(self,"_inline_target_index",None)
        if current_row!=target:
            self.trace_grid.removeWidget(self.delay)
            self.trace_grid.removeWidget(self.invert)
            self.trace_grid.addWidget(self.delay,target,2)
            self.trace_grid.addWidget(self.invert,target,3)
            self.delay.show()
            self.invert.show()
            self._inline_target_index=target
        self.trace_grid.addWidget(self.trace_delay_static[ref],ref,2)
        self.trace_grid.addWidget(self.trace_polarity_static[ref],ref,3)
        self.trace_delay_static[ref].setText("0.00 ms")
        self.trace_polarity_static[ref].setText("Không đảo")
        self.trace_delay_static[ref].show()
        self.trace_polarity_static[ref].show()
'''
s=s[:a]+new+s[b:]
p.write_text(s,encoding='utf-8')
print('V88_GRID_REF_SWAP_NO_OVERLAP_FIXED')
