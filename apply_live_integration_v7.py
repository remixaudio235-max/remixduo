from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
s=p.read_text(encoding="utf-8")
assert "self.observer=UIADataBarObserver(SMAART_TRF) if not demo else None" in s
s=s.replace("from win_databar_v7 import locate_smaart,UIADataBarObserver",
            "from win_databar_v7 import locate_smaart\nfrom live_sync_v7 import LiveDataBarV7\nfrom plot_geometry_v7 import locate_plots")
s=s.replace("    found=pyqtSignal(object,str)","    found=pyqtSignal(object,str)\n    layout_ready=pyqtSignal(object)")
s=s.replace("self.observer=UIADataBarObserver(SMAART_TRF) if not demo else None",
            """self.observer=LiveDataBarV7(SMAART_TRF) if not demo else None
        self.plot_layout=None
        self.plot_hwnd=None
        self.plot_future=None
        self.plot_requested=0.
        self.events.layout_ready.connect(self.on_plot_layout)""")
s=s.replace("self.setFixedSize(354,385)","self.setFixedSize(354,465)")
# Insert Y range input widgets after sum checkboxes
needle="showrow.addWidget(self.mag);showrow.addWidget(self.phase);layout.addLayout(showrow)"
assert needle in s
s=s.replace(needle,needle+'''
        # Chart axis Y ranges are not currently exposed as numbers by Smaart
        # UIA. Users can match current Smaart zoom without fake pixel parity.
        yrow=QGridLayout()
        self.mag_min=QDoubleSpinBox();self.mag_min.setRange(-150,150);self.mag_min.setValue(-80)
        self.mag_max=QDoubleSpinBox();self.mag_max.setRange(-150,150);self.mag_max.setValue(20)
        self.phase_min=QDoubleSpinBox();self.phase_min.setRange(-500,500);self.phase_min.setValue(-180)
        self.phase_max=QDoubleSpinBox();self.phase_max.setRange(-500,500);self.phase_max.setValue(180)
        for widget in (self.mag_min,self.mag_max,self.phase_min,self.phase_max):
            widget.setDecimals(0);widget.valueChanged.connect(self.update_y_ranges)
        yrow.addWidget(QLabel("Mag Y min/max"),0,0)
        yrow.addWidget(self.mag_min,0,1);yrow.addWidget(self.mag_max,0,2)
        yrow.addWidget(QLabel("Phase Y min/max"),1,0)
        yrow.addWidget(self.phase_min,1,1);yrow.addWidget(self.phase_max,1,2)
        layout.addLayout(yrow)
        self.update_y_ranges()''')
# invalid reference: self.graph_mag created AFTER yrow in code, so update_y_ranges called before graph creation.
# Instead move initial update to after graphs
s=s.replace("        self.update_y_ranges()\n        self.solve", "        self.solve")
s=s.replace('''        self.graph_phase=SumGraph("phase")
        self.overlay_positioned=False''',
            '''        self.graph_phase=SumGraph("phase")
        self.update_y_ranges()
        self.overlay_positioned=False''')
# insert handler before refresh_visibility
needle="    def refresh_visibility(self,*_):"
assert needle in s
s=s.replace(needle,'''    def update_y_ranges(self,*_):
        if not hasattr(self,"graph_mag"):return
        if self.mag_max.value()>self.mag_min.value():
            self.graph_mag.y_min=self.mag_min.value()
            self.graph_mag.y_max=self.mag_max.value()
        if self.phase_max.value()>self.phase_min.value():
            self.graph_phase.y_min=self.phase_min.value()
            self.graph_phase.y_max=self.phase_max.value()
        self.graph_mag.update();self.graph_phase.update()

    def on_plot_layout(self,payload):
        if payload is None:
            self.plot_layout=None
            self.overlay_positioned=False
            self.refresh_visibility()
            return
        hwnd,layout=payload
        self.plot_hwnd=hwnd
        self.plot_layout=layout
        self._apply_plot_layout()

    def _apply_plot_layout(self):
        if self.plot_layout is None:return
        for widget,rect in ((self.graph_phase,self.plot_layout.phase),
                            (self.graph_mag,self.plot_layout.mag)):
            if widget.geometry().getRect()!=rect:
                widget.setGeometry(*rect)
        self.overlay_positioned=True
        self.refresh_visibility()

'''+needle)
start=s.index('''        l,t,r,b=target.rect
        w,h=r-l,b-t
        # 9.6.4 reference layout''')
end=s.index('''        now=time.monotonic()
        if target.foreground''',start)
s=s[:start]+'''        l,t,r,b=target.rect
        if self.plot_hwnd==target.hwnd and self.plot_layout is not None:
            self._apply_plot_layout()
        else:
            self.overlay_positioned=False
            self.refresh_visibility()
        if self.isVisible() and self.geometry().x()!=r-365:self.move(r-365,t+100)
        now=time.monotonic()
        if now-self.plot_requested>2.0 and (
            self.plot_future is None or self.plot_future.done()):
            self.plot_requested=now
            hwnd=target.hwnd
            self.plot_future=self.pool.submit(locate_plots,hwnd)
            self.plot_future.add_done_callback(
                lambda task,h=hwnd:self.events.layout_ready.emit((h,task.result()))
                if not task.exception() and task.result() is not None
                else self.events.layout_ready.emit(None))
''' + s[end:]
s=s.replace('''            self.poll_future=self.pool.submit(self.observer.poll)
            self.poll_future.add_done_callback(
                 lambda task:self.events.found.emit(*task.result()) if not task.exception() else
                 self.events.found.emit(None,"Tick observer error"))''',
'''            self.poll_future=self.pool.submit(self.observer.poll,target.hwnd)
            self.poll_future.add_done_callback(
                lambda task:self.events.found.emit(task.result().pair,task.result().status)
                if not task.exception() else self.events.found.emit(None,
                     "Smaart Data Bar scan error: "+str(task.exception())[:100]))''')
# Note when Smaart closes and reopens old plot_hwnd may not reset; invalidate on hide
s=s.replace('''            self.overlay_positioned=False;self.refresh_visibility()
            if self.isVisible():self.hide()
            return
        if not self.isVisible():self.show()''',
'''            self.overlay_positioned=False;self.refresh_visibility()
            self.plot_hwnd=None;self.plot_layout=None
            if self.isVisible():self.hide()
            return
        if not self.isVisible():self.show()''')
# clip lines outside axes, not artificially flatten at plot boundary
s=s.replace('''            yy=max(-1,min(h+1,yy))
            if previous is None or''','''            if yy<0 or yy>h:
                previous=None
                continue
            if previous is None or''')
p.write_text(s,encoding="utf-8")
print("V7_LIVE_UI_INTEGRATION_PATCH_PASS",len(s.splitlines()))
