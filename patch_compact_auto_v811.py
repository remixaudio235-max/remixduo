from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_11_AUTO_SMOOTH_COMPACT_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert s.count('from tf_display_smoothing import SMOOTH_OPTIONS')==1
s=s.replace('from tf_display_smoothing import SMOOTH_OPTIONS',
            'from tf_display_smoothing import SMOOTH_OPTIONS\nfrom smaart_smooth_sync_v811 import read_saved_smooth')
s=s.replace('RemiX Signal V8.10','RemiX Signal V8.11')
s=s.replace('SMAART � V8.10','SMAART · V8.11')
assert 'self.setFixedSize(205,550)' in s
s=s.replace('self.setFixedSize(205,550)','self.setFixedSize(205,463)')
needle='''        displaycol.addStretch(1)
        self.tabs.addTab(display_page,"Hiện")

        axis_page=QWidget()'''
if needle not in s:
    idx=s.index('        displaycol.addStretch(1)')
    print('CHECK_SOURCE',repr(s[idx:idx+122]))
    raise RuntimeError('display tab anchor unknown')
s=s.replace(needle,'''        displaycol.addStretch(1)
        # V8.11: no display tab. Retain the hidden QObjects for existing
        # solver, visibility and smoothing code paths, but disable the
        # entire display control page and all user-initiated toggles.
        display_page.hide()

        axis_page=QWidget()''')
needle='''        self.diag_layout.addWidget(self.notes)
        self.axis_note=QLabel('''
assert s.count(needle)==1
s=s.replace(needle,'''        self.diag_layout.addWidget(self.notes)
        self.smooth_status=QLabel("Smooth: đang đọc cấu hình Smaart")
        self.smooth_status.setObjectName("diagnostic")
        self.smooth_status.setWordWrap(True)
        self.diag_layout.addWidget(self.smooth_status)
        self.axis_note=QLabel(''')
needle='''        self.timer.timeout.connect(self.tick)
        self.timer.start(33)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._last_smooth_poll=0.0
        self._last_smooth_ns=-1
        self._smooth_snapshot=None
        self._refresh_saved_smoothing(force=True)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)''')
anchor='''    def recalc(self,*_):'''
assert s.count(anchor)==1
functions='''    def _refresh_saved_smoothing(self,force=False):
        """Watch SmaartConfig.xml at 1.5s intervals; never touch Smaart."""
        now=time.monotonic()
        if not force and now-self._last_smooth_poll<1.5:return
        self._last_smooth_poll=now
        # Parse only if stat changed. This is a saved-config sync,
        # NOT an unsupported claim of instant live Smaart GUI parity.
        try:
            from smaart_smooth_sync_v811 import CONFIG
            stamp=CONFIG.stat().st_mtime_ns
        except OSError:
            stamp=-1
        if not force and stamp==self._last_smooth_ns:return
        self._last_smooth_ns=stamp
        snap=read_saved_smooth()
        if snap is None:
            self.smooth_status.setText(
                "Smooth: cấu hình chưa đọc được · giữ giá trị đã xác nhận")
            return
        old=self._smooth_snapshot
        self._smooth_snapshot=snap
        combo_changes=False
        for box,value in ((self.mag_smooth,snap.mag_oct),
                          (self.phase_smooth,snap.phase_oct)):
            ix=box.findData(value)
            if ix<0:continue
            if box.currentIndex()!=ix:
                box.blockSignals(True)
                box.setCurrentIndex(ix)
                box.blockSignals(False)
                combo_changes=True
        if snap.mag_verified and snap.phase_verified:
            tag="đã xác nhận 1/6 Oct"
        else:
            tag="ID khác 5: ánh xạ dự kiến, chưa xác nhận GUI"
        self.smooth_status.setText(
            f"Smooth từ Smaart đã lưu: MAG ID {snap.mag_id}, "
            f"PHASE ID {snap.phase_id} ({tag}). "
            "Không phản ánh thay đổi chưa lưu trong Smaart.")
        if combo_changes and self.current_traces:
            self.recalc()

    def _enforce_display_always_on(self):
        for checkbox in (self.mag,self.phase,self.mag_fit):
            if not checkbox.isChecked():
                checkbox.blockSignals(True)
                checkbox.setChecked(True)
                checkbox.blockSignals(False)

'''
s=s.replace(anchor,functions+anchor)
needle='''    def recalc(self,*_):
        if not self.current_traces:return'''
assert s.count(needle)==1
s=s.replace(needle,'''    def recalc(self,*_):
        self._enforce_display_always_on()
        if not self.current_traces:return''')
needle='''    def refresh_visibility(self,*_):
        has=self.current_sum is not None and self.overlay_positioned
        for w,enabled in ((self.graph_mag,self.mag.isChecked()),(self.graph_phase,self.phase.isChecked())):
            w.setVisible(bool(has and enabled))
        for marker in self.roi_markers.values():
            marker.setVisible(bool(has and (self.phase.isChecked() or self.mag.isChecked())))'''
assert s.count(needle)==1
s=s.replace(needle,'''    def refresh_visibility(self,*_):
        self._enforce_display_always_on()
        has=self.current_sum is not None and self.overlay_positioned
        self.graph_mag.setVisible(bool(has))
        self.graph_phase.setVisible(bool(has))
        for marker in self.roi_markers.values():
            marker.setVisible(bool(has))''')
needle='''    def tick(self):
        if self.demo:'''
assert s.count(needle)==1
s=s.replace(needle,'''    def tick(self):
        self._refresh_saved_smoothing()
        if self.demo:''')
p.write_text(s,encoding='utf-8')
print('V811_PATCH_OK',len(s),'two tabs and saved smooth sync')
