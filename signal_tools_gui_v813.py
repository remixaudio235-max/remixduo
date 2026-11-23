"""Three-window workflow for RemiX Duo.

Main launcher (three buttons) docks to Smaart's right control column.
Exactly one working dialog is shown at a time: Auto Phase (the original
V8.12 engine), Auto EQ, or FIR. AutoEQ/FIR calculate from stored TF data;
nothing is written to Smaart or hardware.
"""
from __future__ import annotations
import math,concurrent.futures,hashlib,os  # V8.119: os used by PEQ drag reject path
from dataclasses import replace
from pathlib import Path
from trf_core import read_trf
from smaart_fs_sync_v841 import read_saved_smaart_fs
import numpy as np
import win32gui
from PyQt6.QtCore import Qt,QTimer,QEvent,QPoint,QObject,pyqtSignal
from PyQt6.QtGui import QColor,QPen,QPainter,QPainterPath,QPixmap
from PyQt6.QtWidgets import (QWidget,QDialog,QApplication,QVBoxLayout,
    QHBoxLayout,QLabel,QPushButton,QComboBox,QDoubleSpinBox,QSpinBox,
    QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea,QMenu,QCheckBox,QSizePolicy,QButtonGroup)
from signal_tools_core_v813 import (source_arrays,
    design_linear_phase_fir,design_phase_only_fir,save_fir_txt,save_fir_wav_float)
# V8.137: keep the historic local symbol name so existing QA monkeypatches
# still intercept the worker, but the GUI now uses automatic Boost/Cut limits.
from remix_autoeq_v05_adapter import design_remix_eq_auto_limits as design_remix_eq
from native_eq_mag_v06 import NativeAutoEQMag
from fir_native_v846 import NativeFIROverlay,make_source
from autoeq_export_dialog_v08 import EQExportSnapshot,EQExportDialog
from win_databar_v7 import locate_smaart
from dock_geometry_v815 import read_smaart_anchors,compute_dock_rects
from dock_tiers_v8122 import FULL_PAGE_H
from remix_layout_v856 import style_dock,style_active_heading,fit_fir_content
from concurrent.futures import ThreadPoolExecutor
import time
from remix_duo.ui.widgets import MiniPlot, show_notice, show_plot_notice, STYLE


FIR_PHASE_MIN_IMPROVEMENT_PCT=5.0   # V8.118: below this, FIR Phase is HOLD


def schedule_auto_wait_notice(owner,still_running,preferred=None):
    """Show one busy notice only when the same operation exceeds 50 ms."""
    def later():
        try:
            if not still_running():return
            target=preferred if preferred is not None else owner
            if target is None or not target.isVisible():target=owner
            show_notice(target,"Đang Auto, vui lòng đợi...")
        except (RuntimeError,AttributeError):
            return  # owner was closed while the worker was running
    QTimer.singleShot(50,later)


def autoeq_error_vn(reason):
    """User-facing Auto EQ failure with a concrete recovery action.

    Solver exceptions remain diagnostic data; the dock/toast never exposes a
    bare English implementation message to the operator.
    """
    text=str(reason)
    lowered=text.lower()
    if "1/4-oct peq plan" in lowered or "target regression" in lowered:
        return ("Không tạo được Auto EQ: các PEQ quá gần nhau; sau khi ép khoảng "
                "cách 1/4 octave, đáp tuyến lệch mục tiêu quá mức an toàn. "
                "Cách xử lý: kéo LF/HF bỏ vùng dao động mạnh, giảm số PEQ tối đa "
                "hoặc giảm Boost tối đa rồi bấm AUTO EQ lại.")
    if "worsened nearby dip" in lowered:
        return ("Không tạo được Auto EQ: bộ PEQ dự kiến làm hố đáp tuyến lân cận "
                "sâu hơn. Cách xử lý: kéo LF/HF tránh vùng hố sâu hoặc giảm Boost "
                "tối đa rồi bấm AUTO EQ lại.")
    if "not enough" in lowered and ("tf bin" in lowered or "bin" in lowered):
        return ("Không tạo được Auto EQ: dải LF/HF hiện tại có quá ít dữ liệu TF "
                "hợp lệ. Cách xử lý: kéo LF/HF vào vùng có đường Magnitude liên tục "
                "rồi bấm AUTO EQ lại. Coherence chỉ là thông số tham khảo.")
    if text=="NO_APPROVED_PEQ":
        return ("Không tạo được PEQ phù hợp với các giới hạn hiện tại. Cách xử lý: "
                "kéo LF/HF vào vùng cần sửa, tăng hoặc giảm số PEQ tối đa, hoặc đổi "
                "mức Boost tối đa rồi bấm AUTO EQ lại.")
    return ("Không tạo được Auto EQ do dữ liệu hoặc giới hạn an toàn hiện tại. "
            "Cách xử lý: kiểm tra đúng 1 Trace đang tick, kéo lại LF/HF, giảm số "
            "PEQ hoặc Boost tối đa rồi bấm AUTO EQ lại.")


def _middle_elide(text,limit):
    """Keep start and end of a trace name: 'VIP 2 SKY…find 8,83-1'."""
    text=str(text)
    if len(text)<=limit:return text
    head=(limit-1)//2
    return text[:head]+"…"+text[-(limit-1-head):]


def _fir_display_now():
    """perf_counter clock for the V8.107 FIR display bridge (test hook)."""
    return time.perf_counter()

def trace_recognition_text(observer,token,count):
    if token is not None:return f"Đã xác minh 3/3 · {Path(token[0]).stem}"
    if count is not None and count!=1:return f"Đã thấy {count} Trace bật · cần đúng 1"
    stable=int(getattr(observer,"single_stable",0)) if observer else 0
    candidate=getattr(observer,"single_candidate",None) if observer else None
    name=Path(candidate[0]).stem if candidate else "Trace"
    return f"Đang xác minh {stable}/3 · {name}"

def stable_anchor_sample(current,pending,latest):
    if latest is None:return current,pending
    if current is None or latest==current:return latest,None
    if pending==latest:return latest,None
    return current,latest





class TFDialog(QDialog):
    def __init__(self,engine,name):
        super().__init__(None)
        self.engine=engine
        self.setWindowTitle(f"RemiX Duo · {name}")
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE)
        self.setFixedWidth(205)
        self.result=None
        self.main=QVBoxLayout(self)
        self.main.setContentsMargins(7,8,7,8)
        self.main.setSpacing(6)
        heading=QLabel(name.upper());heading.setObjectName("title")
        self.main.addWidget(heading)
        self.note=QLabel("Dữ liệu TRF đã lưu · Không gửi DSP")
        self.note.setObjectName("hint");self.note.setWordWrap(True)
        self.main.addWidget(self.note)
        self.source=QComboBox()
        self.source.currentIndexChanged.connect(self.invalidate)
        self.main.addWidget(self.source)
        self.plot=MiniPlot()
        self.main.addWidget(self.plot)
        self.summary=QLabel("Chọn Trace và nhấn Tính")
        self.summary.setObjectName("score")
        self.summary.setWordWrap(True)
        self.main.addWidget(self.summary)
        self.details=QTextEdit()
        self.details.setReadOnly(True)
        self.main.addWidget(self.details)
        self.refresh_sources()
    def refresh_sources(self):
        previous=self.source.currentIndex()
        self.source.blockSignals(True)
        self.source.clear()
        if self.engine.current_traces:
            for i,trace in enumerate(self.engine.current_traces):
                self.source.addItem(f"T{i+1} · {trace.path.stem[:12]}",i)
            self.source.addItem("SUM · TF Model",2)
            self.source.setCurrentIndex(min(max(0,previous),2))
        else:self.source.addItem("Đang chờ 2 Trace",None)
        self.source.blockSignals(False)
        self.invalidate()
    def invalidate(self,*_):
        self.result=None
        self.plot.clear()
        self.summary.setText("Nhấn Tính để cập nhật kết quả.")
        self.details.clear()
    def get_data(self):
        selected=self.source.currentData()
        if selected is None:
            raise ValueError("Chưa có Trace trong Smaart Data Bar")
        return source_arrays(self.engine,int(selected))
    def warning(self,exc):
        # V8.124: summary/details are hidden in the dock; keep every HOLD
        # reason in overlay.log so "nothing happened" can be diagnosed.
        print("V8124_TOOL_NOTICE",type(self).__name__,str(exc)[:200],flush=True)
        self.summary.setText("Chưa thể tính: " + str(exc))
        self.details.setPlainText(str(exc))
        preferred=None
        if type(self).__name__=="EQDialog":
            preferred=getattr(self.engine,"graph_mag",None)
        elif type(self).__name__=="FIRDialog":
            phase=getattr(self.engine,"graph_phase",None)
            mag=getattr(self.engine,"graph_mag",None)
            preferred=phase if phase is not None and phase.isVisible() else mag
        self.notice(str(exc),preferred)
    def notice(self,message,preferred=None):
        """Emit one Toast; prefer the Smaart plot so tool controls stay clear."""
        if preferred is not None:
            show_plot_notice(preferred,str(message))
        else:
            show_notice(self,str(message))
    def _saved_fs(self):
        # Bind Fs to the observer's actual source window when both editions
        # are running. Never select a config merely from global process order.
        observer=getattr(self.engine,'observer',None)
        hwnd=getattr(observer,'hwnd',0)
        if hwnd:
            from smaart8_api3_readonly_v868 import process_smaart_major
            from smaart_runtime_paths_v868 import saved_config
            edition=process_smaart_major(hwnd)
            if edition not in (8,9):return None
            path=saved_config(edition)
        else:
            from smaart_runtime_paths_v868 import running_major,saved_config
            # A read-only observer is already bound to one edition's trace
            # directory.  Use that provenance when both Smaart 8 and Suite
            # are running; global process discovery is intentionally
            # ambiguous in that case.
            folder=str(getattr(observer,'folder','')).replace('\\','/').lower()
            if '/smaart suite/' in folder:
                edition=9
            elif '/smaart v8/' in folder:
                edition=8
            else:
                edition=running_major()
            path=saved_config(edition) if edition in (8,9) else None
        cache=getattr(self.engine,"_saved_fs_cache",None)
        if cache is not None:return cache.get(path)
        # Standalone dialogs retain the historic synchronous/test hook.  The
        # production ToolHub always installs AsyncSavedFsCache above.
        try:
            return read_saved_smaart_fs(path) if path is not None else read_saved_smaart_fs()
        except TypeError:
            return read_saved_smaart_fs()  # legacy no-argument QA hook
    def after_open(self):
        self.refresh_sources()
        self.show()
        self.raise_()
        self.activateWindow()

class EQFinished(QObject):
    finished=pyqtSignal(int,object)

