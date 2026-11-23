from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_1_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert 'smaart_axes_v71' not in s
s=s.replace('from plot_geometry_v7 import locate_plots',
            'from plot_geometry_v7 import locate_plots\nfrom smaart_axes_v71 import read_saved_axes')
s=s.replace('        self.draw_count=0',
            '        self.draw_count=0\n        self.display_offset_db=0.0')
a=s.index('    def paintEvent(self,event):')
b=s.index('class QAHost(',a)
paint='''    def paintEvent(self,event):
        self.draw_count+=1
        if self.data is None:return
        d=self.data
        w,h=self.width(),self.height()
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        base=QColor("#42f6ff") if self.kind=="mag" else QColor("#f48dff")
        vals=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        paths={"high":QPainterPath(),"low":QPainterPath()}
        last_type=None
        previous=None
        count={"high":0,"low":0}
        segments=0
        denom=np.log(self.f_max/self.f_min)
        for f,y,good in zip(d.hz,vals,d.valid):
            if not(self.f_min<=f<=self.f_max) or not np.isfinite(y):
                last_type=None;previous=None;continue
            quality="high" if good else "low"
            if self.kind=="phase" and quality=="low":
                last_type=None;previous=None;continue
            xx=float((np.log(f/self.f_min)/denom)*w)
            yy=float((self.y_max-y)/(self.y_max-self.y_min)*h)
            if not np.isfinite(xx+yy) or not 0<=yy<=h:
                last_type=None;previous=None;continue
            path=paths[quality]
            if (quality!=last_type or previous is None or
                (self.kind=="phase" and abs(y-previous)>170)):
                path.moveTo(xx,yy)
                segments+=1
            else:
                path.lineTo(xx,yy)
            last_type=quality;previous=y
            count[quality]+=1
        self._last_points=sum(count.values())
        self._last_segments=segments
        self._last_low_coh=count["low"]
        for quality in ("low","high"):
            color=QColor(base)
            if quality=="low":color.setAlpha(90)
            painter.setPen(QPen(color,1.5 if quality=="low" else 2.1))
            painter.drawPath(paths[quality])
        painter.setPen(QColor("#f1b977") if self.display_offset_db else QColor(base))
        painter.setOpacity(.95)
        painter.setFont(self.font())
        offset=(f" | DISPLAY {self.display_offset_db:+.1f} dB"
                if self.kind=="mag" and self.display_offset_db else "")
        painter.drawText(80,19,f"SUM {self.kind.upper()} MODEL"+offset)
        painter.end()

'''
s=s[:a]+paint+s[b:]
s=s.replace('self.setFixedSize(354,465)','self.setFixedSize(354,500)')
needle='        layout.addLayout(yrow)\n        self.solve=QPushButton'
assert needle in s
s=s.replace(needle,'''        layout.addLayout(yrow)
        self.mag_fit=QCheckBox("Auto-fit Mag preview (DISPLAY ONLY)")
        self.mag_fit.setChecked(True)
        self.mag_fit.stateChanged.connect(self.recalc)
        layout.addWidget(self.mag_fit)
        self.solve=QPushButton''')
needle='''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        self.update_y_ranges()'''
assert needle in s
s=s.replace(needle,'''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        saved_axes=read_saved_axes()
        if saved_axes:
            for box,val in ((self.mag_min,saved_axes["mag"][0]),
                            (self.mag_max,saved_axes["mag"][1]),
                            (self.phase_min,saved_axes["phase"][0]),
                            (self.phase_max,saved_axes["phase"][1])):
                box.setValue(val)
            self.axis_note.setText("Axes from saved SmaartConfig.xml")
        else:
            self.axis_note.setText("Smaart Y axes unknown - check before comparing")
        self.update_y_ranges()''')
needle='''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),coh_gate=.60)
        self.graph_mag.set_data(self.current_sum)'''
assert needle in s
s=s.replace(needle,'''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),coh_gate=.60)
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
        if self.graph_mag.display_offset_db:
            self.axis_note.setText(
                f"Preview offset {self.graph_mag.display_offset_db:+.1f} dB "
                "(DISPLAY ONLY, no DSP gain)")
        self.graph_mag.set_data(self.current_sum)''')
needle='''        self.graph_mag.update();self.graph_phase.update()

    def on_plot_layout'''
assert needle in s
s=s.replace(needle,'''        if self.current_traces:self.recalc()
        else:self.graph_mag.update();self.graph_phase.update()

    def on_plot_layout''')
p.write_text(s,encoding='utf-8')
print('V71_OVERLAY_PATCH_PASS')
