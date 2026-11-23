from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_8_TRACE_INLINE_DELAY_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert 'RemiX Signal V8.7 - Windows QA' in s
s=s.replace('RemiX Signal V8.7 - Windows QA','RemiX Signal V8.8 - Windows QA')
s=s.replace('WINDOWS V8.7','WINDOWS V8.8')
s=s.replace('self.setFixedSize(402,547)','self.setFixedSize(402,515)')
needle='''        trace.addWidget(self.pair_label)
        refrow=QHBoxLayout()'''
assert s.count(needle)==1
s=s.replace(needle,'''        trace.addWidget(self.pair_label)
        self.pair_label.hide()  # Preserve legacy name updates, use per-row UI.
        self.trace_grid=QGridLayout()
        self.trace_grid.setContentsMargins(1,0,1,0)
        self.trace_grid.setHorizontalSpacing(6)
        self.trace_grid.setVerticalSpacing(7)
        self.trace_grid.setColumnStretch(0,1)
        self.trace_grid.setColumnMinimumWidth(0,87)
        self.trace_grid.setColumnMinimumWidth(2,94)
        self.trace_grid.setColumnMinimumWidth(3,95)
        self.trace_name_labels=[]
        self.trace_delay_static=[]
        self.trace_polarity_static=[]
        self.trace_delay_tags=[]
        for idx in range(2):
            name=QLabel(f"{idx+1:02d}  —")
            name.setStyleSheet("color:#F0FAFF;font:bold 11px 'Segoe UI';")
            name.setMinimumWidth(86)
            name.setToolTip("Tên file Trace đang chọn trong Smaart")
            self.trace_name_labels.append(name)
            self.trace_grid.addWidget(name,idx,0)
            delay_tag=QLabel("Delay:")
            delay_tag.setStyleSheet("color:#92BBC7;font:10px 'Segoe UI';")
            self.trace_delay_tags.append(delay_tag)
            self.trace_grid.addWidget(delay_tag,idx,1)
            value=QLabel("0.00 ms")
            value.setStyleSheet("color:#9EC5D3;font:11px 'Segoe UI';")
            self.trace_delay_static.append(value)
            self.trace_grid.addWidget(value,idx,2)
            polarity=QLabel("Không đảo")
            polarity.setStyleSheet("color:#A8C9D2;font:10px 'Segoe UI';")
            self.trace_polarity_static.append(polarity)
            self.trace_grid.addWidget(polarity,idx,3)
        trace.addLayout(self.trace_grid)
        refrow=QHBoxLayout()''')
start=s.index('        delayrow=QHBoxLayout()')
end=s.index('        self.solve=QPushButton("AUTO ALIGN")',start)
orig=s[start:end]
assert 'self.delay=QDoubleSpinBox()' in orig and 'self.invert=QCheckBox' in orig
replacement='''        # Delay and phase inversion now live directly in the affected
        # TRACE row. Reference row displays 0.00ms / Không đảo.
        self.delay=QDoubleSpinBox()
        self.delay.setRange(0,180)
        self.delay.setDecimals(2)
        self.delay.setSingleStep(.1)
        self.delay.setSuffix(" ms")
        self.delay.setMinimumWidth(94)
        self.delay.setMaximumWidth(105)
        self.delay.setToolTip(
            "Delay dương chỉ áp dụng cho Trace được ghi ở dòng này.")
        self.delay.valueChanged.connect(self.recalc)
        self.delay.valueChanged.connect(self._update_delay_route_label)
        self.invert=QCheckBox("Không đảo")
        self.invert.setMinimumWidth(95)
        self.invert.setToolTip(
            "Bật: Đảo pha cho chính Trace được Delay. Tắt: Không đảo.")
        self.invert.stateChanged.connect(self.recalc)
        self.invert.stateChanged.connect(self._update_delay_route_label)
        self.trace_grid.addWidget(self.delay,1,2)
        self.trace_grid.addWidget(self.invert,1,3)
        # Retain legacy text object for status/tests, but never duplicate
        # its information in the Auto Align section.
        self.delay_route_label=QLabel("")
        self.delay_route_label.hide()
'''
s=s[:start]+replacement+s[end:]
start=s.index('    def _update_delay_route_label(self,*_):')
end=s.index('    def on_ref_changed(self,*_):',start)
new='''    def _update_delay_route_label(self,*_):
        """Inline display always agrees with the physical delay target."""
        ref=self._reference_index()
        target=1-ref
        names=tuple(self.current_pair or ())
        for i,name_label in enumerate(self.trace_name_labels):
            full=Path(names[i]).stem if len(names)==2 else "—"
            # Use the real selected filename in tooltip if name is long.
            shortened=full if len(full)<=12 else full[:11]+"…"
            name_label.setText(f"{i+1:02d}  {shortened}")
            name_label.setToolTip(f"Trace {i+1}: {full}")
            if i==ref:
                self.trace_delay_static[i].setText("0.00 ms")
                self.trace_polarity_static[i].setText("Không đảo")
                self.trace_delay_static[i].show()
                self.trace_polarity_static[i].show()
            else:
                self.trace_delay_static[i].hide()
                self.trace_polarity_static[i].hide()
        # Both editable controls are placed on the actual target row;
        # when Auto Align changes REF, they move together atomically.
        current_row=getattr(self,"_inline_target_index",None)
        if current_row!=target:
            self.trace_grid.removeWidget(self.delay)
            self.trace_grid.removeWidget(self.invert)
            self.trace_grid.addWidget(self.delay,target,2)
            self.trace_grid.addWidget(self.invert,target,3)
            self.delay.show()
            self.invert.show()
            self._inline_target_index=target
        self.invert.setText("Đảo pha" if self.invert.isChecked()
                            else "Không đảo")
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
p.write_text(s,encoding='utf-8')
print("V88_INLINE_TRACE_DELAY_AND_POLARITY_PATCHED")