class EQDialog(TFDialog):
    native_ready=pyqtSignal(object,object,object,object,int,str)
    native_clear=pyqtSignal()
    native_enabled=pyqtSignal(bool)
    export_ready=pyqtSignal(bool)

    """Compact Auto EQ dialog: original RemiX algorithm, worker, stale gate."""
    def _verified_single(self):
        # V8.23 scanner must have accepted a FULL, unambiguous Data Bar scan.
        # A partial/failed scan may not authorize a new EQ computation.
        observer=getattr(self.engine,"observer",None)
        if observer is None:return None
        getter=getattr(observer,"current_single",None)
        return getter() if callable(getter) else None
    def refresh_sources(self):
        self._refresh_fs()
        token=self._verified_single()
        observer=getattr(self.engine,"observer",None)
        # Data Bar states come from the SAME UIA/PrintWindow full scan
        # as AutoPhase. Only accept a fully verified + fresh snapshot.
        complete=(observer is not None and getattr(observer,"ready",False) and
                  len(observer.order)>0 and
                  len(observer.states)==len(observer.order) and
                  all(v in ("on","off") for v in observer.states.values()) and
                  time.perf_counter()-getattr(observer,"single_scan_at",0.)<1.5)
        count=sum(v=="on" for v in observer.states.values()) if complete else None
        state=(token,count)
        if (state==getattr(self,"_eq_state",None) and self.source.count()
                and (token is None or self.source.currentData() is not None)):
            return
        # A saved preview may be temporarily suspended due to one failed
        # native scan. Restore the displayed selector after the *same*
        # immutable Trace has been independently reverified, without
        # clearing existing PEQ/MagEQ or the approved export token.
        previous=getattr(self,"_single_token",None)
        if (token is not None and token==previous and
                self.result is not None and
                self.source.count() and self.source.currentData() is None):
            self.source.blockSignals(True)
            self.source.clear()
            self.source.addItem(f"✔ {Path(token[0]).stem[:22]}",0)
            self.source.blockSignals(False)
            self._eq_state=state
            return
        # Transient native scan failure must SUSPEND display, not erase
        # the exact immutable EQ result. current_single()==None still
        # blocks both MagEq drawing and Export until reverified.
        previous=getattr(self,"_single_token",None)
        candidate=getattr(observer,"single_candidate",None)
        from mageq_presentation_gate_v853 import keep_preview_on_partial_scan
        if keep_preview_on_partial_scan(token,previous,candidate,count):
            # Keep computed EQ in memory but show an explicit unverified
            # selector during an incomplete scan (export still blocked).
            if candidate is None and count is None and self.source.count():
                self.source.blockSignals(True)
                self.source.clear()
                self.source.addItem("Chờ đúng 1 Trace được tick",None)
                self.source.blockSignals(False)
            return
        self._eq_state=state
        self._single_token=token
        self.source.blockSignals(True)
        self.source.clear()
        recognition=trace_recognition_text(observer,token,count)
        if token is None:
            if count is not None and count!=1:
                label=f"Đang bật {count} Trace — Auto EQ cần đúng 1"
            else:
                label="Chờ đúng 1 Trace được tick"
            self.source.addItem(recognition,None)
            self.source.setToolTip("Auto EQ: tick đúng một Trace trong Smaart Data Bar")
        else:
            stem=Path(token[0]).stem
            self.source.addItem("✓ "+_middle_elide(recognition,28),0)
            self.source.setToolTip("Auto EQ: chỉ Trace đang được tick: "+stem)
        # Source selector is display-only. Do NOT allow manual T1/T2/SUM.
        self.source.setEnabled(False)
        self.source.blockSignals(False)
        self.invalidate()
    def get_data(self):
        token=self._verified_single()
        if token is None or token!=getattr(self,"_single_token",None):
            raise ValueError("Auto EQ yêu cầu đúng 1 Trace đang được tick, đã xác minh")
        path=Path(token[0])
        before=path.stat()
        if (before.st_mtime_ns,before.st_size)!=(token[1],token[2]):
            raise ValueError("Trace đã thay đổi sau khi đọc tick; chọn lại Trace")
        trace=read_trf(str(path))
        after=path.stat()
        if ((after.st_mtime_ns,after.st_size)!=(token[1],token[2]) or
            self._verified_single()!=token):
            raise ValueError("Tick hoặc dữ liệu Trace thay đổi khi đọc")
        return (trace.hz.copy(),trace.h.copy(),trace.coherence.copy(),trace.path.stem)
    def __init__(self,engine):
        super().__init__(engine,"Auto EQ")
        self.plot.hide()  # corrected Mag is on Smaart, NOT inside this dialog

        self._serial=0
        self._pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,thread_name_prefix="remix_autoeq")
        self._bus=EQFinished()
        self._bus.finished.connect(self._finish)
        self._export_dialog=None
        self._export_snapshot=None
        self._export_source_token=None
        self._export_file_sha=None
        self._native_guard=None
        # V8.180 R3: wait for a FRESH independent native Mag proof on Export.
        # Do NOT extend the 450-ms frame TTL or bypass source/tick/SHA checks.
        self._export_recheck_timer=QTimer(self)
        self._export_recheck_timer.setInterval(90)
        self._export_recheck_timer.timeout.connect(self._poll_export_recheck)
        self._export_recheck_context=None
        self.note.setText("AUTO EQ: d\u00f9ng \u0111\u00fang 1 Trace \u0111\u01b0\u1ee3c tick | MagEq + PEQ | kh\u00f4ng ghi DSP")

        self.target=QComboBox()
        # Vietnamese display labels; immutable internal solver IDs remain
        # Flat/House/Tilt. Never send the translated text to DSP math.
        for label,target_id in (
            ("Phẳng", "Flat"),
            ("House (Trầm ấm)", "House"),
            ("Nghiêng", "Tilt"),
        ):
            self.target.addItem(label,target_id)
        self.target.setAccessibleName("Chọn chế độ EQ")
        self.target.currentIndexChanged.connect(self.invalidate)
        self.main.insertWidget(3,self.target)

        self.fs=QComboBox()
        self.fs.setEnabled(False)  # Always read-only, never manual selection.
        self.fs.setToolTip("Fs từ SmaartConfig.xml đã lưu; không mở soundcard")
        self._fs_snapshot=None
        self._fs_checked_at=0.
        self.fs.addItem("Fs: chờ Smaart...",None)
        self.main.insertWidget(4,self.fs)

        # Internal scalar controls preserve validated solver arguments but
        # are NOT in the visible panel. Native Smaart dashed lines own LF/HF.
        self.lf=QDoubleSpinBox(self)
        self.lf.setRange(20,18000)
        self.lf.setDecimals(1)
        self.lf.setValue(60)
        self.lf.hide()
        self.hf=QDoubleSpinBox(self)
        self.hf.setRange(100,20000)
        self.hf.setDecimals(1)
        self.hf.setValue(8000)
        self.hf.hide()
        self.roi_range_changed=None
        self.roi_status=QLabel("K\u00e9o hai v\u1ea1ch LF / HF tr\u00ean Magnitude")
        self.roi_status.setToolTip("K\u00e9o hai v\u1ea1ch -- tr\u00ean Magnitude Smaart \u0111\u1ec3 ch\u1ecdn d\u1ea3i Auto EQ")
        self.roi_status.setWordWrap(True)
        self.main.insertWidget(5,self.roi_status)

        self.filter_count=QSpinBox()
        self.filter_count.setRange(0,12)
        self.filter_count.setValue(0)
        self.filter_count.setSpecialValueText("AUTO")
        self.filter_count.setPrefix("Số PEQ tối đa ")
        self.filter_count.setToolTip("AUTO thử ngân sách PEQ gọn/vừa/tối đa và chọn số ít nhất gần đáp tuyến phẳng nhất; vẫn có thể chọn tay 1–12")
        self.main.insertWidget(6,self.filter_count)

        self.boost=QDoubleSpinBox()
        self.boost.setRange(0,6)
        self.boost.setValue(0)
        self.boost.setSpecialValueText("AUTO")
        self.boost.setPrefix("Boost +")
        self.boost.setSuffix(" dB")
        self.boost.setEnabled(True)
        self.boost.setToolTip("AUTO mặc định; thay đổi Boost/Cut để dùng giới hạn tay. Đặt Boost 0 và Cut -12 để về AUTO")
        self.main.insertWidget(7,self.boost)

        self.cut=QDoubleSpinBox()
        self.cut.setRange(-12,-.1)
        self.cut.setValue(-12)
        self.cut.setSpecialValueText("AUTO")
        self.cut.setPrefix("Cut ")
        self.cut.setSuffix(" dB")
        self.cut.setEnabled(True)
        self.cut.setToolTip("AUTO mặc định; thay đổi Boost/Cut để dùng giới hạn tay. Đặt Boost 0 và Cut -12 để về AUTO")
        self.main.insertWidget(8,self.cut)
        for ctrl in (self.lf,self.hf):
            ctrl.valueChanged.connect(self._roi_changed)
        self._limits_manual=False
        self.filter_count.valueChanged.connect(self.invalidate)
        for ctrl in (self.boost,self.cut):
            ctrl.valueChanged.connect(self._limit_changed)
        self._roi_changed()

        buttons=QHBoxLayout()
        self.calculate=QPushButton("AUTO EQ")
        self.calculate.setObjectName("run")
        self.calculate.clicked.connect(self.compute)
        self.export=QPushButton("Xuất EQ")
        self.export.setToolTip("Xem bảng EQ# / Hz / dB / Q và lưu TXT hoặc PNG")
        self.export.clicked.connect(self.export_eq)
        self.export.setEnabled(False)
        buttons.addWidget(self.calculate,2)
        buttons.addWidget(self.export,1)
        self.main.addLayout(buttons)
        self._action_row=buttons  # V8.56: same live controls, new visual order.
        self.mageq_toggle=QCheckBox("Hiện MagEq trên Mag Smaart")
        self.mageq_toggle.setChecked(True)
        self.mageq_toggle.setToolTip(
            "Bật/tắt duy nhất line MagEq. Đường Mag gốc Smaart luôn giữ nguyên.")
        self.mageq_toggle.toggled.connect(self.native_enabled.emit)
        self.main.addWidget(self.mageq_toggle)
        self.native_state=QLabel("MagEQ HOLD: Cho native pixel/Y")
        self.native_state.setObjectName("hint")
        self.native_state.setWordWrap(True)
        self.main.addWidget(self.native_state)
        self._refresh_fs(force=True)
        self.setFixedHeight(520)

    def _limit_changed(self,*_):
        self._limits_manual=not (self.boost.value()==0. and self.cut.value()==-12.)
        self.invalidate()

    def _roi_changed(self,*_):
        lf,hf=float(self.lf.value()),float(self.hf.value())
        if hasattr(self,"roi_status"):
            self.roi_status.setText(
                f"V\u00d9NG AUTO EQ  {lf:.0f} Hz \u2014 {hf/1000:.2f} kHz"
                if hf>=1000 else f"V\u00d9NG AUTO EQ  {lf:.0f} \u2014 {hf:.0f} Hz")
        callback=getattr(self,"roi_range_changed",None)
        if callable(callback):
            callback(lf,hf)
        self.invalidate()

    def drag_roi_to(self,kind,frequency):
        # Reuse the native Auto Phase ROI boundary policy; never cross lines.
        from roi_markers_v73 import bound_drag
        lf,hf=float(self.lf.value()),float(self.hf.value())
        if kind=="LF":
            target=self.lf
        elif kind=="HF":
            target=self.hf
        else:
            raise ValueError("Unknown Auto EQ ROI marker")
        hz=round(bound_drag(kind,frequency,lf,hf),1)
        if abs(target.value()-hz)>=.05:
            target.setValue(hz)

    def _refresh_fs(self,*,force=False):
        # TFDialog.__init__ calls refresh_sources before EQ controls exist.
        if not hasattr(self,"_fs_checked_at"):
            return
        now=time.perf_counter()
        if not force and now-self._fs_checked_at<1.0:
            return
        self._fs_checked_at=now
        snap=self._saved_fs()
        if snap==self._fs_snapshot:
            return
        # A saved Fs change makes every existing EQ result invalid.
        old=self._fs_snapshot
        self._fs_snapshot=snap
        if snap is None:
            label="Fs: chưa xác minh Smaart"
            value=None
        else:
            label=f"Fs {snap.hz/1000:g} kHz • Smaart"
            value=snap.hz
        self.fs.blockSignals(True)
        self.fs.clear()
        self.fs.addItem(label,value)
        self.fs.setCurrentIndex(0)
        self.fs.blockSignals(False)
        self.fs.setToolTip(
            "Fs đọc từ SmaartConfig.xml đã lưu; chưa theo dõi thay đổi chưa lưu"
            if snap else "Smaart sample rate chưa xác minh; AUTO EQ tạm dừng")
        if old is not None:
            self.invalidate()

    def invalidate(self,*_):
        if hasattr(self,"_serial"):self._serial+=1
        if hasattr(self,"_export_recheck_timer"):self._export_recheck_timer.stop()
        self._export_recheck_context=None
        super().invalidate()
        self.native_clear.emit()
        self._export_snapshot=None
        self._export_source_token=None
        self._export_file_sha=None
        self._peq_drag=None
        if getattr(self,"_export_dialog",None) is not None:
            self._export_dialog.close()
            self._export_dialog=None
        if hasattr(self,"export"):self.export.setEnabled(False)
        self.export_ready.emit(False)
        if hasattr(self,"calculate"):self.calculate.setEnabled(True)
        self._dsp_ready_at=None
        self._dsp_ready_ticket=None
        if hasattr(self,"native_state"):
            self.native_state.setText("DSP: chưa có kết quả | Native: chưa xác minh")

    def _native_export_ok(self,check_sha=False):
        """Export only when selected TRF AND current native Mag pixels match."""
        guard=getattr(self,"_native_guard",None)
        token=getattr(self,"_export_source_token",None)
        if (guard is None or not token or self._export_snapshot is None or
                self.result is None or self._verified_single()!=token or
                getattr(guard,"frame",None) is None or
                getattr(guard,"source",None) is None):
            return False
        src,frame=guard.source,guard.frame
        if (guard.approved_token!=token or
                src.source_name!=Path(token[0]).stem or
                not frame.identity_verified or
                frame.source_identity!=src.source_identity or
                frame.revision!=src.revision or
                not guard._source_binding_ok()):
            return False
        from native_eq_mag_v06 import frame_is_fresh_for_window
        if not frame_is_fresh_for_window(frame,frame.hwnd):
            return False
        if not self._fs_snapshot or self._fs_snapshot!=self._saved_fs():
            return False
        try:
            path=Path(token[0])
            stat=path.stat()
            if (stat.st_mtime_ns,stat.st_size)!=(token[1],token[2]):
                return False
            if check_sha and hashlib.sha256(path.read_bytes()).hexdigest()!=self._export_file_sha:
                return False
        except OSError:
            return False
        return True

    def _export_hold_reason_v8160(self):
        """QA diagnostics ONLY; never authorizes EQ export."""
        guard=getattr(self,"_native_guard",None)
        token=getattr(self,"_export_source_token",None)
        if guard is None:return "native_guard_missing"
        if token is None:return "approved_trace_missing"
        if self._export_snapshot is None or self.result is None:return "eq_preview_missing"
        if self._verified_single()!=token:return "single_tick_3of3_not_current"
        src,frame=getattr(guard,"source",None),getattr(guard,"frame",None)
        if src is None:return "native_source_missing"
        if frame is None:
            return ("native_frame_missing:"+str(getattr(guard,"last_native_drop",""))[:70]
                    +":future="+str(guard.future is not None))
        if guard.approved_token!=token:return "native_approved_token_mismatch"
        if src.source_name!=Path(token[0]).stem:return "native_source_name_mismatch"
        if not frame.identity_verified:return "native_pixels_unverified"
        if frame.source_identity!=src.source_identity:return "source_identity_mismatch"
        if frame.revision!=src.revision:return "native_revision_mismatch"
        if not guard._source_binding_ok():return "native_source_binding_failed"
        from native_eq_mag_v06 import frame_is_fresh_for_window
        if not frame_is_fresh_for_window(frame,frame.hwnd):
            return "native_frame_expired_or_viewport_changed"
        if not self._fs_snapshot or self._fs_snapshot!=self._saved_fs():
            return "saved_fs_mismatch"
        try:
            stat=Path(token[0]).stat()
            if (stat.st_mtime_ns,stat.st_size)!=(token[1],token[2]):
                return "source_file_metadata_changed"
        except OSError:return "source_file_missing"
        return "native_verified_and_file_current"

    def _refresh_export_gate(self):
        # Strict authorization remains entirely in _native_export_ok().
        ready=self._native_export_ok()
        if os.environ.get("REMIX_QA_TRACE_EQ_GATE")=="1":
            now=time.perf_counter()
            last=getattr(self,"_qa_last_export_log_at",0.)
            reason="READY" if ready else self._export_hold_reason_v8160()
            if (reason!=getattr(self,"_qa_last_export_reason",None) or
                    now-last>3.0):
                self._qa_last_export_reason=reason
                self._qa_last_export_log_at=now
                observer=getattr(self.engine,"observer",None)
                age=(now-getattr(observer,"single_verified_at",0.)
                     if observer is not None else -1.)
                print("V8160_EQ_EXPORT_GATE",reason,
                      "tick_age_ms",round(age*1000) if 0<=age<100 else -1,
                      "tick_stable",getattr(observer,"single_stable",-1),
                      "native_frame",bool(getattr(getattr(self,"_native_guard",None),"frame",None)),
                      flush=True)
        can_attempt=(self._recheck_preconditions() is not None)
        can_click=bool(ready or can_attempt)
        if self.export.isEnabled()!=can_click:
            self.export.setEnabled(can_click)
        # Other modules must still see the strict 3/3+pixel authorization.
        if ready!=getattr(self,"_last_strict_export_ready",None):
            self._last_strict_export_ready=ready
            self.export_ready.emit(ready)

    def _parameters(self):
        self._refresh_fs(force=True)
        snap=self._saved_fs()
        if snap is None or snap!=self._fs_snapshot or snap.hz!=self.fs.currentData():
            raise ValueError("Không xác minh được Fs đã lưu của Smaart; không tính Auto EQ")
        self._fs_token=snap
        manual=bool(self._limits_manual)
        return {"fs":int(snap.hz),"target":self.target.currentData(),
                "filters":int(self.filter_count.value()),
                "lf":float(self.lf.value()),"hf":float(self.hf.value()),
                "boost":float(self.boost.value()) if manual else None,
                "cut":float(self.cut.value()) if manual else None}

    def compute(self):
        try:
            f,h,c,source=self.get_data()
            args=self._parameters()
        except Exception as exc:
            self.warning(exc)
            return
        self.invalidate()
        self._serial+=1
        ticket=self._serial
        token=self._verified_single()
        try:
            source_sha=hashlib.sha256(Path(token[0]).read_bytes()).hexdigest()
        except (OSError,TypeError,IndexError):
            return self.warning("Cannot verify source TRF")
        self._pending_native=(
            ticket,0,f.copy(),h.copy(),c.copy(),
            tuple(id(t) for t in (self.engine.current_traces or ())),source,
            token,self._fs_token,source_sha)

        self.calculate.setEnabled(False)
        self.summary.setText("RemiX AEQ đang tính (worker)...")
        future=self._pool.submit(design_remix_eq,f,h,c,source=source,**args)
        schedule_auto_wait_notice(
            self,lambda t=ticket:t==self._serial and not self.calculate.isEnabled(),
            getattr(self.engine,"graph_mag",None))
        future.add_done_callback(lambda done,t=ticket:
                                 self._bus.finished.emit(t,done))

    @staticmethod
    def _pending_sha_ok(pending):
        try:
            return hashlib.sha256(Path(pending[7][0]).read_bytes()).hexdigest()==pending[9]
        except (OSError,TypeError,IndexError):
            return False

    def _finish(self,ticket,future):
        if ticket!=self._serial:return
        self.calculate.setEnabled(True)
        try:
            r=future.result()
        except Exception as exc:
            print("V8136_AUTOEQ_ERROR_RAW",repr(exc),flush=True)
            self.warning(autoeq_error_vn(exc))
            return
        pending=getattr(self,"_pending_native",None)
        from mageq_presentation_gate_v853 import token_still_current
        rearming=(pending is not None and self._verified_single() is None and
                  token_still_current(getattr(self.engine,"observer",None),pending[7]))
        if (pending is None or pending[0]!=ticket or
                # V8.156: completion is bound to immutable TRF token + SHA,
                # not the 2-trace SUM/overlay object IDs. The latter can
                # refresh or disappear while this independent worker runs.
                (self.source.currentData()!=pending[1] and not
                 (rearming and self.source.currentData() is None)) or
                (self._verified_single()!=pending[7] and not rearming) or
                self._saved_fs()!=pending[8] or
                not self._pending_sha_ok(pending)):
            self.native_clear.emit()
            self.summary.setText("Trace hoặc Fs Smaart đã thay đổi: bỏ Auto EQ cũ")
            return
        # Distinguish completed static DSP from independent native-pixel proof.
        # This status is NEVER a permission to export or to paint over Smaart.
        self._dsp_ready_at=time.perf_counter()
        self._dsp_ready_ticket=ticket
        if hasattr(self,"native_state"):
            self.native_state.setText(
                "DSP READY: tính xong; đang xác minh Mag native (Export HOLD)")
        self.result=r
        print("R55_EQ_DSP_READY",ticket,round(self._dsp_ready_at,6),
              getattr(r,"status",None),len(getattr(r,"peqs",())),flush=True)
        if getattr(r,"limits_auto",False):
            for control in (self.boost,self.cut):
                control.blockSignals(True)
                control.setSpecialValueText("")
            self.boost.setValue(float(r.boost_limit_db))
            self.cut.setValue(float(r.cut_limit_db))
            self.boost.blockSignals(False)
            self.cut.blockSignals(False)
        can_draw=((r.status=="PREVIEW_READY" and bool(r.peqs)) or
                  (r.status=="NO_EQ_NEEDED" and not r.peqs))
        if can_draw:
            self._export_source_token=pending[7]
            self._export_file_sha=pending[9]
        # Never put the corrected Mag in a small right-panel graph.
        # It belongs to the Smaart native Magnitude overlay.
        if can_draw and pending[1] in (0,1):
            self.native_ready.emit(pending[2],pending[3],pending[4],
                                   r,pending[1],pending[6])
        else:
            self.native_clear.emit()

        display_state=("BYPASS 0 PEQ: MagEq = Mag goc"
                       if r.status=="NO_EQ_NEEDED" and not r.peqs
                       else f"{r.status} / {len(r.peqs)} PEQ")
        self.summary.setText(
            f"MagEq [{r.source}] / {display_state} | "
            f"WRMS {r.rms_before:.2f} -> {r.rms_after:.2f} dB"+
            (f" | Auto PEQ ≤{r.filter_limit}"
             if getattr(r,"filters_auto",False) else "")+
            (f" | Auto +{r.boost_limit_db:.1f}/{r.cut_limit_db:.1f} dB"
             if getattr(r,"limits_auto",False) else ""))
        lines=[f"Mag gốc: {r.source} (không thay đổi)",
               f"MagEq: đường mới trên Mag Smaart / {r.fs} Hz",
               "RemiX AEQ-U1.2 / preview / không ghi DSP",
               (f"Số PEQ tự chọn: tối đa {r.filter_limit}, thực tạo {len(r.peqs)}"
                if getattr(r,"filters_auto",False)
                else f"Số PEQ thủ công: tối đa {self.filter_count.value()}"),
               (f"Giới hạn tự chọn: Nâng +{r.boost_limit_db:.1f} dB / "
                f"Cắt {r.cut_limit_db:.1f} dB" if getattr(r,"limits_auto",False)
                else "Giới hạn thủ công/legacy"),
               "Hz       Gain     Q"]
        lines += [f"{q.freq_hz:7.1f}  {q.gain_db:+6.2f}   {q.q:.2f}"
                  for q in r.peqs]
        if r.status=="NO_EQ_NEEDED" and not r.peqs:
            lines.append("BYPASS: 0 PEQ, MagEq TRUNG Mag goc; khong co hieu chinh.")
            lines.append("Overlay chi hien neu original Mag khop pixel Smaart.")
            lines.append("Xuat EQ khoa: khong co PEQ de xuat.")
        elif not r.peqs:
            lines.append("Khong co PEQ duoc phe duyet (fail-closed)")
        if r.warnings:lines.extend(r.warnings[:3])
        self.details.setPlainText("\n".join(lines))
        if r.status=="PREVIEW_READY" and r.peqs:
            try:
                self._export_snapshot=EQExportSnapshot.from_result(r,self.target.currentData())
            except ValueError as exc:
                self._export_snapshot=None
                self.details.append("Chưa thể xuất EQ: "+str(exc))
        else:
            self._export_snapshot=None
        if r.status!="NO_EQ_NEEDED" and not r.peqs:
            message=autoeq_error_vn("NO_APPROVED_PEQ")
            print("V8136_AUTOEQ_NO_PEQ",message,flush=True)
            self.notice(message,getattr(self.engine,"graph_mag",None))
        self._refresh_export_gate()  # HOLD until independent native match.

    def drag_peq_marker(self,number,global_x,global_y,phase):
        """Edit Hz and Gain in the ONE approved live Smaart MagEq preview.

        Q stays unchanged; original TRF/source, sample rate, native
        verified identity and preview-only/no-DSP semantics are preserved.
        """
        from dataclasses import replace
        from peq_marker_drag_v851 import bounded_marker_change,preview_after_drag
        from engines.remix_autoeq_unified import (
            AutoEQInput,AutoEQProfile,prepare_analysis_curves)
        from native_eq_mag_v06 import build_state,frame_is_fresh_for_window
        import numpy as np
        guard=getattr(self,"_native_guard",None)
        if guard is None:return False
        if phase=="start":
            self._peq_drag=None
            if not self._native_export_ok(check_sha=True):return False
            if not (self.engine.graph_mag.isVisible() and
                    guard.frame is not None and guard.source is not None and
                    guard.frame.identity_verified and
                    guard.frame.source_identity==guard.source.source_identity and
                    frame_is_fresh_for_window(guard.frame,guard.frame.hwnd) and
                    guard.frame is self.engine.graph_mag.mageq_frame and
                    self.result and self.result.status=="PREVIEW_READY" and
                    1<=number<=len(self.result.peqs)):
                return False
            pending=getattr(self,"_pending_native",None)
            if pending is None or self._verified_single()!=pending[7]:
                return False
            freqs,tf,coh=pending[2:5]
            lf,hf=float(self.lf.value()),float(self.hf.value())
            # V8.135: coherence is reference-only for Auto EQ, including
            # interactive PEQ edits. Keep the drag analysis identical to the
            # proposal path by using every real TF bin and neutral confidence.
            good=(freqs>=lf)&(freqs<=hf)&(np.abs(tf)>1e-12)
            if good.sum()<24:return False
            level=float(np.median(20*np.log10(np.maximum(
                np.abs(tf[good]),1e-15))))
            from remix_autoeq_v05_adapter import target_anchors
            tf_f,tf_g=target_anchors(self.target.currentData(),lf,hf)
            inp=AutoEQInput(freqs,tf*10**(-level/20),np.ones_like(coh),
                 "coherence",float(self.result.fs),"stored_tf",
                 tf_f,tf_g,6.)
            profile=AutoEQProfile(f_min_hz=lf,f_max_hz=hf,
                 max_filters=int(getattr(self.result,"filter_limit",0) or
                                 self.filter_count.value()),
                 max_peq=int(getattr(self.result,"filter_limit",0) or
                             self.filter_count.value()),
                 max_boost_db=float(self.boost.value()),
                 max_cut_db=float(self.cut.value()))
            analysis=prepare_analysis_curves(inp,profile)
            if not np.allclose(analysis.grid_hz,self.result.hz,
                               rtol=1e-9,atol=1e-7):
                return False
            self._peq_drag=dict(original=self.result,
                index=number-1,press_y=float(global_y),
                press_gain=self.result.peqs[number-1].gain_db,
                weights=analysis.weights.copy(),
                source_revision=guard.source.revision,
                source_identity=guard.source.source_identity)
            self._export_snapshot=None
            self.export.setEnabled(False)
            return True
        info=getattr(self,"_peq_drag",None)
        if info is None or info["index"]!=number-1:return False
        source=guard.source;frame=guard.frame
        if (source is None or frame is None or
                source.source_identity!=info["source_identity"] or
                source.revision!=info["source_revision"] or
                not guard._source_binding_ok() or
                not frame_is_fresh_for_window(frame,frame.hwnd) or
                not self.engine.graph_mag.isVisible()):
            if phase=="end":self._peq_drag=None
            return False
        try:
            peqs=bounded_marker_change(
                info["original"].peqs,info["index"],
                global_x,global_y,frame.plot,
                info["press_y"],info["press_gain"],
                float(frame.fit.px_per_db),
                float(self.lf.value()),float(self.hf.value()),
                float(self.cut.value()),float(self.boost.value()))
            updated=preview_after_drag(info["original"],peqs,info["weights"])
            pending=self._pending_native
            new_source=build_state(pending[2],pending[3],pending[4],
                 updated.peqs,fs=updated.fs,source_index=pending[1],
                 source_name=pending[6],revision=source.revision)
            if new_source.source_identity!=source.source_identity:
                raise ValueError("Edited EQ changed original source identity")
        except (ValueError,TypeError,IndexError) as exc:
            if os.environ.get("REMIX_QA_TRACE_PEQ_DRAG")=="1":
                print("PEQ_DRAG_REJECT",repr(exc),flush=True)
            if phase=="end":self._peq_drag=None
            return False
        self.result=updated
        guard.source=new_source
        self.engine.graph_mag.set_mageq(new_source,frame)
        self.summary.setText(
            f"MagEq [{updated.source}] / MANUAL PEQ "
            f"{number}: {peqs[number-1].freq_hz:.1f} Hz, "
            f"{peqs[number-1].gain_db:+.2f} dB, Q {peqs[number-1].q:.2f} | "
            f"WRMS {updated.rms_before:.2f} -> {updated.rms_after:.2f} dB")
        self.details.setPlainText("PEQ edited on Smaart | Preview only | "
            "No DSP write\nHz          Gain       Q\n"+
            "\n".join(f"EQ{i} {b.freq_hz:.1f}  {b.gain_db:+.2f}  {b.q:.2f}"
                  for i,b in enumerate(updated.peqs,1)))
        if phase=="end":
            self._peq_drag=None
            # Only allow export after release, and only with reverified
            # source+viewport+TRF SHA (no partial-drag export).
            try:
                self._export_snapshot=EQExportSnapshot.from_result(
                    updated,self.target.currentData())
            except ValueError:self._export_snapshot=None
            self._refresh_export_gate()
        return True

    def _open_verified_export_eq(self):
        """Called only after a strict on-click native/SHA/trace proof."""
        if not self._native_export_ok(check_sha=True):
            return self.warning("Export HOLD: native Mag proof invalidated")
        if self.result is None or self._export_snapshot is None:
            return self.warning("Hãy tính AUTO EQ thành công trước khi xuất EQ")
        if self._export_dialog is not None:
            self._export_dialog.close()
        self._export_dialog=EQExportDialog(self._export_snapshot,self)
        self._export_dialog.show()
        self._export_dialog.raise_()

    def _stop_export_recheck(self):
        if hasattr(self,"_export_recheck_timer"):
            self._export_recheck_timer.stop()
        self._export_recheck_context=None

    def _export_retry_tick_state(self,token):
        """Return verified/rearming/invalid; rearming NEVER authorizes export.

        Only the same immutable Data Bar candidate can bridge one incomplete
        scanner pass. Explicit 0/2+ ticks, another verified trace, an unknown
        row mapping or a reset scanner end the wait immediately.
        """
        current=self._verified_single()
        if current==token:
            return "verified"
        if current is not None:
            return "invalid"
        observer=getattr(self.engine,"observer",None)
        if observer is None or not getattr(observer,"ready",False):
            return "invalid"
        if getattr(observer,"single_candidate",None)!=tuple(token[:3]):
            return "invalid"
        order=getattr(observer,"order",())
        states=getattr(observer,"states",{})
        if (not order or len(states)!=len(order)
                or any(v not in ("on","off","unknown")
                       for v in states.values())):
            return "invalid"
        known_on=sum(v=="on" for v in states.values())
        if known_on>1:
            return "invalid"
        # A complete 0/2+ tick observation is an actual selection change.
        if (all(v in ("on","off") for v in states.values())
                and known_on!=1):
            return "invalid"
        return "rearming"

    def _recheck_preconditions(self,*,check_sha=False,expected_sha=None):
        """Gate a bounded attempt, not export; metadata-only during polling.

        SHA is computed ONCE on click (and once on final export commit).
        90-ms polls must never read/hash the whole TRF.
        """
        token=getattr(self,"_export_source_token",None)
        guard=getattr(self,"_native_guard",None)
        if (not token or guard is None or guard.source is None
                or self.result is None or self._export_snapshot is None
                or getattr(guard,"approved_token",None)!=token
                or guard.source.source_name!=Path(token[0]).stem
                or not self._fs_snapshot
                or self._fs_snapshot!=self._saved_fs()):
            return None
        tick=self._export_retry_tick_state(token)
        if tick=="invalid":
            return None
        # Only a currently verified tick can pass the original strict binder.
        if tick=="verified" and not guard._source_binding_ok():
            return None
        # An already verified native pixel witness is mandatory even to
        # offer a retry. A calculated EQ plan alone is NEVER enough.
        frame=(getattr(guard,"frame",None) or
               getattr(guard,"_last_verified_frame",None))
        if frame is None:
            return None
        if (not frame.identity_verified or
                frame.source_identity!=guard.source.source_identity or
                frame.revision!=guard.source.revision):
            return None
        try:
            if (not win32gui.IsWindow(frame.hwnd)
                    or win32gui.IsIconic(frame.hwnd)
                    or tuple(win32gui.GetWindowRect(frame.hwnd))!=frame.window_rect):
                return None
        except (OSError,TypeError,ValueError):
            return None
        try:
            path=Path(token[0])
            before=path.stat()
            if (before.st_mtime_ns,before.st_size)!=(token[1],token[2]):
                return None
            sha=expected_sha
            if check_sha:
                sha=hashlib.sha256(path.read_bytes()).hexdigest()
                after=path.stat()
                if (after.st_mtime_ns,after.st_size)!=(token[1],token[2]):
                    return None
                if sha!=self._export_file_sha:
                    return None
            elif sha is not None and sha!=self._export_file_sha:
                return None
        except (OSError,TypeError,ValueError,IndexError):
            return None
        return (token,int(self._serial),sha,tick)

    def _poll_export_recheck(self):
        context=getattr(self,"_export_recheck_context",None)
        if context is None:
            self._stop_export_recheck()
            return
        token,serial,sha,started=context
        current=self._recheck_preconditions(expected_sha=sha)
        if (current is None or current[:3]!=(token,serial,sha)):
            self._stop_export_recheck()
            return self.warning("Export HOLD: Trace, Fs, Mag viewport or source proof changed")
        tick=current[3]
        elapsed=time.monotonic()-started
        if tick=="rearming" and elapsed>=1.5:
            self._stop_export_recheck()
            return self.warning("Export HOLD: Data Bar 3/3 did not reverify in 1.5 s")
        # Strict 3/3 + strict 450-ms native frame ONLY. SHA is already
        # locked for the attempt; final commit re-hashes the source once.
        if tick=="verified" and self._native_export_ok(check_sha=False):
            self._stop_export_recheck()
            return self._open_verified_export_eq()
        if elapsed>=3.5:
            reason=self._export_hold_reason_v8160()
            self._stop_export_recheck()
            return self.warning("Export HOLD: Native Mag verification timed out ("+reason[:70]+")")
        # The observer's own timer handles 3/3; this requests only a new
        # independent pixel fit, NEVER substitutes a candidate for a tick.
        if tick=="verified":
            guard=getattr(self,"_native_guard",None)
            if guard is not None:
                guard.tick()

    def export_eq(self):
        """Click-to-reverify: tolerate async latency, never stale pixel proof."""
        if os.environ.get("REMIX_QA_DIAG_EQ_EXPORT")=="1":
            import json as _diag_json
            _g=getattr(self,"_native_guard",None)
            _f=getattr(_g,"frame",None)
            _data={
                "reason":self._export_hold_reason_v8160(),
                "frame_age_ms":round(1000*(time.monotonic()-_f.created),1) if _f is not None else None,
                "frame_exists":_f is not None,
                "future_pending":bool(getattr(_g,"future",None) is not None),
                "native_drop":str(getattr(_g,"last_native_drop","")),
                "token_current":self._verified_single()==getattr(self,"_export_source_token",None),
            }
            print("QA_EQ_EXPORT_PRECISE",_diag_json.dumps(_data),flush=True)
        if self._native_export_ok(check_sha=True):
            self._stop_export_recheck()
            return self._open_verified_export_eq()
        reason=self._export_hold_reason_v8160()
        transient=(reason=="single_tick_3of3_not_current"
                   or reason=="native_frame_expired_or_viewport_changed"
                   or reason.startswith("native_frame_missing:"))
        context=(self._recheck_preconditions(check_sha=True)
                 if transient else None)
        if context is None:
            self._refresh_export_gate()
            return self.warning("Export HOLD: source or Mag viewport not verified ("+reason[:65]+")")
        self._stop_export_recheck()
        self._export_recheck_context=(*context[:3],time.monotonic())
        self._export_recheck_timer.start()
        self.notice("Đang xác minh lại Magnitude trước khi xuất EQ...",
                    getattr(self.engine,"graph_mag",None))
        # Data Bar and Mag workers reverify separately. No DSP writes.
        self._poll_export_recheck()

    def closeEvent(self,event):
        self._stop_export_recheck()
        if not getattr(self,"_really_close",False):
            # Close button hides dialog; reopening via Hub must still work.
            self.hide()
            event.ignore()
            return
        self._serial+=1
        if self._export_dialog is not None:
            self._export_dialog.close()
            self._export_dialog=None
        from worker_lifecycle_v8142 import bounded_shutdown
        bounded_shutdown(self._pool)
        super().closeEvent(event)
