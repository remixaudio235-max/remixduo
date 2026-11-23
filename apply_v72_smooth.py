from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_2_SMOOTH_QA')
p=base/'trf_core.py'
s=p.read_text(encoding='utf-8')
anchor='import numpy as np'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\nfrom tf_display_smoothing import smooth_log_octaves, smooth_phase_unit_phasor')
old='''    sources:tuple[str,str]

def read_trf'''
assert old in s
s=s.replace(old,'''    sources:tuple[str,str]
    phase_valid:np.ndarray|None=None
    phase_concentration:np.ndarray|None=None

def read_trf''')
old='''    if mag_oct:mag=_octave_smooth(f,mag,mag_oct)
    if phase_oct:deg=_octave_smooth(f,deg,phase_oct,True)
    mask=(coh>=coh_gate)&np.isfinite(mag)&np.isfinite(deg)
    return SumTrace(f,mag,deg,coh,mask,float(delay_ms),bool(invert_trace2),
                    (a.path.name,b.path.name))'''
assert old in s
new='''    # Smooth only display series; AutoAlign solver and original H stay raw.
    if mag_oct:
        mag=smooth_log_octaves(f,mag,mag_oct)
    deg,phase_valid,concentration=smooth_phase_unit_phasor(
        f,h,coh,phase_oct,coh_gate=coh_gate)
    mask=(coh>=coh_gate)&np.isfinite(mag)&np.isfinite(deg)
    return SumTrace(f,mag,deg,coh,mask,float(delay_ms),bool(invert_trace2),
                    (a.path.name,b.path.name),phase_valid,concentration)'''
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')

p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('''    QCheckBox,QDoubleSpinBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame)''',
'''    QCheckBox,QDoubleSpinBox,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame)''')
assert 'QComboBox' in s
s=s.replace('from smaart_axes_v71 import read_saved_axes',
            'from smaart_axes_v71 import read_saved_axes\nfrom tf_display_smoothing import SMOOTH_OPTIONS')
old='''        vals=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        paths={"high":QPainterPath(),"low":QPainterPath()}
        last_type=None
        previous=None'''
assert old in s
s=s.replace(old,'''        vals=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        if self.kind=="phase" and self.y_max-self.y_min >= 350:
            # Plot wrapped phase in the graph's selected 360 degree Y window.
            vals=(vals-self.y_min)%360.0+self.y_min
        phase_mask=getattr(d,"phase_valid",None)
        if phase_mask is None:phase_mask=d.valid
        paths={"high":QPainterPath(),"low":QPainterPath()}
        last_type=None
        previous=None
        previous_x=None''')
old='''        for f,y,good in zip(d.hz,vals,d.valid):
            if not(self.f_min<=f<=self.f_max) or not np.isfinite(y):
                last_type=None;previous=None;continue
            quality="high" if good else "low"
            if self.kind=="phase" and quality=="low":
                last_type=None;previous=None;continue'''
assert old in s
s=s.replace(old,'''        for i,(f,y,good) in enumerate(zip(d.hz,vals,d.valid)):
            if not(self.f_min<=f<=self.f_max) or not np.isfinite(y):
                last_type=None;previous=None;previous_x=None;continue
            if self.kind=="phase" and not phase_mask[i]:
                last_type=None;previous=None;previous_x=None;continue
            quality="high" if good else "low"
            if self.kind=="phase" and quality=="low":
                last_type=None;previous=None;previous_x=None;continue''')
old='''            if not np.isfinite(xx+yy) or not 0<=yy<=h:
                last_type=None;previous=None;continue
            path=paths[quality]
            if (quality!=last_type or previous is None or
                (self.kind=="phase" and abs(y-previous)>170)):
                path.moveTo(xx,yy)
                segments+=1
            else:
                path.lineTo(xx,yy)
            last_type=quality;previous=y'''
assert old in s
s=s.replace(old,'''            if not np.isfinite(xx+yy) or not 0<=yy<=h:
                last_type=None;previous=None;previous_x=None;continue
            path=paths[quality]
            abrupt=self.kind=="phase" and previous is not None and abs(y-previous)>120
            gap=self.kind=="phase" and previous_x is not None and abs(xx-previous_x)>23
            if quality!=last_type or previous is None or abrupt or gap:
                path.moveTo(xx,yy)
                segments+=1
            else:
                path.lineTo(xx,yy)
            last_type=quality;previous=y;previous_x=xx''')
s=s.replace('''self.setWindowTitle("RemiX Auto Align V7.1 - Windows QA")''',
'''self.setWindowTitle("RemiX Auto Align V7.2 - Windows QA")''')
s=s.replace('''title=QLabel("RemiX  AUTO ALIGN  V7.1",self)''',
'''title=QLabel("RemiX  AUTO ALIGN  V7.2",self)''')
s=s.replace('self.setFixedSize(354,500)','self.setFixedSize(354,540)')
anchor='''        layout.addLayout(yrow)
        self.mag_fit=QCheckBox'''
assert anchor in s
s=s.replace(anchor,'''        layout.addLayout(yrow)
        smoothrow=QHBoxLayout()
        self.mag_smooth=QComboBox()
        self.phase_smooth=QComboBox()
        for name,value in SMOOTH_OPTIONS:
            self.mag_smooth.addItem(name,value)
            self.phase_smooth.addItem(name,value)
        # 1/6 Oct is visible as Smaart Mag setting in GUI screenshot;
        # smoothingId 5 is not independently validated as that fraction.
        self.mag_smooth.setCurrentIndex(4)
        self.phase_smooth.setCurrentIndex(4)
        for control in (self.mag_smooth,self.phase_smooth):
            control.currentIndexChanged.connect(self.recalc)
        smoothrow.addWidget(QLabel("Mag Smooth"))
        smoothrow.addWidget(self.mag_smooth)
        smoothrow.addWidget(QLabel("Phase Smooth"))
        smoothrow.addWidget(self.phase_smooth)
        layout.addLayout(smoothrow)
        self.mag_fit=QCheckBox''')
old='''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),coh_gate=.60)'''
assert old in s
s=s.replace(old,'''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),
             coh_gate=.60,
             mag_oct=float(self.mag_smooth.currentData() or 0),
             phase_oct=float(self.phase_smooth.currentData() or 0))''')
p.write_text(s,encoding='utf-8')
print('V72_PATCH_PASS',base)
