"""Portable offline workspace; never represents imported TRF as live TF/ticks."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import numpy as np
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
                            QComboBox,QFileDialog,QPlainTextEdit)
from .. import __version__
from ..application.design import DesignRequest,calculate
from ..core.traces import read_trf,compute_sum
from ..core.fir_export import write_export
from ..core.fir_preview import cascade_magnitude
from .widgets import MiniPlot,show_notice

class Completion(QObject):
    finished=pyqtSignal(int,object,object)

class Workspace(QWidget):
    def __init__(self,backend=None):
        super().__init__()
        self.setWindowTitle(f'RemiX Duo {__version__} · TRF Offline Alpha')
        self.resize(820,740)
        self.setMinimumSize(620,560)
        self.setStyleSheet('QWidget{background:#171021;color:#F4EEFF;font:14px "Arial";}'
            'QPushButton,QComboBox{background:#38224F;border:1px solid #A78BFA;border-radius:7px;padding:9px;}'
            'QPushButton:disabled{color:#9989A8;border-color:#5C486C;}'
            'QPlainTextEdit{background:#100B18;border:1px solid #705284;padding:8px;}')
        logo=Path(__file__).resolve().parents[1]/'resources/remixduo_app.ico'
        self.setWindowIcon(QIcon(str(logo)))
        self.traces=[None,None];self.result=None;self.request=None
        self._generation=0;self._closed=False;self._busy=False
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='DuoDesign')
        self._events=Completion(self)
        self._events.finished.connect(self._finished,Qt.ConnectionType.QueuedConnection)
        layout=QVBoxLayout(self)
        title=QLabel('RemiX Duo · Không gian TRF dùng chung')
        title.setStyleSheet('font-size:23px;font-weight:bold;color:#D2B8FF;')
        layout.addWidget(title)
        notice=QLabel('OFFLINE ALPHA · Dữ liệu TRF đã lưu, không phải TF trực tiếp.\n'
                      'HOLD: nhận tick và overlay Smaart trên macOS chưa được kiểm chứng.')
        notice.setWordWrap(True);layout.addWidget(notice)
        self.native_monitor=None
        if backend is not None and hasattr(backend,'list_windows'):
            self.native_status=QLabel('Smaart native · chưa theo dõi');self.native_status.setWordWrap(True)
            layout.addWidget(self.native_status)
            native_button=QPushButton('Kiểm tra cửa sổ/tick Smaart (chỉ đọc)')
            layout.addWidget(native_button)
            from .native_monitor import NativeMonitor
            self.native_monitor=NativeMonitor(backend,self)
            self.native_monitor.reason_changed.connect(self.native_status.setText)
            # Native diagnostics do not own explicitly imported offline TRFs.
            # A future native-bound source must invalidate through its own identity gate.
            native_button.clicked.connect(self.native_monitor.start)
        self.labels=[]
        for index in range(2):
            row=QHBoxLayout();button=QPushButton(f'Mở TRF {index+1}')
            button.clicked.connect(lambda checked=False,i=index:self.choose_trace(i))
            label=QLabel('Chưa chọn');label.setWordWrap(True)
            self.labels.append(label);row.addWidget(button);row.addWidget(label,1);layout.addLayout(row)
        row=QHBoxLayout();self.fs=QComboBox()
        self.fs.addItem('Chọn Fs của phép đo…',None)
        for fs in (44100,48000,88200,96000,192000): self.fs.addItem(f'{fs} Hz',fs)
        self.fs.currentIndexChanged.connect(self.invalidate)
        self.tool=QComboBox()
        for title,key in [('Auto Phase · hai TRF','phase'),('Auto EQ · TRF 1','eq'),
                          ('FIR MAG · TRF 1','fir'),('FIR Phase · TRF 1','fir_phase')]:
            self.tool.addItem(title,key)
        self.tool.currentIndexChanged.connect(self.invalidate)
        row.addWidget(self.fs);row.addWidget(self.tool);layout.addLayout(row)
        self.plot=MiniPlot();layout.addWidget(self.plot)
        self.status=QLabel('Chọn TRF và xác nhận Fs để tính.');self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);layout.addWidget(self.details,1)
        row=QHBoxLayout();self.run_button=QPushButton('Tính từ TRF')
        self.run_button.clicked.connect(self.run_design)
        self.export_button=QPushButton('Xuất kết quả…');self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_result)
        row.addWidget(self.run_button);row.addWidget(self.export_button);layout.addLayout(row)

    def invalidate(self,*args):
        self._generation+=1;self.result=None;self.request=None
        self.export_button.setEnabled(False);self.plot.clear()
        self.details.clear();self.status.setText('Đầu vào thay đổi · cần tính lại.')

    def choose_trace(self,index):
        filename,_=QFileDialog.getOpenFileName(self,'Mở TRF đã lưu','','Smaart TRF (*.trf)')
        if not filename:return
        try: trace=read_trf(filename)
        except Exception as exc: show_notice(self,str(exc));return
        self.invalidate();self.traces[index]=trace
        self.labels[index].setText(str(trace.path))

    def run_design(self):
        try:
            if self.traces[0] is None: raise ValueError('Chưa chọn TRF 1')
            request=DesignRequest.create(self.tool.currentData(),*self.traces,fs=self.fs.currentData())
            self.submit_request(request)
        except (ValueError,RuntimeError) as exc:
            self.status.setText(str(exc));show_notice(self,str(exc))

    def submit_request(self,request):
        if self._closed: raise RuntimeError('Workspace closed')
        if self._busy: raise RuntimeError('Đang tính; vui lòng chờ kết quả hiện tại')
        self.invalidate();self._busy=True;self.request=request
        generation=self._generation
        self.run_button.setEnabled(False);self.status.setText('Đang tính trên worker…')
        events=self._events
        future=self._pool.submit(calculate,request)
        def complete(future):
            try: result,error=future.result(),None
            except BaseException as exc: result,error=None,str(exc)
            try: events.finished.emit(generation,result,error)
            except RuntimeError: pass  # Qt owner already destroyed; no UI work here.
        future.add_done_callback(complete)

    def _finished(self,generation,result,error):
        if self._closed:return
        self._busy=False;self.run_button.setEnabled(True)
        if generation!=self._generation:return
        if error:
            self.status.setText(error);show_notice(self,error);return
        self.result=result;req=self.request
        if req.tool=='phase':
            text='\n'.join(f'{i+1}. Delay {c.delay_ms:.2f} ms | Đảo cực {c.invert_trace2} | Score {c.score_db:.2f} dB' for i,c in enumerate(result))
            if result:
                c=result[0];before=compute_sum(req.trace,req.reference)
                after=compute_sum(req.trace,req.reference,c.delay_ms,c.invert_trace2)
                self.plot.set_curves(before.hz,before.mag_db,after.mag_db)
        elif req.tool=='eq':
            self.plot.set_curves(result.hz,result.before_db,result.after_db)
            text='\n'.join(f'{p.freq_hz:.1f} Hz | {p.gain_db:+.2f} dB | Q {p.q:.2f}' for p in result.peqs)
            text+='\n'+'; '.join(result.warnings)
        else:
            t=req.trace
            before,after,_=cascade_magnitude(t.hz,t.h,result.taps,result.fs)
            self.plot.set_curves(t.hz,before,after)
            text=f'{result.fs} Hz · {len(result.taps)} taps · độ trễ {result.latency_ms:.2f} ms\nFIR thiết kế từ TRF, chưa xác minh trên DSP.'
        self.details.setPlainText(text or 'Không đủ dữ liệu đáng tin cậy; không có kết quả.')
        self.status.setText('Hoàn tất mô phỏng OFFLINE · chưa ghi Smaart/DSP.')
        self.export_button.setEnabled(bool(result) if isinstance(result,list) else result is not None)

    def export_result(self):
        if self.result is None or self.request is None:return
        fir=self.request.tool in ('fir','fir_phase')
        name,_=QFileDialog.getSaveFileName(self,'Xuất kết quả offline','','WAV Float32 (*.wav)' if fir else 'JSON (*.json)')
        if not name:return
        try:
            if fir: write_export(self.result,'Generic WAV Float32',name)
            else:
                from dataclasses import asdict
                data={'mode':'stored_trf_offline','fs':self.request.fs,
                      'sources':[str(t.path) for t in (self.request.trace,self.request.reference) if t is not None],
                      'native_verified':False,
                      'result':[asdict(x) for x in (self.result if isinstance(self.result,list) else self.result.peqs)]}
                Path(name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            self.status.setText('Đã xuất file offline: '+name)
        except (OSError,ValueError) as exc: show_notice(self,str(exc))

    def closeEvent(self,event):
        self._closed=True;self._generation+=1
        if self.native_monitor is not None:self.native_monitor.close()
        self._pool.shutdown(wait=False,cancel_futures=True)
        super().closeEvent(event)
