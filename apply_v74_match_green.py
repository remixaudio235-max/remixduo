from pathlib import Path
root=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_4_MATCH_GREEN_QA')
p=root/'trf_core.py'
s=p.read_text(encoding='utf-8')
assert 'def phase_match_percent(' not in s
new='''

def phase_match_percent(a,b,delay_ms=0.0,invert_trace2=False,
                        lf=60.,hf=200.,coh_gate=.60,min_bins=12):
    """Coherence-weighted circular phase *agreement* in LF..HF.

    Score 100 means identical phase (0-degree difference); 0 means 180
    degrees apart. The metric is a model similarity percentage, NOT a
    probability or independently validated Smaart alignment score.
    Uses the same matched frequency bins as the complex SUM and solver,
    before any Mag/Phase display smoothing or display-only Mag offset.
    Returns (None, valid_bins) if too few trustworthy bins.
    """
    if not (20. <= float(lf) < float(hf) <= 20000.):
        return None, 0
    f,h1,h2,coh=matched(a,b)
    mask=((f>=float(lf)) & (f<=float(hf)) & (coh>=float(coh_gate))
          & np.isfinite(h1.real)&np.isfinite(h1.imag)
          & np.isfinite(h2.real)&np.isfinite(h2.imag)
          & (np.abs(h1)>1e-12) & (np.abs(h2)>1e-12))
    n=int(np.count_nonzero(mask))
    if n<int(min_bins):
        return None,n
    freqs=f[mask]
    shifted=h2[mask]*np.exp(-2j*np.pi*freqs*(float(delay_ms)/1000.))
    if invert_trace2:
        shifted=-shifted
    # Angle difference via normalized complex product (phase only).
    cross=h1[mask]*np.conj(shifted)
    cos_delta=np.clip(cross.real/np.maximum(np.abs(cross),1e-20),-1.,1.)
    weight=np.clip(coh[mask],0.,1.)**2
    denom=float(weight.sum())
    if not np.isfinite(denom) or denom<=1e-15:
        return None,n
    agreement=50. * (1.+float(np.dot(weight,cos_delta)/denom))
    return float(np.clip(agreement,0.,100.)),n
'''
# Insert before synthetic() so user's direct scripting imports work.
needle='\ndef synthetic(name,hz,db=0.,delay_ms=0.,invert=False):'
assert s.count(needle)==1
s=s.replace(needle,new+needle)
p.write_text(s,encoding='utf-8')

p=root/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
needle='from trf_core import synthetic,compute_sum,auto_align,read_trf,SumTrace'
assert s.count(needle)==1
s=s.replace(needle,'from trf_core import synthetic,compute_sum,auto_align,read_trf,SumTrace,phase_match_percent')
s=s.replace('RemiX Auto Align V7.3 - Windows QA','RemiX Auto Align V7.4 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.3','RemiX  AUTO ALIGN  V7.4')
needle='''        self.roi_guides=True
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.roi_guides=True
        self.phase_match_value=None
        self.phase_match_bins=0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)''')
needle='''        base=QColor("#42f6ff") if self.kind=="mag" else QColor("#f48dff")'''
assert s.count(needle)==1
s=s.replace(needle,'''        base=QColor("#39FF14") # Green neon SUM Mag and SUM Phase''')
needle='''            if quality=="low":color.setAlpha(90)
            painter.setPen(QPen(color,1.5 if quality=="low" else 2.1))
            painter.drawPath(paths[quality])
        painter.setPen(QColor("#f1b977") if self.display_offset_db else QColor(base))'''
assert s.count(needle)==1
s=s.replace(needle,'''            if quality=="low":color.setAlpha(100)
            painter.setPen(QPen(color,2.2 if quality=="low" else 3.5,
                                Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(paths[quality])
        painter.setPen(base)''')
needle='''        painter.drawText(80,19,f"SUM {self.kind.upper()} MODEL"+offset)
        painter.end()'''
