"""RemiX Signal V8.17: large Trace status, selectable Top-3 previews."""
from pathlib import Path
import re

root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_17_TRACE_TOP3_SELECT_QA")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
s=s.replace("RemiX Signal V8.16","RemiX Signal V8.17")
s=s.replace("SMAART · V8.16","SMAART · V8.17")

needle='''            name.setStyleSheet("color:#F0FAFF;font:bold 10px 'Segoe UI';")'''
assert s.count(needle)==1
s=s.replace(needle,'''            name.setObjectName("traceNameLarge")
            name.setStyleSheet(
                "color:#F5FDFF;font:bold 12px 'Segoe UI';"
                "padding-top:2px;")
            name.setMinimumHeight(22)''')
needle='''            result.setMinimumHeight(16)'''
assert s.count(needle)==1
s=s.replace(needle,'''            result.setMinimumHeight(25)
            result.setObjectName("traceDelayLarge")''')

start=s.index('        self.candidates=[QLabel("—") for _ in range(3)]')
end=s.index('\n        # Compact tabs',start)
s=s[:start]+'''        self.candidates=[]
        self.active_candidate_index=None
        self._candidate_scope=None
        for i in range(3):
            button=QPushButton(f"#{i+1}  --")
            button.setObjectName("candidateOption")
            button.setFixedHeight(44)
            button.setEnabled(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip("Chọn phương án để xem SUM Mag/Phase. Không ghi DSP.")
            button.clicked.connect(
                lambda checked=False,index=i:self.select_candidate(index))
            self.candidates.append(button)
            candidates_card.addWidget(button)
''' + s[end:]

# Style buttons without layout clipping and show active button distinctly.
needle='''            QPushButton#run:hover {background:#FFAF55;}'''
assert s.count(needle)==1
s=s.replace(needle,'''             QPushButton#candidateOption {
                 background:#172C3D;color:#E8F8FF;
                 border:1px solid #355669;border-radius:7px;
                 font:bold 11px 'Segoe UI';text-align:left;
                 padding:3px 6px;min-height:40px;}
             QPushButton#candidateOption:hover {
                 background:#21465B;border:1px solid #6BC5E0;}
             QPushButton#candidateOption:checked {
                 background:#174535;color:#ACFFBE;
                 border:2px solid #52ED93;}
             QPushButton#candidateOption:disabled {
                 background:#111C28;color:#536F7C;
                 border:1px solid #233D4A;}
            QPushButton#run:hover {background:#FFAF55;}''')
needle='''            button.setFixedHeight(44)
            button.setEnabled(False)'''
assert s.count(needle)==1
s=s.replace(needle,'''            button.setFixedHeight(44)
            button.setCheckable(True)
            button.setEnabled(False)''')
# Make trace route big / readable and colors distinct for affected target
start=s.index('            label.setText(f"{i+1:02d}  {shortened}")')
end=s.index('        if hasattr(self,"delay_route_label"):',start)
s=s[:start]+'''            label.setText(f"TRACE {i+1} · {shortened}")
            label.setToolTip(f"Trace {i+1}: {full}")
            val=self.delay.value() if i==target else 0.0
            inv=i==target and self.invert.isChecked()
            polarity="Đảo pha" if inv else "Không đảo"
            self.trace_delay_static[i].setText(f"{val:.2f} ms")
            self.trace_polarity_static[i].setText(polarity)
            self.trace_compact_result[i].setText(
                f"Delay: {val:.2f} ms · {polarity}")
            self.trace_compact_result[i].setStyleSheet(
                "font:bold 12px 'Segoe UI';color:"
                +("#FFB46A;" if inv else
                  "#7DF1BF;" if i==target and val>0 else "#D6E9F4;"))
            self.trace_compact_result[i].setToolTip(
                f"Trace {i+1} · Delay: {val:.2f} ms · {polarity} "
                "(kết quả mô phỏng, không nạp DSP)")
''' + s[end:]

# On selection cleanup, even if pair is invalid.
needle='''        self.last_solve=None
        self.ref_choice.blockSignals(True)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.last_solve=None
        self._clear_candidate_buttons()
        self.ref_choice.blockSignals(True)''')
# Previous resetting loop safe to delete to avoid overwriting disabled button labels.
needle='''        for label in self.candidates:label.setText("—")'''
# previous candidate clear is replaced via regex
s=re.sub(r'(?m)^[ ]*for label in self\.candidates:label\.setText\([^\n]*\)\n',"",s,count=1)

# Replace on REF change old invalidation/refresh manual.
start=s.index('    def on_ref_changed(self,*_):')
end=s.index('    def _refresh_saved_smoothing(self,force=False):',start)
section=s[start:end]
section=section.replace('''        self.last_solve=None''','''        self.last_solve=None
        self._clear_candidate_buttons()''')
