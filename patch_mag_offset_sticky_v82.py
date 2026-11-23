from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_2_DUAL_AXIS_FOLLOW_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
needle='''        self.current_sum=None
        self.last_solve=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.current_sum=None
        self.last_solve=None
        # The Mag preview offset is a display-only alignment, never a DSP gain.
        # Freeze it for a selected pair so viewport pan/Auto Align cannot
        # cause the drawn SUM to jump to a new display baseline.
        self._mag_offset_key=None''')
start=s.index('        self.graph_mag.display_offset_db=0.0\n        if self.mag_fit.isChecked():')
end=s.index('        if self.graph_mag.display_offset_db:',start)
replacement='''        mag_fit_key=(tuple(self.current_pair or self.current_sum.sources),
                     bool(self.mag_fit.isChecked()))
        if mag_fit_key!=self._mag_offset_key:
            self._mag_offset_key=mag_fit_key
            self.graph_mag.display_offset_db=0.0
            if self.mag_fit.isChecked():
                d=self.current_sum
                allowed=(d.hz>=20)&(d.hz<=20000)&np.isfinite(d.mag_db)
                mag=d.mag_db[allowed]
                if len(mag):
                    lo,hi=self.mag_min.value(),self.mag_max.value()
                    inside=np.mean((mag>=lo)&(mag<=hi))
                    if inside<.30:
                        self.graph_mag.display_offset_db=round(
                            (lo+hi)*.5-float(np.median(mag)),1)
'''
s=s[:start]+replacement+s[end:]
# update checkbox to avoid confusion
s=s.replace('self.mag_fit=QCheckBox("Auto-fit Mag preview (DISPLAY ONLY)")',
            'self.mag_fit=QCheckBox("Auto-fit Mag preview (DISPLAY ONLY)")')
needle='''        self.mag_fit.setChecked(True)
        self.mag_fit.stateChanged.connect(self.recalc)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.mag_fit.setChecked(True)
        self.mag_fit.setToolTip(
            "Chi chon display offset luc doi cap Trace/checkbox; "
            "khong thay doi offset khi keo truc Y hoac Auto Align.")
        self.mag_fit.stateChanged.connect(self.recalc)''')
p.write_text(s,encoding="utf-8")
print("V82_STICKY_DISPLAY_MAG_OFFSET_PATCHED")
