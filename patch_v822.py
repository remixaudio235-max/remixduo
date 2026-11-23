from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_22_VISIBILITY_LIVE_QA")

p=root/"dock_geometry_v815.py"
s=p.read_text(encoding="utf8")
assert s.count("panel_h=min(385,available_h)")==1
s=s.replace("panel_h=min(385,available_h)","panel_h=min(560,available_h)")
p.write_text(s,encoding="utf8")

p=root/"overlay_v7.py"
s=p.read_text(encoding="utf8")
needle='''        self.ui_tool_enabled=True'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        # V8.22: authoritative model-overlay visibility state;
        # false means native Smaart Tuning Live with NO RemiX overlays.
        self.overlay_workspace_visible=True
        self.overlay_tool_mode="phase"''')
start=s.index('    def refresh_visibility(self,*_):')
end=s.index('    def closeEvent(self,event):',start)
old=s[start:end]
assert 'eq_active=' in old and 'self.graph_mag.setVisible' in old
new='''    def refresh_visibility(self,*_):
        self._enforce_display_always_on()
        workspace=bool(getattr(self,"overlay_workspace_visible",True))
        mode=getattr(self,"overlay_tool_mode","phase")
        phase_active=(workspace and mode=="phase" and
                      (not self.managed_mode or self.ui_tool_enabled))
        has=(self.current_sum is not None and self.overlay_positioned
             and phase_active)
        eq_active=(workspace and self.managed_mode and mode=="eq"
                   and not self.ui_tool_enabled and
                   self.graph_mag.mageq_source is not None and
                   self.graph_mag.mageq_frame is not None)
        # STRICT single-owner overlay lifecycle:
        # Phase: SUM Phase + SUM Mag + LF/HF
        # EQ: MagEQ only, if computed
        # FIR / LIVE / HIDE: native Smaart only, no RemiX overlays.
        self.graph_mag.setVisible(bool(has or eq_active))
        self.graph_phase.setVisible(bool(has))
        for marker in self.roi_markers.values():
            marker.setVisible(bool(has))
        for grip in self.roi_line_grips.values():
            grip.setVisible(bool(has))

'''
s=s[:start]+new+s[end:]
s=s.replace("V8.21","V8.22")
p.write_text(s,encoding="utf8")

p=root/"native_eq_mag_v06.py"
s=p.read_text(encoding="utf8")
needle='''                self.enabled and self.hub.active=="eq" and
                self.hub.isVisible())'''
assert s.count(needle)==1
s=s.replace(needle,'''                self.enabled and self.hub.active=="eq" and
                self.hub.isVisible() and self.hub.workspace_visible)''')
needle='''                self.hub.active!="eq" or not self.hub.isVisible()):'''
assert s.count(needle)==1
s=s.replace(needle,'''                self.hub.active!="eq" or not self.hub.isVisible()
                or not self.hub.workspace_visible):''')
p.write_text(s,encoding="utf8")

p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
needle='''        outer.addWidget(self.heading)
        self.scroll=QScrollArea()'''
assert s.count(needle)==1
s=s.replace(needle,'''        # Dock title with a deliberate native-view escape hatch.
        # "AUTO" controls whether the companion hides when Smaart loses
        # foreground. "LIVE" returns the original Smaart plot instantly.
        # HIDE hides only the workspace; toolbar remains for re-opening.
        headbar=QWidget(self)
        headbar.setObjectName("dockControls")
        headrow=QHBoxLayout(headbar)
        headrow.setContentsMargins(2,0,2,0)
        headrow.setSpacing(2)
        self.heading.setFixedHeight(24)
        headrow.addWidget(self.heading,1)
        self.auto_hide_btn=QPushButton("AUTO")
        self.auto_hide_btn.setToolTip("Auto Hide khi chuyển khỏi Smaart")
        self.auto_hide_btn.setCheckable(True)
        self.auto_hide_btn.setChecked(True)
        self.live_btn=QPushButton("LIVE")
        self.live_btn.setToolTip("Tuning Live: ẩn tất cả SUM/MagEQ/FIR và panel RemiX")
        self.hide_btn=QPushButton("HIDE")
        self.hide_btn.setToolTip("Ẩn panel và toàn bộ đường RemiX; chọn tool để mở lại")
        for button,width in ((self.auto_hide_btn,36),(self.live_btn,33),(self.hide_btn,33)):
            button.setFixedSize(width,21)
            button.setStyleSheet(
                "QPushButton {font:bold 8px 'Segoe UI';background:#1B3544;"
                "color:#D1F4F9;border:1px solid #40677C;border-radius:4px;}"
                "QPushButton:checked {background:#17513A;color:#8CFFAA;}")
            headrow.addWidget(button)
        outer.addWidget(headbar)
        self.scroll=QScrollArea()''')
