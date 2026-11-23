"""V8.14 unified title/header: one real window, three inline tool pages."""
from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_14_UNIFIED_TITLE_QA")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
s=s.replace("from PyQt6.QtCore import Qt,QTimer","from PyQt6.QtCore import Qt,QTimer,QEvent")
s=s.replace("QTextEdit,QFileDialog,QMessageBox,QFrame)","QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget)")
start=s.index("class ToolHub(QWidget):")
new=r'''class ToolHub(QWidget):
    """One movable floating tool palette. No detached header/windows.

    A title row, one navigation row, and exactly one body are children of
    this top-level widget. Existing engine and TF dialogs keep their
    persistent models; reparenting only affects presentation.
    """
    def __init__(self,engine):
        super().__init__()
        self.engine=engine
        self.engine.managed_mode=True
        self.engine.ui_tool_enabled=False
        self.eq=EQDialog(engine)
        self.fir=FIRDialog(engine)
        self.active=None
        self._was_target=False
        self._last_host_rect=None
        self._manually_placed=False
        self._drag_offset=None
        self._last_pair_key=None
        self.setObjectName("hub")
        self.setWindowTitle("RemiX Signal V8.14")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(205)
        self.setStyleSheet(STYLE+"""
            QWidget#hub { background:#09141D; border:1px solid #28495E; }
            QFrame#hubTitle {background:#0D2231;border:0;
                border-bottom:1px solid #275166;}
            QLabel#hubName {color:#63E6F4;font:bold 13px 'Segoe UI';}
            QLabel#hubVer {color:#8CADB9;font:9px 'Segoe UI';}
            QPushButton#hubClose {border:0;background:transparent;
                color:#A5C5D1;font:bold 15px 'Segoe UI';min-height:23px;}
            QPushButton#hubClose:hover {background:#A83647;color:white;}
            QFrame#hubNav {background:#101D2A;border:0;
                border-bottom:1px solid #244259;}
        """)
        main=QVBoxLayout(self)
        main.setContentsMargins(0,0,0,0)
        main.setSpacing(0)
        self.title_bar=QFrame(self)
        self.title_bar.setObjectName("hubTitle")
        self.title_bar.setFixedHeight(33)
        self.title_bar.installEventFilter(self)
        title_row=QHBoxLayout(self.title_bar)
        title_row.setContentsMargins(7,2,3,2)
        title_row.setSpacing(3)
        name=QLabel("RemiX Signal")
        name.setObjectName("hubName")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title_row.addWidget(name,1)
        version=QLabel("V8.14")
        version.setObjectName("hubVer")
        version.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title_row.addWidget(version)
        self.close_button=QPushButton("×")
        self.close_button.setObjectName("hubClose")
        self.close_button.setFixedSize(23,23)
        self.close_button.setToolTip("Đóng RemiX Signal")
        self.close_button.clicked.connect(self.close)
        title_row.addWidget(self.close_button)
        main.addWidget(self.title_bar)

        self.nav_frame=QFrame(self)
        self.nav_frame.setObjectName("hubNav")
        self.nav_frame.setFixedHeight(40)
        nav=QHBoxLayout(self.nav_frame)
        nav.setContentsMargins(4,3,4,4)
        nav.setSpacing(3)
        self.buttons={}
        for key,label in (("phase","Auto Phase"),
                          ("eq","Auto EQ"),
                          ("fir","FIR")):
            button=QPushButton(label)
            button.setObjectName("tool_"+key)
            button.setMinimumHeight(29)
            button.setMaximumHeight(30)
            button.setStyleSheet("font:bold 9px 'Segoe UI';min-height:28px;")
            button.clicked.connect(lambda _,mode=key:self.select(mode))
            button.setToolTip(f"Mở {label}")
            nav.addWidget(button, 3 if key=="phase" else (2 if key=="eq" else 1))
            self.buttons[key]=button
        main.addWidget(self.nav_frame)

        self.stack=QStackedWidget(self)
        self.stack.setContentsMargins(0,0,0,0)
        self.pages={"phase":self.engine,"eq":self.eq,"fir":self.fir}
        self.engine.hide()
        self.eq.hide()
        self.fir.hide()
        # Old Auto Phase duplicate logo/header is not needed once the
        # parent palette owns one shared brand title.
        self.engine.header.hide()
        self.engine.setFixedHeight(285)
        for widget in self.pages.values():
            widget.setParent(self.stack)
            widget.setWindowFlags(Qt.WindowType.Widget)
            self.stack.addWidget(widget)
        main.addWidget(self.stack)
        self._page_heights={"phase":285,"eq":478,"fir":475}
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.select("phase")
        self.timer.start(175)
        self.show()

    def select(self,name):
        if name not in self.pages:
            raise ValueError("Unsupported tool")
        self.active=name
        self.engine.ui_tool_enabled=(name=="phase")
        if name in ("eq","fir"):
            # Preserve preview on mode switching only when source pair
            # is unchanged; pair watcher invalidates on data reload.
            dialog=self.pages[name]
            if dialog.source.count()==0 or dialog.source.currentData() is None:
                dialog.refresh_sources()
        widget=self.pages[name]
        self.stack.setCurrentWidget(widget)
        self.stack.setFixedHeight(self._page_heights[name])
        self.setFixedHeight(33+40+self._page_heights[name])
        for mode,button in self.buttons.items():
            selected=mode==name
            button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:28px;"
                +("background:#FF982E;color:#15191F;"
                  "border:0;border-radius:5px;" if selected else
                  "background:#19364A;color:#A8DBE7;"
                  "border:1px solid #30536C;border-radius:5px;"))
        widget.show()

    def _dock(self,rect):
        screen=QApplication.primaryScreen().availableGeometry()
        x=max(screen.left()+3,min(rect[2]-self.width()-3,
                                  screen.right()-self.width()-3))
        y=max(screen.top()+3,min(rect[1]+66,
                                  screen.bottom()-self.height()-3))
        self.move(x,y)
        self._manually_placed=False

    def eventFilter(self,source,event):
        if source is self.title_bar:
            if event.type()==QEvent.Type.MouseButtonPress and (
                event.button()==Qt.MouseButton.LeftButton):
                self._drag_offset=(
                    event.globalPosition().toPoint()-self.frameGeometry().topLeft())
                return True
            if event.type()==QEvent.Type.MouseMove and self._drag_offset is not None:
                dest=event.globalPosition().toPoint()-self._drag_offset
                screen=QApplication.primaryScreen().availableGeometry()
                dest.setX(max(screen.left(),min(dest.x(),
                          screen.right()-self.width())))
                dest.setY(max(screen.top(),min(dest.y(),
                          screen.bottom()-self.height())))
                self.move(dest)
                self._manually_placed=True
                return True
            if event.type()==QEvent.Type.MouseButtonRelease:
                self._drag_offset=None
                return True
            if event.type()==QEvent.Type.MouseButtonDblClick:
                if self._last_host_rect is not None:
                    self._dock(self._last_host_rect)
                return True
        return super().eventFilter(source,event)

    def tick(self):
        pair_key=(tuple(self.engine.current_pair or ()),
                  tuple(id(x) for x in (self.engine.current_traces or ())))
        if pair_key!=self._last_pair_key:
            self._last_pair_key=pair_key
            self.eq.refresh_sources()
            self.fir.refresh_sources()
        target=locate_smaart()
        active=bool(target is not None and
                    self.engine._target_is_foreground(target.hwnd))
        if not active:
            if self.isVisible():self.hide()
            self._was_target=False
            return
        if not self.isVisible():self.show()
        rect=win32gui.GetWindowRect(target.hwnd)
        if not self._was_target:
            if not self._manually_placed:self._dock(rect)
        elif self._last_host_rect!=rect and not self._manually_placed:
            self._dock(rect)
        self._last_host_rect=rect
        self._was_target=True

    def closeEvent(self,event):
        self.timer.stop()
        self.engine.ui_tool_enabled=False
        self.engine.managed_mode=False
        # The attached pages are disposed with their parent widget;
        # close the original worker engine explicitly for thread cleanup.
        self.engine.close()
        event.accept()
'''
s=s[:start]+new
p.write_text(s,encoding="utf8")
p=root/"overlay_v7.py"
t=p.read_text(encoding="utf8")
assert t.count('self.setWindowTitle("RemiX Signal V8.13')==2
t=t.replace("V8.13 · Auto Phase","V8.14 · Auto Phase").replace(
    "V8.13 � Auto Phase","V8.14 · Auto Phase")