def _fir_design_and_preview(freq,h,coh,taps,fs,name,digest,revision,lf=30,hf=16000,
                            mode="mag",phase_plus=False,phase_oct=None):
    # FIR and complex source model live in the SAME worker/version.
    # V8.125 (user): always create the FIR; quality/safety gates become
    # warnings carried on the result instead of HOLD.
    # V8.134: build the display model at Smaart's own Phase smoothing.
    if phase_oct is None:
        phase_oct=1/6
        try:
            from smaart_smooth_sync_v811 import read_saved_smooth
            saved=read_saved_smooth()
            if saved is not None and saved.phase_verified:
                phase_oct=saved.phase_oct
        except Exception:
            pass
    def design(count):
        from remix_duo.core.fir_quality_gate import evaluate_fir_quality
        if mode=="phase":
            # Fast physical-coverage preflight avoids designing a kernel that
            # cannot affect even half an octave inside the requested ROI.
            # This is tap physics, independent of measurement coherence.
            phase_lf=max(float(lf),12.*fs/float(count))
            if phase_lf>=hf or (np.log2(hf/phase_lf)<.5):
                raise ValueError(
                    f"FIR Phase {count} taps chỉ sửa từ {phase_lf:.0f} Hz; "
                    "không đủ 0.5 octave trong LF–HF")
            # Require adequate measured phase evidence before authorizing a
            # physical Phase FIR. Design remains coherence-independent, but
            # low-confidence data never grants export/DSP permission.
            f=np.asarray(freq,float);c=np.asarray(coh,float)
            mid=np.sqrt(float(lf)*float(hf))
            for lower,upper,section in ((lf,hf,"TOTAL"),
                                        (lf,mid,"LF"),(mid,hf,"HF")):
                roi=(f>=lower)&(f<=upper)
                good=roi&np.isfinite(c)&(c>=.65)
                if (int(good.sum())<25 or not np.any(roi) or
                        float(good.sum()/roi.sum())<.65):
                    raise ValueError(
                        f"FIR Phase {section} HOLD: coherence≥0.65 "
                        f"chỉ {good.sum()}/{roi.sum()} bins")
            failures=[]
            for strength in (1.,.75,.5,.25):
                result=design_phase_only_fir(
                    freq,h,coh,taps=count,fs=fs,source=name,lf=lf,hf=hf,
                    phase_plus=phase_plus,strict=False,
                    correction_strength=strength)
                if phase_plus and any("Phase+ không đạt" in str(w)
                                      for w in result.warnings):
                    failures.append(f"{strength:.0%}: Phase+ fallback")
                    continue
                preview=make_source(
                    freq,h,coh,result.taps,fs,name,digest,revision,lf,hf,
                    mode,phase_smooth_oct=phase_oct)
                verdict=evaluate_fir_quality(preview,result,lf,hf)
                print("V8180_FIR_PHASE_ADAPTIVE",count,strength,
                      verdict.accepted,verdict.phase_before_deg,
                      verdict.phase_after_deg,verdict.reasons,flush=True)
                if verdict.accepted:
                    # GUI summary reports the *verified trusted* metric.
                    # The unchanged core FIRSource defaults remain
                    # coherence-independent for the continuous preview API.
                    n=int(np.count_nonzero(
                        (np.asarray(freq,float)>=lf)&
                        (np.asarray(freq,float)<=hf)&
                        (np.asarray(coh,float)>=.65)))
                    b=float(verdict.phase_before_deg)
                    after=float(verdict.phase_after_deg)
                    preview=replace(preview,phase_rms_before=b,
                        phase_rms_after=after,
                        phase_improvement_pct=100*(1-after/max(b,1e-9)),
                        phase_quality_bins=n)
                    return result,preview
                failures.append(
                    f"{strength:.0%}: "+"; ".join(verdict.reasons)[:150])
            raise ValueError("FIR PHASE QUALITY HOLD: " +
                             " | ".join(failures))
        if mode!="mag":
            raise ValueError("Invalid FIR mode")
        result=design_linear_phase_fir(
            freq,h,coh,taps=count,fs=fs,source=name,lf=lf,hf=hf,strict=False)
        preview=make_source(
            freq,h,coh,result.taps,fs,name,digest,revision,lf,hf,mode,
            phase_smooth_oct=phase_oct)
        verdict=evaluate_fir_quality(preview,result,lf,hf)
        print("V8180_FIR_MAG_QUALITY",count,verdict.accepted,
              "RMS",verdict.mag_rms_before_db,verdict.mag_rms_after_db,
              "REASONS",verdict.reasons,flush=True)
        if not verdict.accepted:
            raise ValueError("FIR MAG QUALITY HOLD: "+"; ".join(verdict.reasons))
        return result,preview
    if int(taps):
        return design(int(taps))
    candidates=[]
    failures=[]
    for count in (512,1024,2048,4096):
        try:
            result,preview=design(count)
        except ValueError as exc:
            failures.append(f"{count} taps: {str(exc)[:180]}")
            continue
        physical=tuple(w for w in result.warnings
                       if "Coherence thấp" not in str(w))
        after=(preview.phase_rms_after if preview.phase_rms_after is not None
               else float("inf"))
        # Prefer the smallest warning-free kernel. If every candidate warns,
        # minimize physical warnings, then measured excess RMS, then latency.
        rank=((1,len(physical),after,count) if physical else (0,0,count,count))
        candidates.append((rank,result,preview))
        if not physical:
            break
    if not candidates:
        raise ValueError("FIR QUALITY HOLD: không có taps an toàn. "
                         +" | ".join(failures))
    _,result,preview=min(candidates,key=lambda item:item[0])
    result=replace(result,warnings=tuple(result.warnings)+
                   (f"AUTO TAPS: chọn {len(result.taps)} taps",))
    return result,preview

