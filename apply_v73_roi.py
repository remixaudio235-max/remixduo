from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_3_ROI_QA')
p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
needle='from tf_display_smoothing import SMOOTH_OPTIONS'
assert s.count(needle)==1
s=s.replace(needle,needle+'\nfrom roi_markers_v73 import ROIMarker, hz_to_x, x_to_hz, bound_drag')
s=s.replace('RemiX Auto Align V7.2 - Windows QA','RemiX Auto Align V7.3 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.2','RemiX  AUTO ALIGN  V7.3')
needle='''        self.display_offset_db=0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)'''
assert needle in s
s=s.replace(needle,'''        self.display_offset_db=0.0
        self.lf_hz=60.0
        self.hf_hz=200.0
        self.roi_guides=True
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)''')
needle='''        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        base=QColor("#42f6ff") if self.kind=="mag" else QColor("#f48dff")'''
assert needle in s
s=s.replace(needle,'''        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        if self.roi_guides and self.f_min < self.lf_hz < self.hf_hz < self.f_max:
            xlf=hz_to_x(self.lf_hz,0,w,self.f_min,self.f_max)
            xhf=hz_to_x(self.hf_hz,0,w,self.f_min,self.f_max)
            # The ROI band is a subtle reference behind original SUM paths.
            painter.fillRect(QRectF(xlf,0,xhf-xlf,h),
                             QColor(25,155,171,18 if self.kind=="phase" else 10))
            for x,color in ((xlf,QColor("#42eab6")),(xhf,QColor("#ffaf54"))):
                painter.setPen(QPen(color,1.6,Qt.PenStyle.DashLine))
                painter.drawLine(int(x),0,int(x),h)
        base=QColor("#42f6ff") if self.kind=="mag" else QColor("#f48dff")''')
# Include 20k bound equal endpoint; explicit ROI is within plot.
s=s.replace('''self.f_min < self.lf_hz < self.hf_hz < self.f_max''',
            '''self.f_min <= self.lf_hz < self.hf_hz <= self.f_max''')
# Setup after existing widgets exist, no separate click-through surface beyond two tabs
needle='''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        saved_axes=read_saved_axes()'''
assert needle in s
s=s.replace(needle,'''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        self.roi_updating=False
        self.roi_markers={name:ROIMarker(name,self.on_roi_drag)
                          for name in ("LF","HF")}
        for widget in (self.lf,self.hf):
            widget.setDecimals(1)
            widget.setSingleStep(1.0)
            widget.valueChanged.connect(self.on_roi_changed)
        self._sync_roi_to_graphs()
        saved_axes=read_saved_axes()''')
# Add methods before update_y_ranges. Keep dirty results consistent.
needle='''    def update_y_ranges(self,*_):
        if not hasattr(self,"graph_mag"):return'''
assert needle in s
new='''    def _sync_roi_to_graphs(self):
        lf=float(self.lf.value());hf=float(self.hf.value())
        for graph in (self.graph_phase,self.graph_mag):
            graph.lf_hz=lf
            graph.hf_hz=hf
            graph.update()
        for marker in self.roi_markers.values():
            marker.set_frequency(lf if marker.kind=="LF" else hf)
        self._position_roi_markers()

    def on_roi_changed(self,*_):
        if self.roi_updating:
            return
        self.roi_updating=True
        try:
            lf=float(self.lf.value())
            hf=float(self.hf.value())
            if lf>=hf / (2**0.025):
                if self.sender() is self.lf:
                    self.lf.setValue(bound_drag("LF",lf,lf,hf))
                else:
                    self.hf.setValue(bound_drag("HF",hf,lf,hf))
            self._sync_roi_to_graphs()
            if self.last_solve is not None:
                self.last_solve=None
                for item in self.candidates:
                    item.setText("-")
                self.status.setText("ROI changed - nhan AUTO ALIGN de tinh lai")
        finally:
            self.roi_updating=False

    def on_roi_drag(self,kind,global_x):
        if not self.plot_layout:
            return
        x,y,w,h=self.plot_layout.phase
        frequency=x_to_hz(global_x,x,w)
        lf=float(self.lf.value())
        hf=float(self.hf.value())
        bounded=bound_drag(kind,frequency,lf,hf)
        widget=self.lf if kind=="LF" else self.hf
        if abs(widget.value()-bounded) >= 0.05:
            widget.setValue(round(bounded,1))
        print(f"V73_ROI_DRAG {kind} {widget.value():.1f} Hz",flush=True)

    def _position_roi_markers(self):
        if not hasattr(self,"roi_markers") or not self.plot_layout:
            return
        x,y,w,h=self.plot_layout.phase
        for name,marker in self.roi_markers.items():
            hz=self.lf.value() if name=="LF" else self.hf.value()
            mid=round(hz_to_x(hz,x,w))
            px=mid-marker.width()//2
            py=y+5
            if marker.pos().x()!=px or marker.pos().y()!=py:
                marker.move(px,py)

    def update_y_ranges(self,*_):
        if not hasattr(self,"graph_mag"):return'''
s=s.replace(needle,new)
# Place handles after each plot layout assignment; graph geometry is known.
needle='''        self.overlay_positioned=True
        self.refresh_visibility()

    def refresh_visibility(self,*_):'''
assert needle in s
s=s.replace(needle,'''        self.overlay_positioned=True
        self._position_roi_markers()
        self.refresh_visibility()

    def refresh_visibility(self,*_):''')
needle='''        for w,enabled in ((self.graph_mag,self.mag.isChecked()),(self.graph_phase,self.phase.isChecked())):
            w.setVisible(bool(has and enabled))

    def _target_is_foreground'''
assert needle in s
s=s.replace(needle,'''        for w,enabled in ((self.graph_mag,self.mag.isChecked()),(self.graph_phase,self.phase.isChecked())):
            w.setVisible(bool(has and enabled))
        for marker in self.roi_markers.values():
            marker.setVisible(bool(has and (self.phase.isChecked() or self.mag.isChecked())))

    def _target_is_foreground''')
# Close child-independent widgets when the main panel closes
needle='''    def _target_is_foreground(self,target_hwnd):'''
assert needle in s
s=s.replace(needle,'''    def closeEvent(self,event):
        for marker in self.roi_markers.values():
            marker.close()
        self.graph_mag.close()
        self.graph_phase.close()
        super().closeEvent(event)

    def _target_is_foreground(self,target_hwnd):''')
# Useful hint without new row, user understands handles
needle='''        layout.addWidget(self.pair_label)
        self.status=QLabel'''
assert needle in s
s=s.replace(needle,'''        layout.addWidget(self.pair_label)
        self.roi_hint=QLabel("LF/HF: Keo 2 moc tren do thi Phase de chon dai")
        self.roi_hint.setStyleSheet("color:#9bd8c9;font:11px 'Segoe UI'")
        layout.addWidget(self.roi_hint)
        self.status=QLabel''')
s=s.replace('self.setFixedSize(354,540)','self.setFixedSize(354,563)')
p.write_text(s,encoding='utf-8')
print("V73_ROI_PATCH_OK")
