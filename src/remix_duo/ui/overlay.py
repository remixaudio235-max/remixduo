"""Shared Smaart-attached toolbar and compact tool panels.

Geometry is native-window driven. No curve is drawn without verified native
trace/axis evidence; this frontend never substitutes manual TRF for live state.
"""
import json
import os
from pathlib import Path
import time
from PyQt6.QtCore import Qt,QRect
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication,QWidget,QFrame,QLabel,QPushButton,
                            QVBoxLayout,QHBoxLayout,QMenu,QSystemTrayIcon)
from .native_monitor import NativeMonitor
from .widgets import show_notice

TOOLS={'phase':'Auto Phase','eq':'Auto EQ','fir':'Auto FIR'}
BAR_WIDTH=410
STYLE="""
QWidget{background:#171021;color:#F4EEFF;font:12px Arial;}
QFrame#card{background:#251735;border:1px solid #705084;border-radius:6px;}
QLabel#heading{color:#D9BCFF;font-weight:700;}
QPushButton{background:#38234E;border:1px solid #9873BF;border-radius:5px;padding:2px 7px;}
QPushButton:hover{background:#593878;}
QPushButton#run{background:#7034B8;border-color:#BD91F1;font-weight:700;}
"""

def overlay_rects(window,screen):
    x,y,w,h=window.rect;sx,sy,sw,sh=screen
    width,height=BAR_WIDTH,36
    left=min(max(round(x+w-190-width-8),sx+4),sx+sw-width-4)
    top=min(max(round(y+54),sy+4),sy+sh-height-4)
    bar=(left,top,width,height)
    pw,ph=446,400
    px=min(max(left+width-pw,sx+4),sx+sw-pw-4)
    py=min(max(top+height+6,sy+4),sy+sh-ph-4)
    return bar,(px,py,pw,ph)

def _window_flags():
    return Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint

class OverlayBar(QWidget):
    def __init__(self,controller):
        super().__init__(None,_window_flags())
        self.controller=controller;self.setWindowTitle('RemiX Duo · Smaart Overlay')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setStyleSheet(STYLE);self.setFixedSize(BAR_WIDTH,36)
        layout=QHBoxLayout(self);layout.setContentsMargins(5,4,5,4);layout.setSpacing(4)
        badge=QLabel('RemiX Duo · ACTIVE');badge.setObjectName('heading');layout.addWidget(badge)
        self.buttons={}
        for key,title in TOOLS.items():
            button=QPushButton(title);button.setFixedHeight(26)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda checked=False,k=key:controller.open_tool(k))
            self.buttons[key]=button;layout.addWidget(button)
    def contextMenuEvent(self,event):
        menu=QMenu(self)
        manual=menu.addAction('Mở TRF thủ công… (công cụ phụ)')
        quit_=menu.addAction('Thoát RemiX Duo')
        action=menu.exec(event.globalPos())
        if action==manual:self.controller.open_manual()
        elif action==quit_:QApplication.instance().quit()

class ToolPanel(QWidget):
    def __init__(self,controller):
        super().__init__(None,_window_flags())
        self.controller=controller;self.setWindowTitle('RemiX Duo · Native Tool')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setStyleSheet(STYLE);self.setFixedSize(446,400)
        layout=QVBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(8)
        header=QHBoxLayout();self.heading=QLabel('AUTO PHASE');self.heading.setObjectName('heading')
        header.addWidget(self.heading);header.addStretch()
        hide=QPushButton('HIDE');hide.setFixedHeight(26);hide.clicked.connect(controller.hide_tool)
        header.addWidget(hide);layout.addLayout(header)
        self.run=QPushButton('AUTO PHASE');self.run.setObjectName('run');self.run.setFixedHeight(26)
        self.run.clicked.connect(controller.run_tool);layout.addWidget(self.run)
        self.trace1=QLabel('Trace 1 · chưa xác minh tick')
        self.trace2=QLabel('Trace 2 · chưa xác minh tick')
        layout.addWidget(self.trace1);layout.addWidget(self.trace2)
        self.fs=QLabel('Fs · chưa xác minh từ nguồn native');layout.addWidget(self.fs)
        card=QFrame();card.setObjectName('card');box=QVBoxLayout(card)
        self.status=QLabel('HOLD: chờ bằng chứng trace và trục Smaart.');self.status.setWordWrap(True)
        box.addWidget(self.status);layout.addWidget(card)
        self.top3=QLabel('Top 3\n1. —\n2. —\n3. —');layout.addWidget(self.top3)
        layout.addStretch();hint=QLabel('Không dùng highlight hoặc dữ liệu cache làm xác nhận tick.')
        hint.setWordWrap(True);layout.addWidget(hint)