class FIRDialog(TFDialog):
    preview_ready=pyqtSignal(object)
    preview_clear=pyqtSignal()
    """One Smaart-ticked TRF -> offline linear-phase FIR (no DSP write).

    FIR selection and Fs must be fresh, and export must use the exact
    immutable source bytes that created the taps. Never interpret SUM
    or the selected Auto Phase 2-trace pair as the FIR input.
    """
    def _taps_choice_matches(self,actual):
        selected=int(self.taps.currentData())
        return selected==0 or selected==int(actual)
    def _verified_single(self):
        # Smaart 8 uses a different Data Bar; V9 tick detection is forbidden.
        # An explicitly user-selected TRF is an OFFLINE source only.
        token=getattr(self,"_manual_token",None)
        if token is not None:
            from smaart_runtime_paths_v868 import running_major
            if running_major()==9:
                return None  # never mix a V8 offline source into V9 mode
            try:
                stat=Path(token[0]).stat()
                if (stat.st_mtime_ns,stat.st_size)!=(token[1],token[2]):
                    return None
            except OSError:
                return None
            return token
        observer=getattr(self.engine,"observer",None)
        get=getattr(observer,"current_single",None)
        return get() if callable(get) else None

    def _fir_fs_snapshot(self):
        if getattr(self,"_manual_token",None) is not None:
            from smaart_runtime_paths_v868 import saved_config
            return read_saved_smaart_fs(saved_config(8))
        return self._saved_fs()

    def choose_offline_trf(self):
        from smaart_runtime_paths_v868 import trace_directory
        directory=trace_directory(8)
        start=str(directory if directory and directory.is_dir() else Path.home())
        selected,_=QFileDialog.getOpenFileName(
            self,"Chọn một tệp TRF cho Auto FIR offline",start,
            "Smaart Transfer Function (*.trf)")
        if not selected:return
        try:
            self.set_offline_trf(selected)
        except Exception as exc:
            self.warning(exc)

    def set_offline_trf(self,filename):
        # Explicit file selection, not simulated native tick validation.
        from smaart_runtime_paths_v868 import running_major
        if running_major()==9:
            raise ValueError("FIR offline V8 không được chọn khi Smaart 9 chạy")
        # A new explicit selection invalidates any previously approved FIR,
        # even when the newly chosen file turns out to be invalid.
        self.clear_offline_trf()
        path=Path(filename).resolve(strict=True)
        if path.suffix.lower()!=".trf" or not path.is_file():
            raise ValueError("Chỉ hỗ trợ tệp Transfer Function .trf")
        record=read_trf(path)
        if len(record.hz)<60:
            raise ValueError("TRF không đủ dữ liệu tần số")
        from smaart_runtime_paths_v868 import saved_config
        if read_saved_smaart_fs(saved_config(8)) is None:
            raise ValueError("Chưa xác minh Fs lưu trong Smaart 8")
        stat=path.stat()
        self._manual_generation+=1
        self._manual_token=(str(path),stat.st_mtime_ns,stat.st_size,
                            self._manual_generation)
        self._fir_state=None
        self.refresh_sources()

    def clear_offline_trf(self):
        self._manual_token=None
        self._fir_state=None
        self.refresh_sources()

    def _one_tick_still_marked(self):
        """A transient tick timeout is not an explicit selection change.

        This check never grants computation/export. The native observer must
        independently return a fresh 3/3 current_single() before any rebind.
        """
        observer=getattr(self.engine,"observer",None)
        states=getattr(observer,"states",None)
        order=getattr(observer,"order",None)
        return (isinstance(states,dict) and bool(states) and
                order is not None and len(states)==len(order) and
                all(x in ("on","off") for x in states.values()) and
                sum(x=="on" for x in states.values())==1)

    def _same_approved_source(self,token,snap):
        """Check FULL file provenance before re-arming a prior FIR preview."""
        proof=getattr(self,"_approved",None)
        if proof is None or self.result is None or token is None:
            return False
        old,digest,old_snap,taps,lf,hf,mode=proof
        if (not isinstance(token,tuple) or len(token)!=4 or
                tuple(token[:3])!=tuple(old[:3]) or snap!=old_snap or
                not self._taps_choice_matches(taps) or
                self.fir_lf.value()!=lf or self.fir_hf.value()!=hf or
                self.fir_mode.currentData()!=mode or
                getattr(self,"_approved_phase_plus",None)!=bool(
                    mode=="phase" and self.phase_plus.isChecked()) or
                self.result.mode!=mode or self.result.fs!=snap.hz or
                self.result.source!=Path(token[0]).stem or
                len(self.result.taps)!=taps):
            return False
        observer=getattr(self.engine,"observer",None)
        bound_hwnd=getattr(self,"_approved_window",None)
        if bound_hwnd is not None and getattr(observer,"hwnd",None)!=bound_hwnd:
            return False
        try:
            stat=Path(token[0]).stat()
            return ((stat.st_mtime_ns,stat.st_size)==(token[1],token[2]) and
                    self._source_hash(token[0])==digest)
        except (OSError,ValueError,TypeError):
            return False

    def refresh_sources(self):
        if not hasattr(self,"_fir_ready"):
            # TFDialog.__init__ calls the virtual method before FIR exists.
            self.source.addItem("FIR: chỉ dùng 1 Trace tick",None)
            return
        token=self._verified_single()
        snap=self._fir_fs_snapshot()
        state=(token,snap)
        if state==self._fir_state:
            return
        proof=getattr(self,"_approved",None)
        # Losing foreground times out native ticks. Retain only the immutable
        # local FIR data; never authorize export or paint using stale evidence.
        # V8.109: an uncertain tick pixel may temporarily become "unknown".
        # That is NOT a confirmed deselection and must not destroy the
        # already calculated FIR. Retention is data-only: display remains
        # bounded by _proof_current(display=True), export/DSP strict.
        observer=getattr(self.engine,"observer",None)
        candidate=getattr(observer,"single_candidate",None)
        states=getattr(observer,"states",{})
        order=getattr(observer,"order",())
        known_on=(sum(v=="on" for v in states.values())
                  if isinstance(states,dict) else 99)
        complete=(isinstance(states,dict) and bool(order) and
                  len(states)==len(order) and
                  all(v in ("on","off") for v in states.values()))
        still_possible=(getattr(observer,"ready",False) and
                        isinstance(states,dict) and bool(order) and
                        len(states)==len(order) and known_on<=1 and
                        not (complete and known_on!=1))
        retained_candidate=(proof is not None and
                            candidate==proof[0][:3] and still_possible)
        transient=(token is None and proof is not None and
                   self.result is not None and
                   (snap is None or snap==proof[2]) and
                   getattr(self,"_manual_token",None) is None and
                   (retained_candidate or
                    (candidate is None and self._one_tick_still_marked())))
        restored=(token is not None and proof is not None and
                  self._same_approved_source(token,snap))
        self._fir_state=state
        self._fir_token=token
        self._fir_fs=snap
        if getattr(self,"_manual_token",None) is not None:
            self.note.setText("TRF OFFLINE · chỉ thiết kế/xuất FIR; không phủ lên Smaart")
        else:
            self.note.setText("Auto FIR · Preview · Không ghi DSP")
        self.fs.setText(
            f"Fs {snap.hz/1000:g} kHz — Smaart (đã lưu)" if snap else
            "Fs Smaart chưa xác minh — FIR HOLD")
        self.source.blockSignals(True)
        self.source.clear()
        recognition=trace_recognition_text(observer,token,
            known_on if complete else None)
        if token is None:
            label=("FIR HOLD: "+recognition if transient else recognition)
            self.source.addItem(label,None)
        elif getattr(self,"_manual_token",None) is not None:
            self.source.addItem("TRF OFFLINE: "+_middle_elide(Path(token[0]).stem,18),0)
        else:
            self.source.addItem("TRF: "+_middle_elide(Path(token[0]).stem,24),0)
        if token is not None:
            # V8.118: long names were cut to 21 chars, losing the suffix
            # that distinguishes traces; full name always in the tooltip.
            self.source.setToolTip(Path(token[0]).stem)
        self.source.setEnabled(False)
        self.source.blockSignals(False)
        if transient:
            self.export_txt.setEnabled(False)
            self.export_wav.setEnabled(False)
            self.export_dsp.setEnabled(False)
            self.export_fir.setEnabled(False)
            self.export_menu.hide()
            self.summary.setText("FIR HOLD: chờ 3/3 tick xác minh; tạm khóa xuất")
            return
        if restored:
            _,digest,_,taps,lf,hf,mode=proof
            self._approved=(token,digest,snap,taps,lf,hf,mode)
            self.summary.setText(
                f"{taps} taps | {mode.upper()} {lf}-{hf} Hz | Fs {snap.hz/1000:g}k"
                f" | Delay {self.result.latency_ms:.2f} ms"
                + getattr(self,"_phase_quality_summary",""))
            self._refresh_export()
            return
        self.invalidate()

    def invalidate(self,*_):
        # V8.118: a setting changed while the worker was designing used to
        # discard the result silently; tell the user why it disappeared.
        was_computing=(hasattr(self,"calculate") and not self.calculate.isEnabled()
                       and getattr(self,"_pending_fir",None) is not None)
        if getattr(self,"_approved",None) is not None:
            # V8.129 diagnostic: who discards an approved FIR right after design.
            import traceback
            print("V8129_FIR_DISCARD"," <- ".join(
                f"{f.name}:{f.lineno}" for f in
                traceback.extract_stack(limit=8)[:-1][::-1]),flush=True)
        if hasattr(self,"_serial"):self._serial+=1
        super().invalidate()
        if was_computing:
            import traceback
            print("V8124_FIR_INVALIDATED_WHILE_COMPUTING"," <- ".join(
                f"{f.name}:{f.lineno}" for f in
                traceback.extract_stack(limit=7)[:-1][::-1]),flush=True)
            self.summary.setText("Đã đổi thiết lập FIR khi đang tính — bấm Auto FIR để tính lại.")
        if hasattr(self,"export_txt"):self.export_txt.setEnabled(False)
        if hasattr(self,"export_wav"):self.export_wav.setEnabled(False)
        if hasattr(self,"export_dsp"):self.export_dsp.setEnabled(False)
        if hasattr(self,"export_fir"):self.export_fir.setEnabled(False)
        if hasattr(self,"calculate"):self.calculate.setEnabled(True)
        self._approved=None
        self._approved_window=None
        self._approved_phase_plus=None
        self._fir_dsp_ready_at=None
        self._fir_dsp_ready_ticket=None
        self._phase_quality_summary=""
        self._pending_fir=None
        self.preview_clear.emit()

    @staticmethod
    def _source_hash(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _proof_current(self,*,check_hash=True,display=False):
        """FIR provenance proof. ``display=True`` is DISPLAY-ONLY (V8.107):
        it may bridge one bounded 3/3 tick re-arm of the SAME candidate.
        Export, menus and DSP actions always call the strict default."""
        proof=getattr(self,"_approved",None)
        if proof is None or self.result is None:
            return False
        token,digest,snap,taps,lf,hf,mode=proof
        single=self._verified_single()
        if single==token and self._fir_token==token:
            self._fir_tick_ok_at=_fir_display_now()
            tick_ok=True
        elif (display and single is None and self._fir_token in (None,token)
              and getattr(self,"_manual_token",None) is None):
            from mageq_presentation_gate_v853 import presentation_tick_ok
            tick_ok,_,_=presentation_tick_ok(
                getattr(self.engine,"observer",None),token,
                getattr(self,"_fir_tick_ok_at",0.),now=_fir_display_now())
        else:
            tick_ok=False
        if (not tick_ok or
                self._fir_fs!=snap or
                self._fir_fs_snapshot()!=snap or
                not self._taps_choice_matches(taps) or
                self.fir_lf.value()!=lf or self.fir_hf.value()!=hf or
                self.fir_mode.currentData()!=mode or
                getattr(self,"_approved_phase_plus",None)!=bool(
                    mode=="phase" and self.phase_plus.isChecked()) or
                self.result.mode!=mode or
                self.result.fs!=snap.hz or
                len(self.result.taps)!=taps or
                self.result.source!=Path(token[0]).stem):
            return False
        try:
            stat=Path(token[0]).stat()
            if (stat.st_mtime_ns,stat.st_size)!=(token[1],token[2]):
                return False
            if check_hash and self._source_hash(token[0])!=digest:
                return False
        except (OSError,TypeError,ValueError):
            return False
        return True

    def _refresh_export(self):
        ready=self._proof_current(check_hash=True)
        self.export_txt.setEnabled(ready)
        self.export_wav.setEnabled(ready)
        if hasattr(self,"export_fir"):
            self.export_fir.setEnabled(ready)
        if hasattr(self,"export_dsp"):
            from fir_dsp_export_v872 import get_profile,validate
            allowed=ready and not validate(
                self.result,get_profile(self.dsp_profile.currentData()))
            self.export_dsp.setEnabled(bool(allowed))

    def show_export_fir_menu(self):
        """Single export button -> generic TXT or supported vendor profile.

        Never enable unsupported tap limits, and do not bypass the existing
        SHA/trace/Fs/session proof or the post-file-dialog proof recheck.
        """
        if not self._proof_current(check_hash=True):
            self.invalidate()
            return self.warning("FIR Export HOLD: cần một Trace đã xác minh")
        from fir_dsp_export_v872 import get_profile,validate
        self.export_txt_action.setEnabled(True)
        for name,action in self.export_vendor_actions.items():
            errors=validate(self.result,get_profile(name))
            action.setEnabled(not errors)
            action.setStatusTip("; ".join(errors) if errors else
                                "Xuất hệ số FIR, không nạp trực tiếp vào DSP")
            action.setToolTip("; ".join(errors) if errors else
                              "Chỉ định dạng hệ số; kiểm tra model DSP trước khi nạp")
        self.export_menu.popup(
            self.export_fir.mapToGlobal(QPoint(0,self.export_fir.height())))

    def save_dsp_profile(self,profile_name=None):
        from fir_dsp_export_v872 import get_profile,write_export,validate
        if not self._proof_current(check_hash=True):
            self.invalidate()
            return self.warning("DSP Export HOLD: Trace/Fs/file thay đổi")
        selected=(profile_name if isinstance(profile_name,str) and profile_name
                  else self.dsp_profile.currentData())
        profile=get_profile(selected)
        errors=validate(self.result,profile)
        if errors:return self.warning("; ".join(errors))
        name="RemiX_Duo_FIR_"+str(self.result.fs)+"Hz"+profile["extension"]
        dest,_=QFileDialog.getSaveFileName(
            self,"Xuất FIR DSP/Crossover (hệ số, không nạp DSP)",name,
            "FIR coefficients (*"+profile["extension"]+")",
            options=QFileDialog.Option.DontUseNativeDialog)
        if not dest:return
        if not self._proof_current(check_hash=True):
            self.invalidate()
            return self.warning("DSP Export HOLD: nguồn thay đổi khi chọn đường dẫn")
        try:
            write_export(self.result,profile["name"],dest)
        except Exception as exc:return self.warning(exc)

    def get_data(self):
        token=self._verified_single()
        if token is None or token!=self._fir_token:
            raise ValueError("FIR cần đúng 1 Trace tick đã xác minh trong Smaart")
        path=Path(token[0])
        before=path.stat()
        if (before.st_mtime_ns,before.st_size)!=(token[1],token[2]):
            raise ValueError("Dữ liệu FIR thay đổi, phải xác minh lại Trace")
        trace=read_trf(path)
        after=path.stat()
        if (after.st_mtime_ns,after.st_size)!=(token[1],token[2]) or self._verified_single()!=token:
            raise ValueError("Trace thay đổi khi đọc FIR")
        return (trace.hz.copy(),trace.h.copy(),trace.coherence.copy(),path.stem)

    def __init__(self,engine):
        super().__init__(engine,"FIR")
        self._manual_token=None
        self._manual_generation=0
        self.plot.hide()  # FIR curves belong on the original Smaart plot overlays.
        self._serial=0
        self._fir_ready=True
        self._fir_state=None
        self._fir_token=None
        self._fir_fs=None
        self._approved=None
        self._pending_fir=None
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="remix_fir")
        self._bus=EQFinished()
        self._bus.finished.connect(self._finish)

        self.taps=QComboBox()
        self.taps.addItem("AUTO taps",0)
        for count in (512,1024,2048,4096):
            self.taps.addItem(f"{count} taps",count)
        self.taps.setCurrentIndex(0)
        self.taps.currentIndexChanged.connect(self.invalidate)
        # Phase+ is an explicit opt-in, OFF on first use. AUTO taps remains
        # the default; manual counts are retained for expert comparison.
        self.phase_plus=QCheckBox("Phase+")
        self.phase_plus.setChecked(False)
        self.phase_plus.setToolTip(
            "Bật để thử tối ưu Excess Phase mạnh hơn theo taps đã chọn. "
            "Coherence chỉ tham khảo; các giới hạn Mag/pre-ringing vẫn được kiểm tra.")
        self.phase_plus.toggled.connect(self.invalidate)
        self.phase_plus.hide()  # Show only when FIR PHASE is selected.
        self.taps_label=QLabel("Chọn Taps")
        self.taps_label.setObjectName("hint")
        self.main.insertWidget(3,self.taps_label)
        self.main.insertWidget(4,self.taps)
        # Keep original combobox as internal state for the solver, overlays
        # and exports; users switch modes with two clear exclusive buttons.
        self.fir_mode=QComboBox()
        self.fir_mode.addItem("FIR MAG | Biên độ","mag")
        self.fir_mode.addItem("FIR PHASE | Pha","phase")
        self.fir_mode.setAccessibleName("FIR correction mode (internal)")
        self.fir_mag_button=QPushButton("FIR MAG")
        self.fir_phase_button=QPushButton("FIR PHA")
        self.fir_modes=QButtonGroup(self)
        self.fir_modes.setExclusive(True)
        for button in (self.fir_mag_button,self.fir_phase_button):
            button.setObjectName("firModeSwitch")
            button.setCheckable(True)
            self.fir_modes.addButton(button)
        self.fir_mag_button.setChecked(True)
        self.fir_mag_button.clicked.connect(
            lambda: self.fir_mode.setCurrentIndex(0))
        self.fir_phase_button.clicked.connect(
            lambda: self.fir_mode.setCurrentIndex(1))
        self.fir_mode.currentIndexChanged.connect(self._on_fir_range_changed)
        mode_row=QHBoxLayout()
        mode_row.setSpacing(4)
        mode_row.addWidget(self.fir_mag_button)
        mode_row.addWidget(self.fir_phase_button)
        self.main.insertLayout(5,mode_row)
        self._fir_mode_row=mode_row  # reusable layout, relocated by style_fir()
        self.main.insertWidget(6,self.phase_plus)
        self.main.insertWidget(7,self.fir_mode)
        self.fir_mode.hide()
        self.fs=QLabel("Fs: chờ xác minh Smaart")
        self.fs.setObjectName("hint")
        self.fs.setWordWrap(True)
        self.main.insertWidget(8,self.fs)
        self.offline_row=QHBoxLayout()
        self.offline_button=QPushButton("Chọn TRF V8")
        self.offline_button.setToolTip(
            "Chọn TRF thủ công để thiết kế/xuất FIR offline; không giả nhận Trace tick")
        self.offline_button.clicked.connect(self.choose_offline_trf)
        self.offline_clear=QPushButton("Bỏ TRF")
        self.offline_clear.clicked.connect(self.clear_offline_trf)
        self.offline_row.addWidget(self.offline_button,2)
        self.offline_row.addWidget(self.offline_clear,1)
        self.main.insertLayout(self.main.indexOf(self.source)+1,self.offline_row)
        self.overlay_status=QLabel("MagFIR HOLD | PhaseFIR HOLD")
        # V8.61: explicit solver work band, independently editable.
        self.fir_range_label=QLabel("FIR LF/HF · Kéo trên đồ thị")
        self.fir_range_label.setToolTip("Kéo nhãn LF/HF hoặc đường nét đứt trên đồ thị Smaart; tối thiểu 1 octave")
        self.fir_range_label.setObjectName("hint")
        self.main.insertWidget(5,self.fir_range_label)
        band=QHBoxLayout()
        self.fir_lf=QSpinBox()
        self.fir_lf.setRange(20,19000)
        self.fir_lf.setSingleStep(10)
        self.fir_lf.setValue(500)
        self.fir_lf.setPrefix("LF ")
        self.fir_hf=QSpinBox()
        self.fir_hf.setRange(100,20000)
        self.fir_hf.setSingleStep(100)
        self.fir_hf.setValue(2500)
        self.fir_hf.setPrefix("HF ")
        band.addWidget(self.fir_lf)
        band.addWidget(self.fir_hf)
        self.main.insertLayout(6,band)
        self.fir_lf.valueChanged.connect(self._on_fir_range_changed)
        self.fir_hf.valueChanged.connect(self._on_fir_range_changed)
        self.overlay_status.setObjectName("hint")
        self.overlay_status.setWordWrap(True)
        self.main.insertWidget(7,self.overlay_status)
        self.note.setText("FIR: dùng 1 Trace tick → Linear Phase → không ghi DSP")
        self.calculate=QPushButton("TẠO FIR")
        self.calculate.setObjectName("run")
        self.calculate.clicked.connect(self.compute)
        self.main.addWidget(self.calculate)
        # One visible export action. Keep old signal endpoints hidden for
        # compatible tests/integrations; no extra export widgets in the dock.
        buttons=QHBoxLayout()
        self.export_fir=QPushButton("XUẤT FIR")
        self.export_fir.setObjectName("run")
        self.export_fir.setToolTip(
            "Chọn TXT chung hoặc hãng DSP/Crossover sau khi FIR được xác minh")
        self.export_fir.setEnabled(False)
        self.export_fir.clicked.connect(self.show_export_fir_menu)
        buttons.addWidget(self.export_fir)
        self.main.addLayout(buttons)
        self.export_txt=QPushButton("Xuất TXT",self)
        self.export_txt.clicked.connect(self.save_txt)
        self.export_wav=QPushButton("Xuất WAV",self)
        self.export_wav.clicked.connect(self.save_wav)
        self.export_txt.hide()
        self.export_wav.hide()
        self.export_txt.setEnabled(False)
        self.export_wav.setEnabled(False)
        from fir_dsp_export_v872 import PROFILES
        self.dsp_profile=QComboBox()
        for profile in PROFILES:
            self.dsp_profile.addItem(profile["name"],profile["name"])
        self.dsp_profile.hide()
        self.dsp_profile.setToolTip(
            "Định dạng hệ số tham khảo; chưa chứng nhận nạp trực tiếp từng model.")
        self.export_dsp=QPushButton("Xuất DSP / Crossover",self)
        self.export_dsp.setEnabled(False)
        self.export_dsp.clicked.connect(self.save_dsp_profile)
        self.export_dsp.hide()
        self.dsp_profile.currentIndexChanged.connect(self._refresh_export)
        # Fixed menu grouping: first TXT, then profile names by brand.
        # Each entry re-checks source proof and taps on selection AND save.
        self.export_menu=QMenu(self)
        self.export_txt_action=self.export_menu.addAction("TXT chung (.txt)")
        self.export_txt_action.triggered.connect(self.save_txt)
        self.export_vendor_menu=self.export_menu.addMenu("Theo hãng DSP / Crossover")
        self.export_vendor_actions={}
        for profile in PROFILES:
            name=profile["name"]
            if name.startswith("Generic"):
                continue
            action=self.export_vendor_menu.addAction(name)
            action.setToolTip(
                "Định dạng hệ số tham khảo; kiểm tra model/giới hạn taps trước khi nạp")
            action.triggered.connect(
                lambda checked=False, vendor=name: self.save_dsp_profile(vendor))
            self.export_vendor_actions[name]=action
        self._action_row=buttons  # Existing layout mover keeps one export row.
        self.setFixedHeight(540)
        self.refresh_sources()
        # First-open default is FIR PHA, not FIR MAG. Phase+ stays OFF;
        # never force tap count or reset a user's later mode choice.
        self.fir_mode.setCurrentIndex(1)

    def _on_fir_range_changed(self,*_):
        # Buttons reflect the shared FIR mode state even when a legacy
        # integration changes fir_mode programmatically. No auto Phase+ tick.
        phase=self.fir_mode.currentData()=="phase"
        self.fir_mag_button.setChecked(not phase)
        self.fir_phase_button.setChecked(phase)
        self.phase_plus.setVisible(phase)
        # Keep both manual spin edits and drag gestures within one octave.
        # Block only the corrective signal to avoid recursive invalidation.
        lf,hf=self.fir_lf.value(),self.fir_hf.value()
        if lf*2>hf:
            target=self.fir_hf if self.sender() is self.fir_hf else self.fir_lf
            corrected=lf*2 if target is self.fir_hf else hf//2
            target.blockSignals(True)
            try:
                target.setValue(corrected)
            finally:
                target.blockSignals(False)
        # Invalidate stale DSP/export before moving the visual band. This
        # never auto-starts a FIR worker during a mouse drag.
        self.invalidate()
        callback=getattr(self,"range_changed",None)
        if callable(callback):
            callback(self.fir_lf.value(),self.fir_hf.value(),
                     self.fir_mode.currentData())

    def drag_roi_to(self,kind,frequency):
        """Direct plot drag; FIR-only band and minimum one octave."""
        from fir_roi_v888 import clamp_fir_drag
        if kind not in ("LF","HF"):
            raise ValueError("Unknown FIR ROI endpoint")
        target=self.fir_lf if kind=="LF" else self.fir_hf
        bounded=clamp_fir_drag(kind,frequency,self.fir_lf.value(),
                               self.fir_hf.value())
        if target.value()!=bounded:
            target.setValue(bounded)

    def compute(self):
        try:
            freq,h,coh,name=self.get_data()
            snap=self._fir_fs_snapshot()
            token=self._verified_single()
            if snap is None or snap!=self._fir_fs:
                raise ValueError("Fs Smaart đã lưu không đồng bộ; FIR HOLD")
            digest=self._source_hash(token[0])
            taps=int(self.taps.currentData())
            lf,hf=self.fir_lf.value(),self.fir_hf.value()
            mode=self.fir_mode.currentData()
            phase_plus=bool(mode=="phase" and self.phase_plus.isChecked())
            if not (20<=lf<hf<=snap.hz/2 and hf/lf>=2):
                raise ValueError("FIR Range khong hop le: LF < HF, toi thieu 1 octave")
        except Exception as exc:
            self.invalidate()
            self.warning(exc)
            return
        self.invalidate()
        self._serial+=1
        ticket=self._serial
        self._pending_fir=(ticket,token,digest,snap,taps,name,lf,hf,mode,phase_plus)
        self.calculate.setEnabled(False)
        print("V8124_FIR_START",ticket,mode,taps,lf,hf,name,flush=True)
        self.summary.setText("Đang thiết kế FIR trên worker…")
        future=self._pool.submit(
            _fir_design_and_preview,freq,h,coh,taps,snap.hz,name,digest,ticket,
            lf,hf,mode,phase_plus,
            float(self.engine.phase_smooth.currentData() or 0.))
        schedule_auto_wait_notice(
            self,lambda t=ticket:t==self._serial and not self.calculate.isEnabled(),
            getattr(self.engine,"graph_phase" if mode=="phase" else "graph_mag",None))
        future.add_done_callback(
            lambda done,t=ticket:self._bus.finished.emit(t,done))

    def _finish(self,ticket,future):
        if ticket!=self._serial:
            print("V8124_FIR_STALE",ticket,self._serial,flush=True)
            return
        self.calculate.setEnabled(True)
        try:
            result,preview=future.result()
            proof=self._pending_fir
            if proof is None or proof[0]!=ticket:
                raise ValueError("FIR worker result stale")
            _,token,digest,snap,taps,name,lf,hf,mode,phase_plus=proof
            from mageq_presentation_gate_v853 import token_still_current
            # V8.117: a missed scan during re-arm must not discard the design.
            rearming=(self._verified_single() is None and
                      getattr(self,"_manual_token",None) is None and
                      token_still_current(getattr(self.engine,"observer",None),token))
            if (((self._verified_single()!=token or self._fir_token!=token) and
                     not (rearming and self._fir_token in (None,token))) or
                    self._fir_fs_snapshot()!=snap or self._fir_fs!=snap or
                    int(self.taps.currentData())!=taps or
                    self.fir_lf.value()!=lf or self.fir_hf.value()!=hf or
                    self.fir_mode.currentData()!=mode or
                    bool(mode=="phase" and self.phase_plus.isChecked())!=phase_plus or
                    self._source_hash(token[0])!=digest):
                raise ValueError("Trace/Fs/taps thay đổi trong khi tính FIR")
            kernel=np.asarray(result.taps,float)
            if ((taps and kernel.size!=taps) or not np.isfinite(kernel).all() or
                    (mode=="mag" and not np.allclose(kernel,kernel[::-1],rtol=0,atol=1e-9)) or
                    not np.isfinite(result.actual_db).all()):
                raise ValueError("FIR coefficients không đạt kiểm tra đối xứng/hữu hạn")
            selected_taps=int(kernel.size)
            # The original FIR solver imposes the specified +/- bounds
            # on desired EQ; reject unexpected actual filter overshoot.
            fir_warnings=list(getattr(result,"warnings",()) or ())
            peak=float(np.max(result.actual_db))
            if peak>7.5:
                # V8.125: was HOLD; the user asked to always create the FIR.
                fir_warnings.append(f"FIR tăng tối đa {peak:.1f} dB (>7.5 dB)")
            # V8.118 HOLD -> V8.125 warning: a phase FIR that barely flattens
            # Excess Phase mostly adds latency; say so, but still create it.
            gain=getattr(preview,"phase_improvement_pct",None)
            if mode=="phase" and gain is not None and gain<FIR_PHASE_MIN_IMPROVEMENT_PCT:
                fir_warnings.append(
                    f"Excess Phase cải thiện ít "
                    f"({preview.phase_rms_before:.1f}°→{preview.phase_rms_after:.1f}°, "
                    f"{gain:+.1f}%) — thử 2048/4096 taps hoặc đổi LF/HF")
        except Exception as exc:
            self.invalidate()
            self.warning(exc)
            return
        self.result=result
        self._approved=(token,digest,snap,selected_taps,lf,hf,mode)
        self._approved_phase_plus=phase_plus
        self._approved_window=getattr(getattr(self.engine,"observer",None),
                                       "hwnd",None)
        # FIR DSP is fully computed and the local preview may be shown now.
        # Native Smaart paint/export authorization is a separate proof.
        self._fir_dsp_ready_at=time.perf_counter()
        self._fir_dsp_ready_ticket=ticket
        print("R55_FIR_DSP_READY",ticket,round(self._fir_dsp_ready_at,6),
              mode,len(result.taps),flush=True)
        self.plot.set_curves(result.hz,result.target_db,result.actual_db)
        self.plot.set_working_range(lf,hf)
        offline=self._manual_token is not None
        self._phase_quality_summary=" | Phase+" if phase_plus else ""
        if mode=="phase":
            self._phase_quality_summary+=(
                f" | Hiệu chỉnh {100*getattr(result,'correction_strength',1.):.0f}%")
        quality_detail=(f"Phase+: 4096-tap advanced correction, physical FIR delay "
                        f"{result.latency_ms:.2f} ms (must be accounted for).\n"
                        if phase_plus else "")
        phase_lf=getattr(result,"phase_lf_hz",None)
        if mode=="phase" and phase_lf is not None and phase_lf>lf:
            quality_detail+=(f"Phase chỉ được sửa từ {phase_lf:.0f} Hz trở lên: "
                             f"{len(result.taps)} taps không đủ phân giải thấp hơn "
                             "(Mag vẫn được kiểm tra trên toàn dải LF–HF).\n")
        if mode=="phase" and preview.phase_rms_before is None:
            # V8.125: FIR is created on relaxed coherence; never invent an RMS.
            self._phase_quality_summary+=" | Excess RMS: chưa đo được (Coherence thấp)"
            quality_detail+=(
                f"Phase excess RMS: not measurable ({preview.phase_quality_bins} "
                "valid TF bins, need 35).\n"
                "Metric removes fitted bulk delay, NOT absolute phase.\n")
        if mode=="phase" and preview.phase_rms_before is not None:
            before=preview.phase_rms_before
            after=preview.phase_rms_after
            gain=preview.phase_improvement_pct
            self._phase_quality_summary+=f" | Excess RMS {before:.1f}°→{after:.1f}°"
            quality_detail+=(
                f"Phase excess RMS {before:.2f}° -> {after:.2f}° "
                f"(improvement {gain:+.1f}%, {preview.phase_quality_bins} valid TF bins)\n"
                "Metric removes fitted bulk delay, NOT absolute phase.\n")
            if gain<20:
                quality_detail+=(
                    "CẢNH BÁO: FIR chưa làm phẳng Excess Phase đáng kể. "
                    "Thử 2048/4096 taps hoặc dải LF/HF hợp lý hơn; "
                    "không tăng coherence giả.\n")
        self.summary.setText(
            f"{selected_taps} taps | {mode.upper()} {lf}-{hf} Hz | Fs {snap.hz/1000:g}k"
            f" | Delay {result.latency_ms:.2f} ms"
            + self._phase_quality_summary
            + (" | DSP READY · native đang xác minh" if not offline else "")
            + (" | OFFLINE TRF (chưa xác minh trên Smaart)" if offline else ""))
        self.details.setPlainText(
            f"Source: {result.source}\nFs Smaart (đã lưu): {result.fs} Hz\n"
            f"{('Magnitude inverse (linear phase)' if mode=='mag' else 'Excess phase correction (magnitude guarded)')} / OFFLINE\n"
            + quality_detail
            + "Boost +6 dB max / Cut -12 dB max\n"
            "FIR PHASE: delay-compensated preview only; exported taps retain real delay.\n"
            "Xuất FIR taps, không nạp DSP/Smaart.")
        self._refresh_export()
        print("V8124_FIR_OK",mode,selected_taps,lf,hf,self._phase_quality_summary,flush=True)
        self._fir_warnings=tuple(fir_warnings)
        if fir_warnings:
            # V8.125: created anyway; tell the user what is weak about it.
            print("V8125_FIR_WARN"," | ".join(fir_warnings)[:300],flush=True)
            self.details.setPlainText(self.details.toPlainText()+
                "\nCẢNH BÁO:\n- "+"\n- ".join(fir_warnings))
            # V8.138: exactly one compact Toast, on the plot when available;
            # never duplicate it over the FIR controls.
            graph=getattr(self.engine,"graph_phase" if mode=="phase" else "graph_mag",None)
            self.notice("FIR: "+"; ".join(fir_warnings),graph)
        if self._manual_token is None:
            self.preview_ready.emit(preview)
        else:
            # Offline import is NOT a verified Smaart Data Bar tick.
            # Never paint an unverified FIR response on Smaart 8.
            self.preview_clear.emit()

    def _export(self,fmt):
        # Verify again *after* the user chooses a destination, before writing.
        if not self._proof_current(check_hash=True):
            self.invalidate()
            return self.warning("FIR Export HOLD: Trace/Fs/source bytes đã thay đổi")
        is_wav=fmt=="wav"
        name="RemiX_Dou_FIR.wav" if is_wav else "RemiX_Dou_FIR.txt"
        dest,_=QFileDialog.getSaveFileName(self,"Xuất FIR "+fmt.upper(),name,
                         "WAV (*.wav)" if is_wav else "Text (*.txt)",
                         options=QFileDialog.Option.DontUseNativeDialog)
        if not dest:return
        if not self._proof_current(check_hash=True):
            self.invalidate()
            return self.warning("FIR Export HOLD: nguồn đổi trong lúc chọn file")
        try:
            (save_fir_wav_float if is_wav else save_fir_txt)(dest,self.result)
        except Exception as exc:
            return self.warning(exc)

    def save_txt(self):
        return self._export("txt")

    def save_wav(self):
        return self._export("wav")

    def closeEvent(self,event):
        if not getattr(self,"_really_close",False):
            self.hide()
            event.ignore()
            return
        self._serial+=1
        from worker_lifecycle_v8142 import bounded_shutdown
        bounded_shutdown(self._pool)
        super().closeEvent(event)

