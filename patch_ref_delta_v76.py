from pathlib import Path
root=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_6_REF_DELTA_QA')
p=root/'trf_core.py'
s=p.read_text(encoding='utf-8')
assert 'def sum_ref_phase_delta(' not in s
anchor='\ndef synthetic(name,hz,db=0.,delay_ms=0.,invert=False):'
assert s.count(anchor)==1
new='''

def sum_ref_phase_delta(ref,other,delay_ms=0.,invert_other=False,
                        lf=60.,hf=200.,coh_gate=.60,min_bins=12):
    """Circular |Phase(SUM)-Phase(REF)| on *raw* complex TF in LF/HF.

    ref is NEVER delayed/inverted. Only other is corrected with signed
    relative shift. The returned mean absolute circular difference is
    coherence-squared-weighted. P95 is an unweighted percentile of
    the same valid bins, in degrees. Values are model estimates, not
    Smaart internal phase renderer parity.
    """
    if not(20.<=float(lf)<float(hf)<=20000.):
        return None,None,0
    f,h_ref,h_other,coh=matched(ref,other)
    roi=((f>=lf)&(f<=hf)&(coh>=coh_gate)
         & np.isfinite(h_ref.real)&np.isfinite(h_ref.imag)
         & np.isfinite(h_other.real)&np.isfinite(h_other.imag)
         & (np.abs(h_ref)>1e-12)&(np.abs(h_other)>1e-12))
    h_corrected=h_other*np.exp(-2j*np.pi*f*float(delay_ms)/1000.)
    if invert_other:
        h_corrected=-h_corrected
    h_sum=h_ref+h_corrected
    # Suppress cancellation notches whose SUM phase is effectively undefined.
    roi &= (np.abs(h_sum) >
            1e-6*(np.abs(h_ref)+np.abs(h_corrected)))
    count=int(roi.sum())
    if count<int(min_bins):
        return None,None,count
    delta=np.rad2deg(np.angle(h_sum[roi]*np.conj(h_ref[roi])))
    weights=np.square(np.clip(coh[roi],0.,1.))
    if float(weights.sum())<=1e-15:
        return None,None,count
    mean=float(np.average(np.abs(delta),weights=weights))
    p95=float(np.percentile(np.abs(delta),95))
    return mean,p95,count
'''
s=s.replace(anchor,new+anchor)
p.write_text(s,encoding='utf-8')

p=root/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('from trf_core import synthetic,compute_sum,auto_align,read_trf,SumTrace,phase_match_percent',
            'from trf_core import synthetic,compute_sum,auto_align,read_trf,SumTrace,phase_match_percent,sum_ref_phase_delta')
assert 'sum_ref_phase_delta' in s
s=s.replace('RemiX Auto Align V7.5 - Windows QA','RemiX Auto Align V7.6 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.5','RemiX  AUTO ALIGN  V7.6')
s=s.replace('self.setFixedSize(354,605)','self.setFixedSize(354,666)')
needle='''        layout.addWidget(self.pair_label)
        self.roi_hint=QLabel'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.addWidget(self.pair_label)
        refrow=QHBoxLayout()
        ref_caption=QLabel("REF CỐ ĐỊNH:")
        ref_caption.setStyleSheet("color:#c4f1e5;font:bold 12px 'Segoe UI'")
        self.ref_choice=QComboBox()
        self.ref_choice.addItem("TRACE 1",0)
        self.ref_choice.addItem("TRACE 2",1)
        self.ref_choice.setToolTip(
            "Trace được giữ nguyên pha. Delay/INV chỉ áp dụng lên Trace còn lại.")
        self.ref_choice.currentIndexChanged.connect(self.on_ref_changed)
        refrow.addWidget(ref_caption)
        refrow.addWidget(self.ref_choice)
        layout.addLayout(refrow)
        self.correction_target_label=QLabel("BÙ TƯƠNG ĐỐI TRÊN TRACE 2")
        self.correction_target_label.setStyleSheet("color:#f1b977;font:11px 'Segoe UI'")
        layout.addWidget(self.correction_target_label)
        self.roi_hint=QLabel''')
needle='''        layout.addWidget(self.phase_match_label)
        self.status=QLabel'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.addWidget(self.phase_match_label)
        self.sum_ref_label=QLabel("Δ SUM–REF: -- °  |  P95: -- °")
        self.sum_ref_label.setObjectName("delta_sum_ref")
        self.sum_ref_label.setStyleSheet(
            "QLabel#delta_sum_ref{color:#aee9c3;font:bold 13px 'Segoe UI';"
            "background:#112016;border:1px solid #376b4a;"
            "border-radius:6px;padding:5px}")
        self.sum_ref_label.setToolTip(
            "Sai lệch tuyệt đối trung bình của pha SUM so với REF không delay, "
            "có trọng số coherence² trong vùng LF-HF; P95 của độ lệch pha.")
        layout.addWidget(self.sum_ref_label)
        self.status=QLabel''')
needle='''        self.delay.setSingleStep(.1);self.delay.setSuffix(" ms");self.delay.valueChanged.connect(self.recalc)
        self.invert=QCheckBox("\\u0110\\u1ea3o Trace 2");self.invert.stateChanged.connect(self.recalc)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.delay.setSingleStep(.1);self.delay.setSuffix(" ms");self.delay.valueChanged.connect(self.recalc)
        self.invert=QCheckBox("Đảo Trace 2");self.invert.stateChanged.connect(self.recalc)''')
needle='''        self._clear_phase_match()
        self.last_solve=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._clear_phase_match()
        self.last_solve=None''')
