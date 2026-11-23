from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_16_REALTIME_ROW_DOCK_QA")
p=root/"dock_geometry_v815.py"
s=p.read_text(encoding="utf8").replace("    panel:Rect    # x,y,width,height","    panel:Optional[Rect]    # None when no safe room in right sidebar")
s=s.replace("    if available<190:return None","    if available<190:\n        return DockRects((x,real_y,width,real_h),None)")
p.write_text(s,encoding="utf8")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
s=s.replace("QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea)",
            "QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea,QMenu)")
s=s.replace("from PyQt6.QtCore import Qt,QTimer,QEvent","from PyQt6.QtCore import Qt,QTimer,QEvent,QPoint")
begin=s.index("        self.setWindowTitle(\"RemiX Signal V8.15\")",s.index("class ToolHub(QWidget):"))
end=s.index("        self.timer=QTimer(self)",begin)
new='''        self.setWindowTitle("RemiX Signal V8.16")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # IMPORTANT: 3 buttons in ONE native row with Real Time / Impulse / SPL.
        # No title row (V8.15 used two rows and covered the plot header).
        self.setFixedSize(205,30)
        self.setStyleSheet(STYLE+"""
            QWidget#hub {background:#0C1A26;border:1px solid #33556B;}
        """)
        main=QHBoxLayout(self)
        main.setContentsMargins(2,1,2,1)
        main.setSpacing(3)
        self.nav_frame=self
        self.title_bar=None
        for mode,label in (("phase","Auto Phase"),
                           ("eq","Auto EQ"),
                           ("fir","FIR")):
            button=QPushButton(label)
            button.setMinimumHeight(27)
            button.setMaximumHeight(28)
            button.setToolTip(f"RemiX Signal · {label}")
            button.clicked.connect(lambda _,m=mode:self.select(m))
            main.addWidget(button,3 if mode=="phase" else 2 if mode=="eq" else 1)
            self.buttons[mode]=button
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._menu=QMenu(self)
        self._menu.addAction("Đóng RemiX Signal",self.close)
        self.customContextMenuRequested.connect(
            lambda pos:self._menu.exec(self.mapToGlobal(pos)))
'''
s=s[:begin]+new+s[end:]
s=s.replace('''    def _screen_rect(self):
        r=QApplication.primaryScreen().availableGeometry()
        return (r.left(),r.top(),r.right()+1,r.bottom()+1)''',
'''    def _screen_rect(self):
        # Use the monitor containing Smaart rather than primary monitor
        # when the user drags Smaart to another display.
        if self._last_host_rect:
            x1,y1,x2,y2=self._last_host_rect
            screen=QApplication.screenAt(QPoint((x1+x2)//2,(y1+y2)//2))
        else:
            screen=None
        r=(screen or QApplication.primaryScreen()).availableGeometry()
        return (r.left(),r.top(),r.right()+1,r.bottom()+1)''')
begin=s.index("    def _update_placements(self,host):")
end=s.index("    def tick(self):",begin)
new='''    def _update_placements(self,host):
        rects=compute_dock_rects(host,self._anchors,self._screen_rect())
        if rects is None:
            self.hide()
            self.dock.hide()
            return False
        x,y,w,h=rects.toolbar
        self.setFixedSize(w,h)
        self.move(x,y)
        if not self.isVisible():self.show()
        if rects.panel is None:
            self.dock.hide()
        else:
            self.dock.apply_rect(rects.panel)
            if not self.dock.isVisible():self.dock.show()
        return True
'''
s=s[:begin]+new+s[end:]
s=s.replace("now-self._anchor_requested_at>3:","now-self._anchor_requested_at>0.8:")
needle='''        if not self.isVisible():self.show()
        if self._anchors is not None:
            if anchor_changed or not self._was_target or rect!=self._last_host_rect:
                self._update_placements(rect)
            elif not self.dock.isVisible():
                self._update_placements(rect)
        else:
            self.dock.hide()
        self._last_host_rect=rect'''
repl='''        # The native Smaart chrome is the positional authority.
        # Re-anchor every time Smaart moves/resizes, or UIA anchors change.
        # No manual float override: the three buttons ALWAYS share its row.
        self._last_host_rect=rect
        if self._anchors is not None:
            if (anchor_changed or not self._was_target or
                rect!=previous_rect or not self.isVisible()):
                self._update_placements(rect)
        else:
            self.hide()
            self.dock.hide()'''
assert needle in s,"TICK ANCHOR"
s=s.replace(needle,repl)
needle="        rect=win32gui.GetWindowRect(target.hwnd)\n        if target.hwnd!=self._last_hwnd:"
assert needle in s
s=s.replace(needle,"        rect=win32gui.GetWindowRect(target.hwnd)\n        previous_rect=self._last_host_rect\n        if target.hwnd!=self._last_hwnd:")
# Remove eager window appearance before there are valid UIA anchors.
s=s.replace('''        self.timer.start(175)
        self.show()
    def select(self,mode):''',
'''        self.timer.start(175)
        # wait for native button anchors; do not flash in screen center
        self.hide()
        self.dock.hide()
    def select(self,mode):''')
s=s.replace("        if self._last_host_rect is not None and self._anchors is not None:",
            "        if self._last_host_rect is not None and self._anchors is not None:")
p.write_text(s,encoding="utf8")
q=root/"overlay_v7.py"
s=q.read_text(encoding="utf8").replace("V8.15","V8.16")
q.write_text(s,encoding="utf8")
print("V816_EXACT_NATIVE_BUTTON_ROW_PATCH_COMPLETE")