class RightToolDock(QWidget):
    """Floating, borderless *visual* sidebar, never injected into Smaart."""
    def __init__(self,engine,eq,fir):
        super().__init__(None)
        self.engine=engine  # read-only selection state for compact invalid dock
        self.setObjectName("rightDock")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE+"""
          QWidget#rightDock {background:#08131D;border:1px solid #305168;}
          QLabel#dockHeading {background:#132B20;color:#71FF55;
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
        # Dock title with a deliberate native-view escape hatch.
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
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stack=QStackedWidget()
        # V8.107: the LAN "Điều khiển" tool was removed from the Duo toolbar
        # at the user's request; no page and no LAN server are constructed.
        self.pages={"phase":engine,"eq":eq,"fir":fir}
        self.page_heights={"phase":400,"eq":555,"fir":540}
        engine.header.hide()
        engine.setFixedHeight(400)  # Restore full dialog height.
        for widget in self.pages.values():
            widget.hide()
            widget.setParent(self.stack)
            widget.setWindowFlags(Qt.WindowType.Widget)
            widget.setFixedWidth(190)
            self.stack.addWidget(widget)
        self.stack.setFixedWidth(192)
        style_dock(self,engine,eq,fir,eq._action_row,fir._action_row)
        self.scroll.setWidget(self.stack)
        outer.addWidget(self.scroll)
        self.setFixedHeight(310)
    def select(self,mode):
        style_active_heading(self,mode)
        widget=self.pages[mode]
        if mode=="fir":
            self.page_heights[mode]=fit_fir_content(widget)
        self.stack.setFixedHeight(self.page_heights[mode])
        self.stack.setCurrentWidget(widget)
        self.scroll.verticalScrollBar().setValue(0)
        widget.show()
    def apply_rect(self,rect):
        x,y,w,h=rect
        # V8.58: dock geometry follows ONLY the Smaart viewport/screen.
        # Selection validity changes available buttons/cards, NOT the
        # outer height. The old invalid-phase 148px clamp could persist
        # across EQ -> Phase and truncate the two traces and Top 3 until
        # the user hid/reopened the panel.
        if self.width()!=w or self.height()!=h:
            self.setFixedSize(w,h)
        if self.x()!=x or self.y()!=y:
            self.move(x,y)
        self.set_compact(h<FULL_PAGE_H)
    def set_compact(self,compact):
        """V8.122: compact Auto Phase page when the full 400 px page plus
        heading does not fit (many TF engines); the rest scrolls."""
        engine=self.pages["phase"]
        if not hasattr(engine,"set_compact_layout"):
            return
        if not engine.set_compact_layout(compact):
            return
        height=engine.COMPACT_PAGE_H if compact else 400
        engine.setFixedHeight(height)
        self.page_heights["phase"]=height
        if self.stack.currentWidget() is engine:
            self.stack.setFixedHeight(height)
            self.scroll.verticalScrollBar().setValue(0)

class ToolHub(QWidget):
    """Small navigator at top; workspace dock below Smaart TF Engine."""
    def __init__(self,engine,license_badge="RemiX Duo",license_tooltip="License: UNKNOWN"):
        super().__init__(None)
        self.engine=engine
        from smaart_fs_sync_v841 import AsyncSavedFsCache
        self.engine._saved_fs_cache=AsyncSavedFsCache()
        self.engine.managed_mode=True
        self.engine.ui_tool_enabled=False
        self.eq=EQDialog(engine)
        self.engine._eq_tick_safe=self._eq_tick_safe
        self.eq.roi_range_changed=self.engine.set_eq_roi_range
        self.engine.eq_roi_drag_callback=self.eq.drag_roi_to
        self.engine.eq_peq_drag_callback=self.eq.drag_peq_marker
        self.engine.set_eq_roi_range(self.eq.lf.value(),self.eq.hf.value())
        self.fir=FIRDialog(engine)
        self.fir.range_changed=self.engine.set_fir_roi_range
        self.engine.fir_roi_drag_callback=self.fir.drag_roi_to
        self.engine.set_fir_roi_range(self.fir.fir_lf.value(),
                                      self.fir.fir_hf.value(),
                                      self.fir.fir_mode.currentData())
        self.dock=RightToolDock(engine,self.eq,self.fir)
        self.pages=self.dock.pages
        self.workspace_visible=True
        self.auto_hide_enabled=True
        self.dock.hide_btn.clicked.connect(self.hide_workspace)
        self.dock.live_btn.clicked.connect(self.return_to_tuning_live)
        self.dock.auto_hide_btn.toggled.connect(self._toggle_auto_hide)
        self.engine.overlay_workspace_visible=True
        self.engine.overlay_tool_mode="phase"
        self.native_eq=NativeAutoEQMag(self)
        self.native_fir=NativeFIROverlay(self)
        self.fir.preview_ready.connect(self.native_fir.accept)
        self.fir.preview_clear.connect(self.native_fir.clear)
        self.eq.native_ready.connect(self.native_eq.set_data)
        self.eq.native_clear.connect(self.native_eq.clear)
        self.eq.native_enabled.connect(self.native_eq.set_enabled)
        self.buttons={}
        self.active=None
        self._was_target=False
        self._last_pair_key=None
        self._last_host_rect=None
        self._last_hwnd=None
        self._anchors=None
        self._anchor_requested_at=0.
        self._anchor_future=None
        self._pending_anchor=None
        self._anchor_pool=ThreadPoolExecutor(max_workers=1)
        self._manually_placed=False
        self._drag_offset=None
        self.setObjectName("hub")
        self.setWindowTitle("RemiX Duo | Auto Phase · Auto EQ · Auto FIR")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # IMPORTANT: 3 buttons in ONE native row with Real Time / Impulse / SPL.
        # No title row (V8.15 used two rows and covered the plot header).
        # V8.31: extend LEFT of the existing 205px tool row; native buttons
        # retain their original absolute positions and usable widths.
        # A temporary minimum is replaced by the real font-metric width after
        # the active/inactive license label is constructed.  Fixed 250 px left
        # a large empty gap at 100% DPI and was still not universal across DPI.
        self._brand_width=128
        self._brand_extra=self._brand_width+3
        # Preserve the legacy 205px width until native Smaart row is located.
        self.setFixedSize(205,30)
        self.setStyleSheet(STYLE+"""
            QWidget#hub {background:#0C1A26;border:1px solid #33556B;}
            QWidget#remixBrand {background:#0C1A26;border:0;}
            QLabel#remixBrandLogo,QLabel#remixBrandText {background:transparent;border:0;}
            QLabel#remixBrandText {color:#F4FAFF;font:800 12px 'Segoe UI';}
        """)
        main=QHBoxLayout(self)
        main.setContentsMargins(2,1,2,1)
        main.setSpacing(3)
        # The logo is a real asset cropped from the supplied RemiX symbol,
        # not a screenshot overlay and not part of the Smaart application.
        self.brand_strip=QWidget(self)
        self.brand_strip.setObjectName('remixBrand')
        self.brand_strip.setFixedSize(self._brand_width,26)
        brand_row=QHBoxLayout(self.brand_strip)
        brand_row.setContentsMargins(1,0,1,0)
        brand_row.setSpacing(4)
        self.brand_icon=QLabel(self.brand_strip)
        self.brand_icon.setObjectName('remixBrandLogo')
        self.brand_icon.setFixedSize(24,24)
        logo=QPixmap(str(Path(__file__).resolve().parent/'remix_dou_swirl_toolbar32.png'))
        if logo.isNull():
            raise RuntimeError('RemiX Duo logo asset missing')
        self.brand_icon.setPixmap(logo.scaled(24,24,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.brand_text=QLabel(license_badge,self.brand_strip)
        self.brand_text.setObjectName('remixBrandText')
        self.brand_text.setToolTip(license_tooltip)
        self.brand_text.ensurePolished()
        required=(1+24+4+self.brand_text.sizeHint().width()+1+8)
        self._brand_width=min(280,max(128,required))
        self._brand_extra=self._brand_width+3
        self.brand_strip.setFixedSize(self._brand_width,26)
        brand_row.addWidget(self.brand_icon)
        brand_row.addWidget(self.brand_text)
        main.addWidget(self.brand_strip)
        self.brand_strip.hide()  # expanded only by _update_placements
        self.nav_frame=self
        self.title_bar=None
        self._toolbar_mode="full"
        self._panel_mode="dock"
        self._last_anchor_good=None
        # Three primary tools only. EQ export remains in the Auto EQ panel.
        for mode,label in (("phase","Auto Phase"),
                           ("eq","Auto EQ"),
                           ("fir","Auto FIR")):
            button=QPushButton(label)
            button.setMinimumHeight(27)
            button.setMaximumHeight(28)
            button.setToolTip(f"RemiX Duo · {label}")
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _,m=mode:self.select(m))
            button.setObjectName("tool_"+mode)
            main.addWidget(button,1)
            self.buttons[mode]=button
        # Resized mode: compact labels or a real clickable menu button.
        self.menu_button=QPushButton("Duo ▾")
        self.menu_button.setObjectName("responsiveMenu")
        self.menu_button.setToolTip("RemiX Duo — chọn công cụ")
        menu=QMenu(self.menu_button)
        for mode,label in (("phase","Auto Phase"),("eq","Auto EQ"),
                           ("fir","Auto FIR")):
            action=menu.addAction(label)
            action.triggered.connect(lambda _,m=mode:self.select(m))
        self.menu_button.setMenu(menu)
        main.addWidget(self.menu_button)
        self.menu_button.hide()
        self.eq._native_guard=self.native_eq
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._menu=QMenu(self)
        self.license_action=self._menu.addAction(license_badge)
        self.license_action.setToolTip(license_tooltip)
        self.license_action.setEnabled(False)
        self._menu.addSeparator()
        self._menu.addAction("Đóng RemiX Duo",self.close)
        self.customContextMenuRequested.connect(
            lambda pos:self._menu.exec(self.mapToGlobal(pos)))
        self._set_toolbar_mode("full")
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.select("phase")
        self.timer.start(175)
        self.follow_timer=QTimer(self)
        self.follow_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.follow_timer.timeout.connect(self._fast_follow)
        self.follow_timer.start(16)
        # wait for native button anchors; do not flash in screen center
        self.hide()
        self.dock.hide()
    def _menu_style(self,tool):
        colors={"phase":("#58E89A","#061A13"),
                "eq":("#FFA34C","#201105"),
                "fir":("#62DFFA","#07202A"),"remote":("#64DFEF","#07202A")}
        bg,fg=colors.get(tool,("#173447","#D3EDFA"))
        return (f"font:700 9px 'Segoe UI';min-height:22px;"
                f"background:{bg};color:{fg};border:1px solid #456D83;"
                "border-radius:6px;")

    def _set_toolbar_mode(self,mode):
        if mode not in ("full","compact","mini","menu"):
            raise ValueError("Unknown responsive mode")
        self._toolbar_mode=mode
        labels={
            "full":("Auto Phase","Auto EQ","Auto FIR"),
            "compact":("A.Phase","A.EQ","A.FIR"),
            "mini":("AP","EQ","FIR")
        }
        if mode=="menu":
            for button in self.buttons.values():button.hide()
            self.menu_button.show()
            self.menu_button.setText("Duo ▾")
            self.menu_button.setStyleSheet(self._menu_style(self.active))
        else:
            self.menu_button.hide()
            for (name,button),text in zip(self.buttons.items(),labels[mode]):
                button.setText(text)
                button.setMinimumWidth(0)
                button.show()
        # In compact mode, the current tool remains selected; only
        # its presentation changes. Do not reset Auto Phase/EQ/FIR data.
        self._style_buttons()

    def _style_buttons(self):
        # Stable three-tool hierarchy: inactive navy, active color per tool.
        accents={"phase":("#58E89A","#061A13"),
                 "eq":("#FFA34C","#201105"),
                 "fir":("#62DFFA","#07202A"),"remote":("#64DFEF","#07202A")}
        for mode,button in self.buttons.items():
            color,ink=accents[mode]
            active=(mode==self.active)
            bg=color if active else "#102736"
            border=color if active else "#375467"
            fg=ink if active else "#CAE4ED"
            button.setStyleSheet(
                "QPushButton {font:700 9px 'Segoe UI';min-width:0px;"
                "min-height:23px;margin:0px;padding:1px 3px;"
                f"background:{bg};color:{fg};border:1px solid {border};"
                "border-radius:6px;}"
                f"QPushButton:hover {{background:{color};color:{ink};}}"
                "QPushButton:pressed {padding-top:2px;}"
            )

    def _eq_tick_safe(self):
        """Display-only short transient gate; NEVER used to authorize export.

        A changed tick/trace, missing candidate or ambiguous count fails
        immediately.  Native pixel identity and viewport freshness are
        still independently required by the native MagEQ renderer.
        """
        from mageq_presentation_gate_v853 import presentation_tick_ok
        observer=getattr(self.engine,"observer",None)
        token=getattr(self.eq,"_single_token",None)
        last=getattr(self,"_eq_last_verified_at",0.)
        safe,at,reason=presentation_tick_ok(observer,token,last)
        self._eq_last_verified_at=at
        self._eq_display_gate_reason=reason
        return safe
    def open_export_from_bar(self):
        self.select("eq")
        self.eq.export_eq()

    def _toggle_auto_hide(self,enabled):
        self.auto_hide_enabled=bool(enabled)
        self.dock.auto_hide_btn.setChecked(bool(enabled))

    def _disable_model_overlays(self):
        # Hide every RemiX renderer. No change to Smaart trace data.
        self.engine.overlay_workspace_visible=False
        self.engine.ui_tool_enabled=False
        self.engine.refresh_visibility()
        self.native_eq.hide()
        self.native_eq._sync_sum_renderer()
        self.native_fir.frame=None
        self.native_fir._publish()
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
        key=(tuple(self.engine.current_pair or ()),
             tuple(id(t) for t in (self.engine.current_traces or ())))
        if key!=self._last_pair_key:
            self._last_pair_key=key
            self.fir.refresh_sources()
        self.eq.refresh_sources()
        self.active=mode
        self.engine.overlay_tool_mode=mode
        self.engine.overlay_workspace_visible=True
        if mode=="fir":
            self.engine.set_fir_roi_range(self.fir.fir_lf.value(),
                                          self.fir.fir_hf.value(),
                                          self.fir.fir_mode.currentData())
        if self._toolbar_mode=="menu":
            self.menu_button.setStyleSheet(self._menu_style(mode))
        if mode!="eq":
            self.native_eq.hide()
            self.engine.graph_mag.set_mageq()
        if mode!="fir":
            self.native_fir.frame=None
            self.native_fir._publish()
        self.engine.ui_tool_enabled=(mode=="phase")
        # SUM and MagEq are exclusive preview modes: do not superimpose
        # two model curves of the same lime color in the Smaart Mag plot.
        self.engine.refresh_visibility()
        self.dock.select(mode)
        self._style_buttons()
        if self._last_host_rect is not None:
            # Fall back to Smaart host rect when native UIA anchors are
            # temporarily unavailable; re-opening after HIDE must work.
            self._update_placements(self._last_host_rect)
    def _screen_rect(self):
        # Use the monitor containing Smaart rather than primary monitor
        # when the user drags Smaart to another display.
        if self._last_host_rect:
            x1,y1,x2,y2=self._last_host_rect
            screen=QApplication.screenAt(QPoint((x1+x2)//2,(y1+y2)//2))
        else:
            screen=None
        r=(screen or QApplication.primaryScreen()).availableGeometry()
        return (r.left(),r.top(),r.right()+1,r.bottom()+1)
    def _update_placements(self,host):
        # Even when Smaart temporarily loses UIA anchors we provide
        # a visible fallback menu on the same approximate native row.
        edition=getattr(self,'_last_host_edition',None)
        if edition==8:
            # Native V8 TF controls differ from V9, including the Tab row.
            # Do NOT use V9 UIA anchors, toolbar collapse or dock fallback.
            from smaart8_native_sidebar_v870 import v8_sidebar_rects,V8Slot
            slot=self._anchors if isinstance(self._anchors,V8Slot) else None
            rects=v8_sidebar_rects(host,self._screen_rect(),slot)
        else:
            rects=compute_dock_rects(host,self._anchors,self._screen_rect())
        if rects is None:
            # Degenerate/minimized host only; tick handles minimized.
            self.hide()
            self.dock.hide()
            return False
        x,y,w,h=rects.toolbar
        if self._toolbar_mode!=rects.toolbar_mode:
            self._set_toolbar_mode(rects.toolbar_mode)
        # Keep original buttons at x..x+w and put brand at x-brand_extra.
        # Skip the brand only in an extremely narrow/hidden native-menu row.
        sl,_,_,_=self._screen_rect()
        show_brand=(rects.toolbar_mode!='menu' and
                    x-self._brand_extra>=sl+3)
        self.brand_strip.setVisible(show_brand)
        extra=self._brand_extra if show_brand else 0
        self.setFixedSize(w+extra,h)
        self.move(x-extra,y)
        if not self.isVisible():self.show()
        self._panel_mode=rects.panel_mode
        # Placement stays in the tooltip; DOCK/OVERLAP in this compact title
        # was clipped behind AUTO/LIVE/HIDE and added no actionable value.
        px,py,pw,ph=rects.panel
        if self._panel_mode=="no-native-space":
            self.dock.hide()
            return True
        self.dock.apply_rect((px,py,pw,ph))
        self._layout_tier=getattr(rects,"layout_tier","dock")
        self.dock.heading.setToolTip(
            "Panel: "+self._panel_mode+" | "+self._layout_tier+
            " | Kéo nội dung để cuộn")
        if self.workspace_visible:
            if not self.dock.isVisible():self.dock.show()
        else:
            self.dock.hide()
        return True

    def _fast_follow(self):
        """Geometry-only GUI tick: no UIA, file reads or trace calculations."""
        hwnd=self._last_hwnd
        if not hwnd or not win32gui.IsWindow(hwnd):
            return
        if win32gui.IsIconic(hwnd) or not self.engine._target_is_foreground(hwnd):
            if self.isVisible():self.hide()
            if self.dock.isVisible():self.dock.hide()
            return
        rect=win32gui.GetWindowRect(hwnd)
        if rect!=self._last_host_rect:
            self._last_host_rect=rect
            self._update_placements(rect)

    def tick(self):
        pair=(tuple(self.engine.current_pair or ()),
              tuple(id(t) for t in (self.engine.current_traces or ())))
        if pair!=self._last_pair_key:
            self._last_pair_key=pair
        # V8.156: FIR is refreshed once below on EVERY 175-ms slow tick.
        # A transient SUM/overlay object ID change must not trigger an
        # extra synchronous FIR source/FS check in the GUI thread.
        self.eq.refresh_sources()
        self.eq._refresh_export_gate()
        state=getattr(self.eq,"native_state",None)
        if state is not None:
            graph=self.engine.graph_mag
            rendered=getattr(graph,"mageq_frame",None)
            if self.eq.result is None:
                label="MagEQ: Cho Auto EQ"
            elif self.eq._verified_single() is None:
                label="MagEQ HOLD: Cho xac minh tick Trace"
            elif (rendered is not None and
                  rendered is self.native_eq.frame and
                  self.native_eq._source_binding_ok()):
                label=(f"MagEQ LIVE: {rendered.color.upper()} "
                       f"{rendered.fit.score:.0%} pixel")
            elif self.native_eq.source is None:
                label="MagEQ HOLD: Trace chua duoc gan"
            else:
                label="MagEQ HOLD: Native pixel/Y khong khop hoac het han"
            if state.text()!=label:state.setText(label)
        self.fir.refresh_sources()
        self.fir._refresh_export()
        target=locate_smaart(prefer_hwnd=(
            getattr(self,"_last_hwnd",None) or getattr(self.engine.observer,"hwnd",None)))
        active=bool(target and self.engine._target_is_foreground(target.hwnd))
        if not active:
            observer=getattr(self.engine,"observer",None)
            # V8.156: foreground loss is not a trace/source change.
            # Suspend the native 3/3 proof, retaining only the immutable
            # candidate and its generation. New EQ/FIR compute and export
            # remain locked until three fresh valid tick observations.
            # A missing/different Smaart host still invalidates strictly.
            if observer is not None:
                bound_hwnd=int(getattr(observer,"hwnd",0) or 0)
                # With both Smaart editions open, locate_smaart() may
                # select a DIFFERENT background host by z-order when Chrome
                # is foreground. Verify our bound HWND independently.
                bound_alive=(bound_hwnd and win32gui.IsWindow(bound_hwnd) and
                             getattr(observer,"ready",False))
                other_active=(target is not None and
                              getattr(target,"foreground",False) and
                              target.hwnd!=bound_hwnd)
                if bound_alive and not other_active and hasattr(observer,"suspend_single_transient"):
                    observer.suspend_single_transient()
                elif hasattr(observer,"invalidate_single"):
                    observer.invalidate_single()
            self.eq.refresh_sources()
            self.native_eq.hide()
            # A previously verified pair must NOT be displayed immediately
            # on return from a minimized/background Smaart. Re-arm 3/3
            # native viewport snapshots before SUM and Auto Phase reappear.
            if self._was_target:
                self.engine.tick_gate.signature=None
                self.engine.tick_gate.stable=0
                self.engine._selection_quality="transient"
                self.engine._set_tick_presentation(False)
                self.engine.selection_warning.setText(
                    "Đang xác minh Trace sau khi trở lại Smaart")
                self.engine.selection_warning.show()
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
            self.engine.refresh_visibility()
        rect=win32gui.GetWindowRect(target.hwnd)
        previous_rect=self._last_host_rect
        if target.hwnd!=self._last_hwnd:
            from smaart8_api3_readonly_v868 import process_smaart_major
            self._last_host_edition=process_smaart_major(target.hwnd)
            self._last_anchor_good=None
            self._anchors=None
            self._last_hwnd=target.hwnd
            self._anchor_requested_at=0.
        anchor_changed=False
        previous_anchors=self._anchors
        if self._anchor_future is not None and self._anchor_future.done():
            try:
                latest=self._anchor_future.result()
                accepted,self._pending_anchor=stable_anchor_sample(
                    self._anchors,self._pending_anchor,latest)
                anchor_changed=(accepted!=self._anchors)
                # A transient UIA failure must not make the whole
                # companion disappear. Retain last recognized row.
                if accepted is not None:
                    self._last_anchor_good=accepted
                    self._anchors=accepted
                else:
                    self._anchors=self._last_anchor_good
                anchor_changed=(self._anchors!=previous_anchors)
            except Exception:
                self._anchors=self._last_anchor_good
                anchor_changed=(self._anchors!=previous_anchors)
            self._anchor_future=None
        now=time.monotonic()
        if self._anchor_future is None and now-self._anchor_requested_at>0.8:
            self._anchor_requested_at=now
            if getattr(self,'_last_host_edition',None)==8:
                # V8.120: Smaart 8 has no UIA tree; measure the free TF
                # sidebar slot below the real engine boxes from pixels.
                from smaart8_native_sidebar_v870 import read_v8_slot
                self._anchor_future=self._anchor_pool.submit(read_v8_slot,target.hwnd)
            else:
                self._anchor_future=self._anchor_pool.submit(read_smaart_anchors,target.hwnd)
        # The native Smaart chrome is the positional authority.
        # Re-anchor every time Smaart moves/resizes, or UIA anchors change.
        # No manual float override: the three buttons ALWAYS share its row.
        self._last_host_rect=rect
        if (anchor_changed or not self._was_target or
            rect!=previous_rect or not self.isVisible() or
            (self.workspace_visible and not self.dock.isVisible())):
            self._update_placements(rect)
        self._was_target=True
    def closeEvent(self,event):
        # V8.119: every Duo window is a Qt.Tool window, so Qt never quit the
        # app on "Đóng RemiX Duo": the process lived on with stale overlays
        # (live: SUM / LF-HF painted over Chrome). Hide everything first,
        # clean up best-effort, then always quit the event loop.
        try:
            from duo_lifecycle_v8142 import mark_clean
            mark_clean()
            self._disable_model_overlays()
        except Exception as exc:
            print("V8119_CLOSE_HIDE_ERROR",exc,flush=True)
        try:
            self.timer.stop()
            self.follow_timer.stop()
            self.native_eq.stop()
            self.native_fir.close()
            self.eq._serial+=1
            from worker_lifecycle_v8142 import bounded_shutdown
            bounded_shutdown(self.eq._pool)
            self.fir._serial+=1
            bounded_shutdown(self.fir._pool)
            bounded_shutdown(self._anchor_pool)
            cache=getattr(self.engine,"_saved_fs_cache",None)
            if cache is not None:cache.close()
            self.dock.hide()
            self.engine.ui_tool_enabled=False
            self.engine.managed_mode=False
            self.engine.close()
            self.dock.close()
        except Exception as exc:
            print("V8119_CLOSE_CLEANUP_ERROR",exc,flush=True)
        finally:
            event.accept()
            app=QApplication.instance()
            if app is not None and getattr(self,"quit_app_on_close",True):
                QTimer.singleShot(0,app.quit)

# Frozen QA provenance; NOT a license override or changed DSP.
EQ_EXPORT_R4_FROZEN_BUILD_TAG = "REMIX_DUO_EQ_EXPORT_R4_NATIVE_PROOF_WAIT_20261121"