# Add proper fixed-ref helpers before recalc
needle='''    def recalc(self,*_):
        if not self.current_traces:return'''
assert s.count(needle)==1
s=s.replace(needle,'''    def _reference_index(self):
        return int(self.ref_choice.currentData() or 0)

    def _ordered_traces(self):
        if not self.current_traces:
            return None
        a,b=self.current_traces
        return (a,b) if self._reference_index()==0 else (b,a)

    def on_ref_changed(self,*_):
        # Equivalent relative reference frame:
        #   REF1=A, B shifted by +D  ->  REF2=B, A shifted by -D.
        # Both source files and Smaart originals remain untouched.
        new_ref=self._reference_index()+1
        other_num=2 if new_ref==1 else 1
        self.delay.blockSignals(True)
        self.delay.setValue(-self.delay.value())
        self.delay.blockSignals(False)
        self.invert.setText(f"Đảo Trace {other_num}")
        self.correction_target_label.setText(
            f"REF TRACE {new_ref} GIỮ NGUYÊN • BÙ TƯƠNG ĐỐI TRACE {other_num}")
        self.last_solve=None
        if hasattr(self,"candidates"):
            for label in self.candidates:label.setText("-")
        if self.current_traces:
            self.recalc()
            self.status.setText(
                f"REF TRACE {new_ref} cố định; Delay đổi dấu. "
                "Nhấn AUTO ALIGN để tối ưu lại.")
        else:
            self._clear_phase_match()

    def recalc(self,*_):
        if not self.current_traces:return''')
# With physically ordered ref & movable correct, smooth, mag, coherence etc.
needle='''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.current_sum=compute_sum(*self._ordered_traces(),
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),''')
needle='''        a,b=self.current_traces
        results=auto_align(a,b,lf=self.lf.value(),hf=self.hf.value(),max_delay_ms=180)'''
assert s.count(needle)==1
s=s.replace(needle,'''        a,b=self._ordered_traces()
        results=auto_align(a,b,lf=self.lf.value(),hf=self.hf.value(),max_delay_ms=180)''')
needle='''        best=results[0]
        self.delay.setValue(best.delay_ms)
        self.invert.setChecked(best.invert_trace2)
        self.status.setText("Delay "+("Trace 2" if best.delay_ms>=0 else "Trace 1")+
                 f" {abs(best.delay_ms):.2f}ms | "+("INV" if best.invert_trace2 else "NORMAL"))'''
assert s.count(needle)==1
s=s.replace(needle,'''        best=results[0]
        # Apply the solved signed relative shift only to the non-REF Trace.
        self.delay.blockSignals(True)
        self.invert.blockSignals(True)
        self.delay.setValue(best.delay_ms)
        self.invert.setChecked(best.invert_trace2)
        self.delay.blockSignals(False)
        self.invert.blockSignals(False)
        ref_num=self._reference_index()+1
        target_num=2 if ref_num==1 else 1
        self.status.setText(
            f"REF {ref_num} cố định | Shift TRACE {target_num}: "
            f"{best.delay_ms:+.2f} ms | "+
            ("INV" if best.invert_trace2 else "NORMAL")+
            (" | SHIFT ÂM (không phải delay DSP trực tiếp)"
             if best.delay_ms<0 else ""))''')
needle='''                label.setText(f"#{i+1} {'T2' if c.delay_ms>=0 else 'T1'} {abs(c.delay_ms):.2f}ms | "+
                     ("INV" if c.invert_trace2 else "NOR")+f" | {c.score_db:.2f}dB")'''
assert s.count(needle)==1
s=s.replace(needle,'''                label.setText(
                    f"#{i+1} SHIFT T{target_num} {c.delay_ms:+.2f}ms | "+
                    ("INV" if c.invert_trace2 else "NOR")+
                    f" | {c.score_db:.2f}dB")''')
needle='''        if hasattr(self,"phase_match_label"):
            self.phase_match_label.setText("LF/HF PHASE MATCH: -- % (0 bins)")'''
assert s.count(needle)==1
s=s.replace(needle,'''        if hasattr(self,"phase_match_label"):
            self.phase_match_label.setText("LF/HF PHASE MATCH: -- % (0 bins)")
        if hasattr(self,"sum_ref_label"):
            self.sum_ref_label.setText("Δ SUM–REF: -- °  |  P95: -- °")''')
needle='''            percentage,bins=phase_match_percent(
                self.current_traces[0],self.current_traces[1],'''
assert s.count(needle)==1
s=s.replace(needle,'''            percentage,bins=phase_match_percent(
                *self._ordered_traces(),''')
needle='''        self.graph_phase.phase_match_value=percentage
        self.graph_phase.phase_match_bins=bins'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.graph_phase.phase_match_value=percentage
        self.graph_phase.phase_match_bins=bins
        try:
            delta,p95,delta_bins=sum_ref_phase_delta(
                *self._ordered_traces(),
                delay_ms=self.delay.value(),
                invert_other=self.invert.isChecked(),
                lf=self.lf.value(),hf=self.hf.value(),coh_gate=.60)
        except (ValueError,FloatingPointError):
            delta,p95,delta_bins=None,None,0
        if delta is None:
            self.sum_ref_label.setText(
                f"Δ SUM–REF: -- ° | P95: -- ° ({delta_bins} bins)")
        else:
            self.sum_ref_label.setText(
                f"Δ SUM–REF: {delta:.2f}° | P95: {p95:.2f}°")''')
p.write_text(s,encoding='utf-8')
print('V76_PATCH_OK',root)