t=t.replace("SMAART · V8.13","SMAART · V8.14").replace(
    "SMAART � V8.13","SMAART · V8.14")
anchor='''        layout.addWidget(header)

        # TRACE / REFERENCE'''
assert t.count(anchor)==1
t=t.replace(anchor,'''        layout.addWidget(header)
        self.header=header  # Unified V8.14 parent hides duplicate header.

        # TRACE / REFERENCE''')
needle='''        if self.isVisible():
            area=QApplication.primaryScreen().availableGeometry()
            px=max(area.left()+8,min(r-self.width()-3,
                   area.right()-self.width()-8))
            py=max(area.top()+8,min(t+(164 if self.managed_mode else 75),
                   area.bottom()-self.height()-8))
            if abs(self.x()-px)>1 or abs(self.y()-py)>1:
                self.move(px,py)'''
assert t.count(needle)==1
t=t.replace(needle,'''        if self.isVisible() and not self.managed_mode:
            area=QApplication.primaryScreen().availableGeometry()
            px=max(area.left()+8,min(r-self.width()-3,
                   area.right()-self.width()-8))
            py=max(area.top()+8,min(t+75,
                   area.bottom()-self.height()-8))
            if abs(self.x()-px)>1 or abs(self.y()-py)>1:
                self.move(px,py)''')
t=t.replace('''        self.show()

    def on_selection(self,record):''',
            '''        self.show()

    def on_selection(self,record):''')
p.write_text(t,encoding="utf8")
print("V814_UNIFIED_FRAMELESS_TOOL_HUB_PATCHED")