section=section.replace('''        for label in self.candidates:
            label.setText("—")
''',"")
s=s[:start]+section+s[end:]

# Insert reusable methods before align.
start=s.index('    def align(self):')
end=s.index('    def found(self,pair,status):',start)
block='''    def _candidate_key(self):
        if not self.current_pair or not self.current_traces:
            return None
        return (tuple(self.current_pair),
                tuple(id(trace) for trace in self.current_traces),
                round(float(self.lf.value()),1),
                round(float(self.hf.value()),1))

    def _clear_candidate_buttons(self):
        self.active_candidate_index=None
        self._candidate_scope=None
        for i,button in enumerate(self.candidates):
            button.setEnabled(False)
            button.setChecked(False)
            button.setText(f"#{i+1}  --")
            button.setToolTip("Nhấn AUTO ALIGN để tính lại Top 3")

    def _display_candidates(self):
        for i,button in enumerate(self.candidates):
            if self.last_solve and i<len(self.last_solve):
                route=route_candidate(self.last_solve[i])
                polarity="Đảo pha" if route.invert_target else "Không đảo"
                button.setText(
                    f"#{i+1}  Trace {route.delay_trace} · {polarity}\\n"
                    f"Delay: {route.delay_ms:.2f} ms")
                button.setToolTip(
                    f"Phương án #{i+1}: Delay Trace {route.delay_trace} "
                    f"+{route.delay_ms:.2f} ms; {polarity}; "
                    f"giữ nguyên Trace {route.reference_trace}. "
                    f"Điểm tối ưu: {route.score_db:+.3f} dB. "
                    "Chọn để xem SUM Mag/Phase; không ghi DSP.")
                button.setEnabled(True)
            else:
                button.setEnabled(False)
                button.setText(f"#{i+1}  --")
            button.setChecked(self.active_candidate_index==i)

    def select_candidate(self,index):
        """Preview selected signed-solver route, not physical DSP action."""
        if (self.last_solve is None or self._candidate_scope is None or
            self._candidate_scope!=self._candidate_key() or
            not isinstance(index,int) or index<0 or
            index>=min(3,len(self.last_solve))):
            self._clear_candidate_buttons()
            return False
        route=route_candidate(self.last_solve[index])
        before_ref=self._reference_index()
        # Atomic, positive, physical target selection; no transient
        # recomputations while changing REF/delay/invert together.
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
        if before_ref!=route.reference_index:
            self._mag_offset_key=None
            self._mag_anchor_verified=False
        self.active_candidate_index=index
        self._display_candidates()
        self._update_delay_route_label()
        self.recalc()
        polarity="Đảo pha" if route.invert_target else "Không đảo"
        self.status.setText(
            f"XEM THỬ #{index+1}: Trace {route.delay_trace} · "
            f"Delay: {route.delay_ms:.2f} ms · {polarity}. "
            f"Giữ Trace {route.reference_trace}. "
            "Chưa áp dụng lên Smaart/DSP.")
        return True

    def align(self):
        if not self.current_traces:
            self._clear_candidate_buttons()
            self.status.setText("Cần đủ 2 Trace đã xác nhận.")
            return
        gen=self.controller.generation
        pair=self.controller.last_pair
        # Use ORIGINAL trace order for solver, never reference-swapped order.
        a,b=self.current_traces
        key=self._candidate_key()
        results=auto_align(a,b,lf=self.lf.value(),hf=self.hf.value(),
                           max_delay_ms=180)
        if not self.controller.is_current(gen,pair) or key!=self._candidate_key():
            self._clear_candidate_buttons()
            return
        self.last_solve=results
        self._candidate_scope=key
        self.active_candidate_index=None
        if not results:
            self._clear_candidate_buttons()
            self.status.setText("Không đủ Coherence trong vùng LF/HF.")
            return
        self._display_candidates()
        self.select_candidate(0)

'''
s=s[:start]+block+s[end:]

# ROI invalidates previously computed candidate options
needle='''            if self.last_solve is not None:
                self.last_solve=None
                for item in self.candidates:
                    item.setText("-")'''
assert s.count(needle)==1
s=s.replace(needle,'''            if self.last_solve is not None:
                self.last_solve=None
                self._clear_candidate_buttons()''')

# Resize engine view so Top-3 buttons remain fully reachable via scrollbar.
s=s.replace("self.setFixedSize(205,330)","self.setFixedSize(205,400)")
p.write_text(s,encoding="utf-8")

p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8")
assert 'self.page_heights={"phase":330,"eq":478,"fir":475}' in s
s=s.replace('self.page_heights={"phase":330,"eq":478,"fir":475}',
            'self.page_heights={"phase":400,"eq":478,"fir":475}')
p.write_text(s,encoding="utf-8")
print("V817_BIG_TRACE_AND_SELECTABLE_TOP3_PATCH_PASS")