assert s.count(needle)==1
s=s.replace(needle,'''        painter.drawText(80,19,f"SUM {self.kind.upper()} MODEL"+offset)
        # Floating phase agreement above the Phase SUM, strictly inside LF-HF.
        if (self.kind=="phase" and self.roi_guides and
                self.phase_match_value is not None and
                self.f_min <= self.lf_hz < self.hf_hz <= self.f_max):
            xlf=hz_to_x(self.lf_hz,0,w,self.f_min,self.f_max)
            xhf=hz_to_x(self.hf_hz,0,w,self.f_min,self.f_max)
            mid=(xlf+xhf)/2
            tag_w=165
            tag_x=max(3.,min(float(w)-tag_w-3.,mid-tag_w/2))
            rect=QRectF(tag_x,34.,tag_w,30.)
            painter.setPen(QPen(QColor("#39FF14"),1.4))
            painter.setBrush(QColor(9,22,12,228))
            painter.drawRoundedRect(rect,6,6)
            painter.setPen(QColor("#39FF14"))
            font=painter.font()
            font.setBold(True)
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,
                            f"PHASE MATCH {self.phase_match_value:.0f}%")
        painter.end()''')
needle='''        layout.addWidget(self.roi_hint)
        self.status=QLabel'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.addWidget(self.roi_hint)
        self.phase_match_label=QLabel("LF/HF PHASE MATCH: -- % (0 bins)")
        self.phase_match_label.setObjectName("phase_match")
        self.phase_match_label.setStyleSheet(
            "QLabel#phase_match{color:#39FF14;font:bold 15px 'Segoe UI';"
            "background:#112313;border:1px solid #2b7130;"
            "border-radius:6px;padding:6px}")
        layout.addWidget(self.phase_match_label)
        self.status=QLabel''')
s=s.replace('self.setFixedSize(354,563)','self.setFixedSize(354,605)')
needle='''        self.graph_phase.set_data(None);self.graph_mag.set_data(None)
        self.last_solve=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.graph_phase.set_data(None);self.graph_mag.set_data(None)
        self._clear_phase_match()
        self.last_solve=None''')
needle='''        self.graph_mag.set_data(self.current_sum)
        self.graph_phase.set_data(self.current_sum)
        self.refresh_visibility()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.graph_mag.set_data(self.current_sum)
        self.graph_phase.set_data(self.current_sum)
        self._update_phase_match()
        self.refresh_visibility()''')
needle='''    def _sync_roi_to_graphs(self):
        lf=float(self.lf.value());hf=float(self.hf.value())'''
assert s.count(needle)==1
methods='''    def _clear_phase_match(self):
        if hasattr(self,"phase_match_label"):
            self.phase_match_label.setText("LF/HF PHASE MATCH: -- % (0 bins)")
        if hasattr(self,"graph_phase"):
            self.graph_phase.phase_match_value=None
            self.graph_phase.phase_match_bins=0
            self.graph_phase.update()

    def _update_phase_match(self):
        if not getattr(self,"current_traces",None):
            self._clear_phase_match()
            return
        try:
            percentage,bins=phase_match_percent(
                self.current_traces[0],self.current_traces[1],
                delay_ms=self.delay.value(),
                invert_trace2=self.invert.isChecked(),
                lf=self.lf.value(),hf=self.hf.value(),coh_gate=.60)
        except (ValueError,FloatingPointError):
            percentage,bins=None,0
        self.graph_phase.phase_match_value=percentage
        self.graph_phase.phase_match_bins=bins
        if percentage is None:
            self.phase_match_label.setText(
                f"LF/HF PHASE MATCH: -- % ({bins} bins)")
        else:
            self.phase_match_label.setText(
                f"LF/HF PHASE MATCH: {percentage:.1f}% ({bins} bins)")
        self.graph_phase.update()

'''
s=s.replace(needle,methods+needle)
needle='''        self._position_roi_markers()

    def on_roi_changed(self,*_):'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._position_roi_markers()
        self._update_phase_match()

    def on_roi_changed(self,*_):''')
p.write_text(s,encoding='utf-8')
print("V74_PATCH_READY",root)
