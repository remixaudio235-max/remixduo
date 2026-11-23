"""Independent bounded workers for geometry and AX selection; no GUI-thread I/O."""
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import QObject,QTimer,pyqtSignal,Qt

class NativeEvents(QObject):
    geometry=pyqtSignal(object,object)
    selection=pyqtSignal(object,object,object)

class NativeMonitor(QObject):
    geometry_changed=pyqtSignal(object)
    selection_changed=pyqtSignal(object)
    reason_changed=pyqtSignal(str)

    def __init__(self,backend,parent=None):
        super().__init__(parent)
        self.backend=backend;self.window=None;self.closed=False
        self._geometry_busy=False;self._selection_busy=False
        self._geometry_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='DuoWindow')
        self._selection_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='DuoSelection')
        self.events=NativeEvents(self)
        self.events.geometry.connect(self.accept_geometry,Qt.ConnectionType.QueuedConnection)
        self.events.selection.connect(self.accept_selection,Qt.ConnectionType.QueuedConnection)
        self.geometry_timer=QTimer(self);self.geometry_timer.setInterval(16)
        self.geometry_timer.timeout.connect(self.poll_geometry)
        self.selection_timer=QTimer(self);self.selection_timer.setInterval(500)
        self.selection_timer.timeout.connect(self.poll_selection)

    def start(self):
        if self.closed:return
        self.geometry_timer.start();self.selection_timer.start();self.poll_geometry()

    def poll_geometry(self):
        if self.closed or self._geometry_busy:return
        self._geometry_busy=True;events=self.events
        future=self._geometry_pool.submit(self.backend.list_windows)
        def done(f):
            try: value,error=f.result(),None
            except Exception as exc:value,error=None,str(exc)
            try:events.geometry.emit(value,error)
            except RuntimeError:pass
        future.add_done_callback(done)

    def accept_geometry(self,windows,error):
        if self.closed:return
        self._geometry_busy=False
        old=self.window
        self.window=next((w for w in windows or [] if (w.foreground or w.companion_foreground) and w.on_screen),None)
        self.geometry_changed.emit(self.window)
        if self.window is None:
            self.selection_changed.emit(None)
            self.reason_changed.emit(error or 'HOLD: đưa cửa sổ Smaart ra trước')
        elif old is None or old.ref!=self.window.ref:
            self.selection_changed.emit(None);self.poll_selection()

    def poll_selection(self):
        if self.closed or self._selection_busy or self.window is None:return
        self._selection_busy=True;window=self.window;events=self.events
        future=self._selection_pool.submit(self.backend.read_selection,window.ref)
        def done(f):
            try:value,error=f.result(),None
            except Exception as exc:value,error=None,str(exc)
            try:events.selection.emit(window,value,error)
            except RuntimeError:pass
        future.add_done_callback(done)

    def accept_selection(self,window,evidence,error):
        if self.closed:return
        self._selection_busy=False
        if self.window!=window:return
        if error:
            self.selection_changed.emit(None);self.reason_changed.emit(error);return
        self.selection_changed.emit(evidence)
        if evidence is None or not evidence.complete:
            self.reason_changed.emit('HOLD: Smaart chưa cung cấp đầy đủ trạng thái bật/tắt của từng trace; không dùng highlight làm tick')
        else:self.reason_changed.emit(f'Đã đọc đầy đủ {len(evidence.visible_verified)} trace · {len(evidence.selected)} đang bật')

    def close(self):
        if self.closed:return
        self.closed=True;self.window=None
        self.geometry_timer.stop();self.selection_timer.stop()
        self._geometry_pool.shutdown(wait=False,cancel_futures=True)
        self._selection_pool.shutdown(wait=False,cancel_futures=True)
