from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_7_POSITIVE_DELAY_ROUTE_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
assert "positive_delay_route_v87" not in s
needle='from sum_render_v84 import make_geometry'
assert s.count(needle)==1
s=s.replace(needle,needle+'\nfrom positive_delay_route_v87 import route_candidate')
s=s.replace('RemiX Signal V8.6 - Windows QA','RemiX Signal V8.7 - Windows QA')
s=s.replace('WINDOWS V8.6','WINDOWS V8.7')
s=s.replace('self.setFixedSize(402,510)','self.setFixedSize(402,547)')
needle='''        delayrow.addWidget(tag("SHIFT"))
        self.delay=QDoubleSpinBox()
        self.delay.setRange(-180,180)'''
assert s.count(needle)==1
s=s.replace(needle,'''        delayrow.addWidget(tag("DELAY"))
        self.delay=QDoubleSpinBox()
        # A negative shift is a solver convention, NOT a valid DSP delay.
        self.delay.setRange(0,180)''')
needle='''        self.invert=QCheckBox("ĐẢO TRACE 2")'''
if needle not in s:
    needle='''        self.invert=QCheckBox("D?O TRACE 2")'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.invert=QCheckBox("ĐẢO TRACE 2")''')
needle='''        control.addLayout(delayrow)
        self.solve=QPushButton("AUTO ALIGN")'''
assert s.count(needle)==1
s=s.replace(needle,'''        control.addLayout(delayrow)
        self.delay_route_label=QLabel("TRỄ TRACE 2 · +0.00 ms  |  MỐC TRACE 1")
        self.delay_route_label.setWordWrap(True)
        self.delay_route_label.setMinimumHeight(25)
        self.delay_route_label.setToolTip(
            "Mô hình TF: thêm Delay DƯƠNG cho Trace được ghi rõ, "
            "giữ nguyên Trace mốc. Cần kiểm chứng thời gian đến thực tế "
            "bằng IR trước khi nhập Delay vào DSP.")
        self.delay_route_label.setStyleSheet(
            "color:#4FE9FF;background:#102B38;border:1px solid #27596C;"
            "border-radius:6px;font:bold 11px 'Segoe UI';padding:4px 6px;")
        control.addWidget(self.delay_route_label)
        self.delay.valueChanged.connect(self._update_delay_route_label)
        self.solve=QPushButton("AUTO ALIGN")''')
# selected pair resets reference to known state to avoid target reuse
needle='''        self.last_solve=None
        self.delay.blockSignals(True);self.delay.setValue(0.);self.delay.blockSignals(False)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.last_solve=None
        self.ref_choice.blockSignals(True)
        self.ref_choice.setCurrentIndex(0)
        self.ref_choice.blockSignals(False)
        self.delay.blockSignals(True);self.delay.setValue(0.);self.delay.blockSignals(False)''')
needle='''        self.invert.blockSignals(True);self.invert.setChecked(False);self.invert.blockSignals(False)
        for label in self.candidates:label.setText("-")'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.invert.blockSignals(True);self.invert.setChecked(False);self.invert.blockSignals(False)
        self._update_delay_route_label()
        for label in self.candidates:label.setText("-")''')
start=s.index('    def on_ref_changed(self,*_):')
end=s.index('    def recalc(self,*_):',start)
new='''    def _update_delay_route_label(self,*_):
        """User-visible physical routing, positive-only; never solver sign."""
        ref_num=self._reference_index()+1
        delayed=2 if ref_num==1 else 1
        if hasattr(self,"delay_route_label"):
            self.delay_route_label.setText(
                f"TRỄ TRACE {delayed}: +{self.delay.value():.2f} ms"
                f"  |  MỐC TRACE {ref_num}")
        if hasattr(self,"invert"):
            self.invert.setText(f"ĐẢO TRACE {delayed}")
        if hasattr(self,"correction_target_label"):
            self.correction_target_label.setText(
                f"TRACE {ref_num} GIỮ NGUYÊN | TRỄ TRACE {delayed}")

    def on_ref_changed(self,*_):
        # A reference change changes the PHYSICAL delayed target; it must
        # never negate an already-positive DSP delay or silently advance.
        self._update_delay_route_label()
        self.last_solve=None
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        for label in self.candidates:
            label.setText("—")
        if self.current_traces:
            self.recalc()
            ref=self._reference_index()+1
            target=2 if ref==1 else 1
            self.status.setText(
                f"REF TRACE {ref} | TRỄ TRACE {target} "
                f"+{self.delay.value():.2f}ms, chọn AUTO ALIGN để tối ưu.")
        else:
            self._clear_phase_match()

'''
s=s[:start]+new+s[end:]
start=s.index('    def align(self):')
end=s.index('    def found(self,pair,status):',start)
new='''    def align(self):
        if not self.current_traces:
            self.status.setText("Cần đủ 2 Trace đã xác nhận.")
            return
        gen=self.controller.generation
        pair=self.controller.last_pair
        # Always solve ORIGINAL TRACE 1 versus ORIGINAL TRACE 2.
        # Do not feed current REF order to the signed solver or the
        # direction can flip on consecutive AUTO ALIGN clicks.
        a,b=self.current_traces
        results=auto_align(a,b,lf=self.lf.value(),hf=self.hf.value(),
                           max_delay_ms=180)
        if not self.controller.is_current(gen,pair):return
        self.last_solve=results
        if not results:
            self.status.setText("Không đủ Coherence trong LF/HF để căn chỉnh.")
            return
        route=route_candidate(results[0])
        # Apply as a nonnegative real delay on the earlier modeled Trace.
        # INV applies to that same delayed Trace, NEVER an ambiguous T2.
        self.ref_choice.blockSignals(True)
        self.delay.blockSignals(True)
        self.invert.blockSignals(True)
        try:
            self.ref_choice.setCurrentIndex(route.reference_index)
            self.delay.setValue(route.delay_ms)
            self.invert.setChecked(route.invert_target)
        finally:
            self.ref_choice.blockSignals(False)
            self.delay.blockSignals(False)
            self.invert.blockSignals(False)
        self._update_delay_route_label()
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        self.status.setText(
            f"MÔ HÌNH TF: TRỄ TRACE {route.delay_trace} "
            f"+{route.delay_ms:.2f}ms | GIỮ TRACE {route.reference_trace} | "
            f"{'ĐẢO' if route.invert_target else 'KHÔNG ĐẢO'} TRACE "
            f"{route.delay_trace}. Xác minh bằng IR trước khi áp dụng DSP.")
        for i,label in enumerate(self.candidates):
            if i<len(results):
                c=route_candidate(results[i])
                label.setText(
                    f"#{i+1} TRỄ T{c.delay_trace} +{c.delay_ms:.2f}ms | "
                    f"{'INV' if c.invert_target else 'NOR'} | "
                    f"{c.score_db:.2f}dB")
            else:
                label.setText("—")
        self.recalc()

'''
s=s[:start]+new+s[end:]
# Initial target label always correct
needle='''        self.timer.start(33)
        self.show()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.timer.start(33)
        self._update_delay_route_label()
        self.show()''')
p.write_text(s,encoding='utf-8')
print("V87_POSITIVE_DELAY_GUI_AND_SOLVER_ROUTING_PATCHED")