needle='''        self.dock=RightToolDock(engine,self.eq,self.fir)
        self.pages=self.dock.pages'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.dock=RightToolDock(engine,self.eq,self.fir)
        self.pages=self.dock.pages
        self.workspace_visible=True
        self.auto_hide_enabled=True
        self.dock.hide_btn.clicked.connect(self.hide_workspace)
        self.dock.live_btn.clicked.connect(self.return_to_tuning_live)
        self.dock.auto_hide_btn.toggled.connect(self._toggle_auto_hide)
        self.engine.overlay_workspace_visible=True
        self.engine.overlay_tool_mode="phase"''')
needle='''    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")
        key=(tuple(self.engine.current_pair or ()),'''
assert s.count(needle)==1
s=s.replace(needle,'''    def _toggle_auto_hide(self,enabled):
        self.auto_hide_enabled=bool(enabled)
        self.dock.auto_hide_btn.setChecked(bool(enabled))

    def _disable_model_overlays(self):
        # Hide every RemiX renderer. No change to Smaart trace data.
        self.engine.overlay_workspace_visible=False
        self.engine.ui_tool_enabled=False
        self.engine.refresh_visibility()
        self.native_eq.hide()
        self.native_eq._sync_sum_renderer()
        self.engine.refresh_visibility()

    def hide_workspace(self):
        self.workspace_visible=False
        self._disable_model_overlays()
        self.dock.hide()
        # The native Smaart toolbar remains visible for user re-entry.

    def return_to_tuning_live(self):
        self.hide_workspace()
        self.active=None
        self._style_buttons()

    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")
        self.workspace_visible=True
        self.engine.overlay_workspace_visible=True
        self.engine.overlay_tool_mode=mode
        key=(tuple(self.engine.current_pair or ()),''')
# Above replacement open key may need preserve exact parentheses: check syntax below!
needle='''        self.active=mode
        if self._toolbar_mode=="menu":'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.active=mode
        self.engine.overlay_tool_mode=mode
        self.engine.overlay_workspace_visible=True
        if self._toolbar_mode=="menu":''')
needle='''        if not self.dock.isVisible():self.dock.show()
        return True'''
assert s.count(needle)==1
s=s.replace(needle,'''        if self.workspace_visible:
            if not self.dock.isVisible():self.dock.show()
        else:
            self.dock.hide()
        return True''')
needle='''        if not active:
            self.native_eq.hide()
            self.hide()
            self.dock.hide()
            self._was_target=False
            return'''
assert s.count(needle)==1
s=s.replace(needle,'''        if not active:
            self.native_eq.hide()
            # AUTO: hide model overlays when Smaart loses foreground.
            # On returning, the previous selected tool can be resumed.
            self.engine.overlay_workspace_visible=False
            self.engine.refresh_visibility()
            self.hide()
            self.dock.hide()
            self._was_target=False
            return
        if self.workspace_visible:
            self.engine.overlay_workspace_visible=True
            self.engine.overlay_tool_mode=self.active or "live"
            self.engine.refresh_visibility()''')
needle='''            rect!=previous_rect or not self.isVisible() or
            not self.dock.isVisible()):'''
assert s.count(needle)==1
s=s.replace(needle,'''            rect!=previous_rect or not self.isVisible() or
            (self.workspace_visible and not self.dock.isVisible())):''')
s=s.replace("V8.21","V8.22")
p.write_text(s,encoding="utf8")
print("V822_DOCK_HEIGHT_HIDE_AUTO_LIVE_PATCHED")
