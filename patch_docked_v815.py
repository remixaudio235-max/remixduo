from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_15_TOPBAR_RIGHT_DOCK_QA")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8")
s=s.replace("from PyQt6.QtCore import Qt,QTimer,QEvent","from PyQt6.QtCore import Qt,QTimer,QEvent")
s=s.replace("QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget)","QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea)")
s=s.replace("from win_databar_v7 import locate_smaart","from win_databar_v7 import locate_smaart\nfrom dock_geometry_v815 import read_smaart_anchors,compute_dock_rects\nfrom concurrent.futures import ThreadPoolExecutor\nimport time")
start=s.index("class ToolHub(QWidget):")
new=r'''class RightToolDock(QWidget):
    """Floating, borderless *visual* sidebar, never injected into Smaart."""
    def __init__(self,engine,eq,fir):
        super().__init__(None)
        self.setObjectName("rightDock")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE+"""
          QWidget#rightDock {background:#08131D;border:1px solid #305168;}
          QLabel#dockHeading {background:#192C3C;color:#F2B15D;
              font:bold 10px 'Segoe UI';padding:3px 8px;}
          QScrollArea {border:0;background:#08131D;}
          QScrollBar:vertical {background:#132332;width:8px;}
          QScrollBar::handle:vertical {background:#38667C;
              border-radius:3px;min-height:25px;}
        """)
        self.setFixedWidth(205)
        outer=QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)
        self.heading=QLabel("AUTO PHASE")
        self.heading.setObjectName("dockHeading")
        self.heading.setFixedHeight(22)
        outer.addWidget(self.heading)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stack=QStackedWidget()
        self.pages={"phase":engine,"eq":eq,"fir":fir}
        self.page_heights={"phase":285,"eq":478,"fir":475}
        engine.header.hide()
        for widget in self.pages.values():
            widget.hide()
            widget.setParent(self.stack)
            widget.setWindowFlags(Qt.WindowType.Widget)
            widget.setFixedWidth(190)
            self.stack.addWidget(widget)
        self.stack.setFixedWidth(192)
        self.scroll.setWidget(self.stack)
        outer.addWidget(self.scroll)
        self.setFixedHeight(310)
    def select(self,mode):
        self.heading.setText({"phase":"AUTO PHASE","eq":"AUTO EQ",
                              "fir":"FIR"}[mode])
        widget=self.pages[mode]
        self.stack.setFixedHeight(self.page_heights[mode])
        self.stack.setCurrentWidget(widget)
        self.scroll.verticalScrollBar().setValue(0)
        widget.show()
    def apply_rect(self,rect):
        x,y,w,h=rect
        self.setFixedSize(w,h)
        self.move(x,y)

class ToolHub(QWidget):
    """Small navigator at top; workspace dock below Smaart TF Engine."""
    def __init__(self,engine):
        super().__init__(None)
        self.engine=engine
        self.engine.managed_mode=True
        self.engine.ui_tool_enabled=False
        self.eq=EQDialog(engine)
        self.fir=FIRDialog(engine)
        self.dock=RightToolDock(engine,self.eq,self.fir)
        self.pages=self.dock.pages
        self.buttons={}
        self.active=None
        self._was_target=False
        self._last_pair_key=None
        self._last_host_rect=None
        self._last_hwnd=None
        self._anchors=None
        self._anchor_requested_at=0.
        self._anchor_future=None
        self._anchor_pool=ThreadPoolExecutor(max_workers=1)
        self._manually_placed=False
        self._drag_offset=None
        self.setObjectName("hub")
        self.setWindowTitle("RemiX Signal V8.15")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(205,66)
        self.setStyleSheet(STYLE+"""
            QWidget#hub {background:#09141D;border:1px solid #28495E;}
            QFrame#hubTitle {background:#0C2331;border:0;
                border-bottom:1px solid #30556A;}
            QLabel#hubName {color:#6BEAF2;font:bold 12px 'Segoe UI';}
            QLabel#hubVer {color:#8EAAB9;font:9px 'Segoe UI';}
            QPushButton#hubClose {background:transparent;color:#ADCDD6;
                border:0;min-height:23px;font:bold 14px 'Segoe UI';}
            QPushButton#hubClose:hover {background:#9F354A;}
        """)
        main=QVBoxLayout(self)
        main.setContentsMargins(0,0,0,0)
        main.setSpacing(0)
        self.title_bar=QFrame(self)
        self.title_bar.setObjectName("hubTitle")
        self.title_bar.setFixedHeight(29)
        self.title_bar.installEventFilter(self)
        title=QHBoxLayout(self.title_bar)
        title.setContentsMargins(5,1,2,1)
        title.setSpacing(2)
        name=QLabel("RemiX Signal")
        name.setObjectName("hubName")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title.addWidget(name,1)
        version=QLabel("V8.15")
        version.setObjectName("hubVer")
        version.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title.addWidget(version)
        close=QPushButton("×")
        close.setObjectName("hubClose")
        close.setFixedSize(21,23)
        close.setToolTip("Đóng RemiX Signal")
        close.clicked.connect(self.close)
        title.addWidget(close)
        self.close_button=close
        main.addWidget(self.title_bar)
        self.nav_frame=QFrame(self)
        self.nav_frame.setFixedHeight(37)
        nav=QHBoxLayout(self.nav_frame)
        nav.setContentsMargins(3,2,3,3)
        nav.setSpacing(3)
        for mode,label in (("phase","Auto Phase"),("eq","Auto EQ"),
                           ("fir","FIR")):
            button=QPushButton(label)
            button.setMinimumHeight(27)
            button.setMaximumHeight(29)
            button.setToolTip(f"Hiển thị {label} trong cột phải Smaart")
            button.clicked.connect(lambda _,m=mode:self.select(m))
            nav.addWidget(button,3 if mode=="phase" else 2 if mode=="eq" else 1)
            self.buttons[mode]=button
        main.addWidget(self.nav_frame)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.select("phase")
        self.timer.start(175)
        self.show()
    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")
        key=(tuple(self.engine.current_pair or ()),
             tuple(id(t) for t in (self.engine.current_traces or ())))
        if key!=self._last_pair_key:
            self._last_pair_key=key
            self.eq.refresh_sources()
            self.fir.refresh_sources()
        self.active=mode
        self.engine.ui_tool_enabled=(mode=="phase")
        self.dock.select(mode)
        for name,button in self.buttons.items():
            button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:27px;"
                +("background:#FF9D35;color:#121820;border:0;"
                  "border-radius:4px;" if name==mode else
                  "background:#18364A;color:#B6D8E4;"
                  "border:1px solid #315169;border-radius:4px;"))
        if self._last_host_rect is not None and self._anchors is not None:
            self._update_placements(self._last_host_rect)
    def _screen_rect(self):
        r=QApplication.primaryScreen().availableGeometry()
        return (r.left(),r.top(),r.right()+1,r.bottom()+1)
    def _update_placements(self,host):
        rects=compute_dock_rects(host,self._anchors,self._screen_rect())
        if rects is None:
            self.dock.hide()
            return False
        if not self._manually_placed:
            x,y,w,h=rects.toolbar
            self.move(x,y)
        self.dock.apply_rect(rects.panel)
        if self.isVisible() and not self.dock.isVisible():self.dock.show()
        return True
    def eventFilter(self,obj,event):
        if obj is self.title_bar:
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                self._drag_offset=event.globalPosition().toPoint()-self.pos()
                return True
            if event.type()==QEvent.Type.MouseMove and self._drag_offset is not None:
                target=event.globalPosition().toPoint()-self._drag_offset
                r=QApplication.primaryScreen().availableGeometry()
                target.setX(max(r.left(),min(target.x(),r.right()-self.width()+1)))
                target.setY(max(r.top(),min(target.y(),r.bottom()-self.height()+1)))
                self.move(target)
                self._manually_placed=True
                return True
            if event.type()==QEvent.Type.MouseButtonRelease:
                self._drag_offset=None
                return True
            if event.type()==QEvent.Type.MouseButtonDblClick:
                self._manually_placed=False
                if self._last_host_rect and self._anchors:
                    self._update_placements(self._last_host_rect)
                return True
        return super().eventFilter(obj,event)
    def tick(self):
        pair=(tuple(self.engine.current_pair or ()),
              tuple(id(t) for t in (self.engine.current_traces or ())))
        if pair!=self._last_pair_key:
            self._last_pair_key=pair
            self.eq.refresh_sources()
            self.fir.refresh_sources()
        target=locate_smaart()
        active=bool(target and self.engine._target_is_foreground(target.hwnd))
        if not active:
            self.hide()
            self.dock.hide()
            self._was_target=False
            return
        rect=win32gui.GetWindowRect(target.hwnd)
        if target.hwnd!=self._last_hwnd:
            self._anchors=None
            self._last_hwnd=target.hwnd
            self._anchor_requested_at=0.
        if self._anchor_future is not None and self._anchor_future.done():
            try:self._anchors=self._anchor_future.result()
            except Exception:self._anchors=None
            self._anchor_future=None
        now=time.monotonic()
        if self._anchor_future is None and now-self._anchor_requested_at>3:
            self._anchor_requested_at=now
            self._anchor_future=self._anchor_pool.submit(read_smaart_anchors,target.hwnd)
        if not self.isVisible():self.show()
        if self._anchors is not None:
            if not self._was_target or rect!=self._last_host_rect:
                self._update_placements(rect)
            elif not self.dock.isVisible():
                self._update_placements(rect)
        else:
            self.dock.hide()
        self._last_host_rect=rect
        self._was_target=True
    def closeEvent(self,event):
        self.timer.stop()
        self._anchor_pool.shutdown(wait=False,cancel_futures=True)
        self.dock.hide()
        self.engine.ui_tool_enabled=False
        self.engine.managed_mode=False
        self.engine.close()
        self.dock.close()
        event.accept()
'''
s=s[:start]+new
p.write_text(s,encoding="utf8")
q=root/"overlay_v7.py"
t=q.read_text(encoding="utf8").replace("RemiX Signal V8.14","RemiX Signal V8.15").replace("SMAART · V8.14","SMAART · V8.15")
q.write_text(t,encoding="utf8")
print("V815_TWO_LINKED_WINDOWS_DOCKED_SMAART_UI_PATCHED")