class OverlayController:
    def __init__(self,backend,*,start=True):
        self.backend=backend;self.window=None;self.evidence=None;self.tool='phase'
        self.closed=False;self.native_plots=[];self.manual=None;self._last_log=None;self.panel_requested=False
        self.bar=OverlayBar(self);self.panel=ToolPanel(self)
        self.tray=None
        if QSystemTrayIcon.isSystemTrayAvailable():
            from ..platforms.paths import app_paths
            self.tray=QSystemTrayIcon(QIcon(str(app_paths().resource('remix_dou_swirl_toolbar32.png'))))
            self.tray.setToolTip('RemiX Duo · Auto Phase / EQ / FIR')
            menu=QMenu();self.tray_state=menu.addAction('Chờ cửa sổ Smaart');self.tray_state.setEnabled(False)
            menu.addAction('Thoát RemiX Duo',QApplication.instance().quit)
            self.tray.setContextMenu(menu);self.tray_menu=menu;self.tray.show()
        for widget in (self.bar,self.panel):backend.configure_overlay(widget)
        self.monitor=NativeMonitor(backend)
        self.monitor.geometry_changed.connect(self.follow_host)
        self.monitor.selection_changed.connect(self.accept_selection)
        self.monitor.reason_changed.connect(self.show_reason)
        if start:self.monitor.start()

    def screen_bounds(self,window):
        center=QRect(*map(round,window.rect)).center()
        screen=QApplication.screenAt(center) or QApplication.primaryScreen()
        return screen.geometry().getRect()

    def follow_host(self,window):
        if self.closed:return
        allowed=window is not None and window.on_screen and (window.foreground or window.companion_foreground)
        self.window=window if allowed else None
        if not allowed:
            self.evidence=None;self.bar.hide();self.panel.hide()
            for plot in self.native_plots:plot.hide()
            if self.tray:self.tray_state.setText('Ẩn · chờ Smaart ở trước')
            return
        bar,panel=overlay_rects(window,self.screen_bounds(window))
        self.bar.setGeometry(*bar);self.panel.setGeometry(*panel)
        self.bar.show()
        if self.tray:self.tray_state.setText('Đang bám cửa sổ Smaart')
        if self.panel_requested:self.panel.show()
        # Avoid activating the companion app or stealing Smaart focus on every tick.
        log=os.environ.get('REMIX_DUO_QA_GEOMETRY_LOG')
        marker=(window.ref,window.rect,bar,self.bar.isVisible())
        if log and marker!=self._last_log:
            record={'time':time.monotonic(),'pid':window.ref.pid,'window':window.ref.opaque_id,
                    'host':window.rect,'bar':self.bar.geometry().getRect(),
                    'visible':self.bar.isVisible()}
            with Path(log).open('a',encoding='utf-8') as output:output.write(json.dumps(record)+'\n')
            self._last_log=marker

    def open_tool(self,tool):
        if self.window is None:return
        self.tool=tool;self.panel.heading.setText(TOOLS[tool].upper());self.panel.run.setText(TOOLS[tool].upper())
        self.panel_requested=True
        self.panel.trace2.setVisible(tool=='phase');self.panel.top3.setVisible(tool=='phase')
        self.follow_host(self.window);self.panel.show();self.panel.raise_()
        self.run_tool()

    def accept_selection(self,evidence):
        self.evidence=evidence
        if evidence is None or not evidence.complete:
            self.panel.trace1.setText('Trace 1 · chưa xác minh tick')
            self.panel.trace2.setText('Trace 2 · chưa xác minh tick')
            return
        names=evidence.selected
        self.panel.trace1.setText('Trace 1 · '+(names[0] if names else '—'))
        self.panel.trace2.setText('Trace 2 · '+(names[1] if len(names)>1 else '—'))

    def hide_tool(self):
        self.panel_requested=False;self.panel.hide()

    def run_tool(self):
        expected=2 if self.tool=='phase' else 1
        e=self.evidence;now=time.monotonic()
        selected=e.verified_selected(self.window.ref if self.window else None,
                                     now,expected) if e is not None else None
        if selected is None:
            reason=f'HOLD: cần đúng {expected} trace có tick được xác minh mới. Không chọn trace thay bạn.'
        else:
            reason='HOLD: chưa có TF/Fs và trục native được kiểm chứng; chưa vẽ SUM/MagEQ/FIR.'
        self.show_reason(reason)
        if self.panel.isVisible():show_notice(self.panel,reason)

    def show_reason(self,reason):
        if not self.closed:self.panel.status.setText(reason)

    def open_manual(self):
        from .workspace import Workspace
        if self.manual is None or self.manual._closed:self.manual=Workspace()
        self.manual.show();self.manual.raise_()

    def close(self):
        if self.closed:return
        self.closed=True;self.monitor.close()
        self.bar.close();self.panel.close()
        if self.manual is not None:self.manual.close()
        if self.tray:self.tray.hide()
