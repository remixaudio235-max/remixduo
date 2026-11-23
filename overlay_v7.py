"""RemiX Auto Align V7 Windows - independent transparent SUM Phase/Mag overlay.

QA demo: py overlay_v7.py --demo
Live:    py overlay_v7.py  (safe/fail-closed until DataBar identity map verified)
This is a companion window, not original Smaart plugin or renderer parity.
"""
from __future__ import annotations
import argparse,concurrent.futures,sys,time,os
# pywinauto/pythoncom otherwise defaults the importing (GUI) thread to MTA.
# QApplication later needs OLE/STA; changing an already initialized apartment
# fails with RPC_E_CHANGED_MODE and Qt6Core fast-fails on button interaction.
if sys.platform == "win32":
    sys.coinit_flags = 2  # COINIT_APARTMENTTHREADED, before every UIA import.
from dataclasses import replace
from PyQt6 import sip
from types import SimpleNamespace
from pathlib import Path
import numpy as np
import win32gui,win32con,win32process,win32api
from worker_lifecycle_v8142 import bounded_shutdown
from PyQt6.QtCore import Qt,QTimer,pyqtSignal,QObject,QRectF,QPointF,QUrl
from PyQt6.QtGui import (QColor,QPen,QPainter,QPainterPath,QPixmap,QCursor,QImage,
                         QDesktopServices)
from PyQt6.QtWidgets import (QApplication,QWidget,QPushButton,QLabel,
    QCheckBox,QDoubleSpinBox,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,
    QTabWidget,QSizePolicy,QMessageBox)
from trf_core import synthetic,compute_sum,auto_align,read_trf,SumTrace,phase_match_percent,sum_ref_phase_delta
from remix_duo.core.align_confidence import assess_alignment
from selection_v7 import SelectionController
from win_databar_v7 import locate_smaart
from live_sync_v7 import LiveDataBarV7, SyncResult
from stable_ticks_v824 import StableTickGate
from remix_duo.core.traces import with_gain_db,TRACE_GAIN_LIMIT_DB
from remix_duo import __version__
from remix_duo.platforms.paths import app_paths
from remix_duo.update.github_release import (check_for_update,valid_release_url,
                                              ReleaseResult)
SUM_PEN_WIDTH=3.5
OFFSET_APPLY_DB=0.3   # V8.116 hysteresis for auto-measured trace offsets


def _selection_now():
    """Monotonic clock for the V8.107 tick re-arm display bridge (test hook)."""
    return time.monotonic()


def _native_pan_min_interval(active_kind):
    """V8.161: fast during a real Y gesture; low-rate passive wheel check."""
    return .025 if active_kind in ("phase","mag") else .18
from plot_geometry_v7 import locate_plots
from plot_role_v812 import locate_role_plots
from smaart_axes_v71 import read_saved_axes
from tf_display_smoothing import SMOOTH_OPTIONS
from smaart_smooth_sync_v811 import read_saved_smooth
from roi_markers_v73 import ROIMarker, ROILineGrip, hz_to_x, x_to_hz, bound_drag
from peq_marker_drag_v851 import PEQMarkerGrip
from phase_axis_follow_v77 import (capture_native_phase,
    detect_vertical_shift,shifted_y_range)
from passive_phase_y_v78 import NativeAxisFollower
from phase_axis_absolute_v79 import capture_fit,AxisFit
from fast_phase_y_v80 import capture_fit_fast,FastFitResult
from native_fast_pan_v81 import NativeFastPan,PanFrame
from native_dual_y_v82 import NativeDualFastPan,DualPanResult,native_pan_poll_interval
from axis_y_sync_v828 import trusted_pan,translated_y_range
from mag_sum_native_v826 import capture_sum_mag_axis,SumMagAxis
from sum_render_v84 import make_geometry
from positive_delay_route_v87 import route_candidate

DIR=Path(__file__).resolve().parent
from smaart_discovery_v875 import trace_folder as _smaart_trace_folder
SMAART_TRF=_smaart_trace_folder(9)  # Windows Known Documents (OneDrive-safe)
class Events(QObject):
    loaded=pyqtSignal(int,object,object,object)
    found=pyqtSignal(object)
    layout_ready=pyqtSignal(object)
    axis_snapshot=pyqtSignal(object)
    pan_snapshot=pyqtSignal(object)
    mag_anchor_ready=pyqtSignal(object)
    aligned=pyqtSignal(int,object,object)
    trace_offsets=pyqtSignal(object)
    live_smooth=pyqtSignal(object)
    update_ready=pyqtSignal(object)

class SumGraph(QWidget):
    def __init__(self,kind):
        super().__init__(None)
        self.kind=kind
        self.data:SumTrace|None=None
        self.mageq_source=None
        self.mageq_frame=None
        self.fir_source=None
        self.fir_frame=None
        # Editable FIR band is independent of Auto Phase and the last FIR preview.
        self.fir_roi_active=False
        self.fir_lf_hz=500.0
        self.fir_hf_hz=2500.0
        self._fir_raster_id=None
        self._fir_raster_qimage=None
        self.mageq_draw_count=0
        # The native Mag overlay must remain Windows click-through. Hover
        # labels are driven by passive cursor samples, never Qt mouse events.
        self._hover_number=None
        self._hover_markers=()
        self._hover_timer=QTimer(self)
        self._hover_timer.setInterval(75)
        self._hover_timer.timeout.connect(self._poll_mageq_hover)
        self.label=f"SUM {kind.upper()} (MODEL - Y do RemiX chon)"
        self.theme="dark"
        self.f_min=20.
        self.f_max=20000.
        self.y_min,self.y_max=(-180.,180.) if kind=="phase" else (-18.,18.)
        self.draw_count=0
        self._paint_cache=None
        self._cache_rebuilds=0
        self.display_offset_db=0.0
        self.require_native_axis=False
        self.native_axis_ready=False
        self.require_native_x_axis=False
        self.native_x_axis_ready=True
        self.native_axis_label=""
        self.lf_hz=60.0
        self.hf_hz=200.0
        self.roi_guides=True
        self.eq_roi_active=False
        self.eq_lf_hz=60.0
        self.eq_hf_hz=8000.0
        self.phase_match_value=None
        self.phase_match_bins=0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        flags=(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool|
               Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowTransparentForInput)
        self.setWindowFlags(flags)
        self.resize(500,300)
        self.hide()

    def _poll_mageq_hover(self):
        if (self.kind!="mag" or not self.isVisible() or
                not self.eq_roi_active or self.mageq_source is None or
                self.mageq_frame is None):
            number=None
        else:
            from mageq_visual_v13 import marker_hover_at
            local=self.mapFromGlobal(QCursor.pos())
            number=marker_hover_at(self._hover_markers,
                                   local.x(),local.y())
        # Only repaint on an actual hover transition, not each cursor poll.
        if number!=self._hover_number:
            self._hover_number=number
            self.update()

    def set_data(self,value:SumTrace|None):
        self.data=value
        self._paint_cache=None
        self.update()

    def set_mageq(self,source=None,frame=None):
        """One MagEq on native Magnitude; SUM state remains intact."""
        if self.kind!="mag":return
        if source is None or frame is None or frame.revision!=source.revision:
            source=frame=None
        old=self.mageq_source
        if (source is None or old is None or
            old.revision!=source.revision or
            old.source_identity!=source.source_identity):
            self._hover_number=None
            self._hover_markers=()
        self.mageq_source=source
        self.mageq_frame=frame
        if source is None:
            self._hover_timer.stop()
        elif not self._hover_timer.isActive():
            self._hover_timer.start()
        self.update()

    def set_fir(self,source=None,frame=None):
        """FIR presentation shares the existing two native plot widgets."""
        if source is None or frame is None or frame.source_identity!=source.identity:
            source=frame=None
        if self.fir_source is source and self.fir_frame is frame:return
        self.fir_source,self.fir_frame=source,frame
        self._fir_raster_id=None
        self._fir_raster_qimage=None
        self.update()

    def _paint_fir_guide(self,p):
        """Working range is an edit guide, NOT a computed FIR response."""
        lf,hf=self.fir_lf_hz,self.fir_hf_hz
        if not (20<=lf<hf<=20000 and hf>=2*lf):return
        w,h=self.width(),self.height()
        x1=hz_to_x(lf,0,w,self.f_min,self.f_max);x2=hz_to_x(hf,0,w,self.f_min,self.f_max)
        p.save()
        p.fillRect(QRectF(x1,0,x2-x1,h),QColor(20,205,230,24))
        for x,c in ((x1,QColor("#42eab6")),(x2,QColor("#ffaf54"))):
            p.setPen(QPen(c,1.8,Qt.PenStyle.DashLine))
            p.drawLine(int(x),0,int(x),h)
        p.restore()

    def _paint_fir_range(self,p,src,w,h):
        # The range belongs to the immutable FIR preview, never the current UI.
        lo,hi=float(src.range_lf),float(src.range_hf)
        if not (20<=lo<hi<=20000):return
        scale=lambda hz: max(0,min(w,int(w*np.log(hz/self.f_min)/
                                   np.log(self.f_max/self.f_min))))
        x1,x2=scale(lo),scale(hi)
        p.save()
        p.fillRect(x1,0,max(0,x2-x1),h,QColor(20,205,230,20))
        p.setPen(QPen(QColor(40,218,240,180),1,Qt.PenStyle.DashLine))
        p.drawLine(x1,0,x1,h)
        p.drawLine(x2,0,x2,h)
        p.restore()

    def _paint_fir(self,p):
        from fir_native_v846 import fir_mag_points,fir_phase_points
        src,frame=self.fir_source,self.fir_frame
        if src is None or frame is None:return
        if self.kind=="phase" and not frame.phase_verified:return
        rect=frame.phase if self.kind=="phase" else frame.mag
        if self.geometry().getRect()!=rect:return
        _,_,w,h=rect
        raster=(frame.phase_raster if self.kind=="phase"
                else frame.mag_raster)
        if raster is not None:
            key=(id(frame),self.kind)
            if key!=self._fir_raster_id:
                self._fir_raster_qimage=QImage(
                    raster,int(w),int(h),int(w)*4,
                    QImage.Format.Format_RGBA8888).copy()
                self._fir_raster_id=key
            p.drawImage(0,0,self._fir_raster_qimage)
            self._paint_fir_range(p,src,w,h)
            p.setPen(QColor("#DAA5FF") if self.kind=="phase"
                     else QColor("#49E4FF"))
            p.drawText(100,20,
                       ("PhaseFIR" if self.kind=="phase" else "MagFIR")+
                       f"  [{src.source_name}] {src.taps} taps | PREVIEW")
            return
        # Legacy QA/synthetic fallback; live workers always supply rasters.
        dots,trust=(fir_phase_points(src,frame) if self.kind=="phase"
                    else fir_mag_points(src,frame))
        if len(dots)<2:return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        p.setClipRect(QRectF(0,0,float(w),float(h)))
        path=QPainterPath()
        prev=None
        for (xx,yy),valid in zip(dots,trust):
            if not valid or not np.isfinite(xx) or not np.isfinite(yy) or (
                xx<0 or xx>w or yy<0 or yy>h):
                prev=None
                continue
            # Suppress false lines across a wrapped +/-180-degree boundary.
            if prev is None or xx-prev[0]>20 or (
                    self.kind=="phase" and abs(yy-prev[1])>h*.45):
                path.moveTo(float(xx),float(yy))
            else:path.lineTo(float(xx),float(yy))
            prev=(xx,yy)
        color=QColor("#DAA5FF") if self.kind=="phase" else QColor("#49E4FF")
        p.setPen(QPen(color,2.3,Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        p.setClipping(False)
        self._paint_fir_range(p,src,w,h)
        p.setPen(color)
        p.drawText(100,20,("PhaseFIR" if self.kind=="phase" else "MagFIR")+
                   f"  [{src.source_name}]  {src.taps} taps | PREVIEW")
        p.restore()

    def _paint_mageq(self,p):
        from smaart_native_mag_fit import native_points
        from mageq_visual_v13 import (build_geometry,draw_gradient,draw_markers,
            MAGEQ_LINE,MAGEQ_LINE_WIDTH,MAGEQ_HALO_WIDTH)
        src,frame=self.mageq_source,self.mageq_frame
        if src is None or frame is None:return
        rect=frame.plot
        if self.geometry().getRect()!=rect:return
        x,y,w,h=rect
        from native_eq_mag_v06 import _display_db
        pts,valid=native_points(rect,frame.fit,src.freqs,
             _display_db(src,src.after_db),src.coh,
             expect_x_min=getattr(frame,"x_min",20.),
             expect_x_max=getattr(frame,"x_max",20000.))
        if len(pts)<2:return
        pts[:,0]-=x;pts[:,1]-=y
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        p.setClipRect(QRectF(0.,0.,float(w),float(h)))
        bypass=not bool(src.peqs)
        if not bypass:
            try:
                mag_geometry=build_geometry(src,frame)
            except ValueError:
                return
        else:
            mag_geometry=None
        gradient_spans=0 if bypass else draw_gradient(p,mag_geometry)
        for trusted in (False,True):
            line=QPainterPath()
            previous=None
            for (xx,yy),good in zip(pts,valid):
                xx=float(xx);yy=float(yy)
                if bool(good)!=trusted or not(np.isfinite(xx) and np.isfinite(yy)):
                    previous=None
                    continue
                if previous is None or xx-previous>23:
                    line.moveTo(xx,yy)
                else:line.lineTo(xx,yy)
                previous=xx
            style=(Qt.PenStyle.DashLine if bypass else Qt.PenStyle.SolidLine)
            if trusted:
                p.setPen(QPen(QColor(3,8,12,205),MAGEQ_HALO_WIDTH,style,
                    Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
                p.drawPath(line)
            color=QColor(MAGEQ_LINE)
            if not trusted:color.setAlpha(135)
            p.setPen(QPen(color,2.0 if not trusted else MAGEQ_LINE_WIDTH,
                style,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            p.drawPath(line)
        # PEQ marker positions follow the current frame/viewport. Passive
        # cursor polling chooses at most one marker for F/G/Q details.
        self._hover_markers=() if bypass else mag_geometry.markers
        markers,labels=(0,0) if bypass else draw_markers(
            p,mag_geometry,hover_number=self._hover_number)
        self.mageq_annotation_stats=dict(
            gradients=gradient_spans,markers=markers,labels=labels,
            total_peq=len(src.peqs),revision=src.revision)
        p.setClipping(False)
        p.setPen(QColor("#FFE0A7"))
        native_basis=("0 dB GRID" if frame.color=="GRID" else
                      f"native {frame.color.upper()}")
        p.drawText(100,22,
             (f"MagEq BYPASS [{src.source_name}] | 0 PEQ | "
              if bypass else
              f"MagEq [{src.source_name}] {len(src.peqs)} PEQ | ")+
             f"{native_basis} {frame.fit.score:.0%} | KHONG GHI DSP")
        self.mageq_draw_count+=1

    def _paint_eq_roi(self,p):
        # Independent X-only EQ selection, never an Auto Phase SUM.
        if self.kind!="mag" or not self.eq_roi_active:return
        lf,hf=self.eq_lf_hz,self.eq_hf_hz
        w,h=self.width(),self.height()
        if not (self.f_min<=lf<hf<=self.f_max and w>0 and h>0):return
        a=hz_to_x(lf,0,w,self.f_min,self.f_max)
        b=hz_to_x(hf,0,w,self.f_min,self.f_max)
        p.fillRect(QRectF(a,0.,b-a,float(h)),QColor(255,177,46,20))
        for xpos,col in ((a,QColor("#42eab6")),(b,QColor("#ffaf54"))):
            p.setPen(QPen(col,1.8,Qt.PenStyle.DashLine))
            p.drawLine(QPointF(xpos,0.),QPointF(xpos,float(h)))
        # Labels sit on the two draggable line heads, not in the plot body.

    def _viewport_paths(self,data,width,height,values,trusted):
        """Build native SUM topology only when TF, zoom/span or size changes.

        Magnitude: prepare a broad 7-height vertical canvas once and
        translate it over the current Y viewport. Phase (360-degree
        wrap): prepare exactly one wrapped period and tile the SAME
        segments at 2 offsets. This preserves proper split-at-wrap paths
        without a full Python 4096-edge rebuild per 16ms pointer move.
        """
        span=float(self.y_max-self.y_min)
        if span<=0:return None,()
        periodic=(self.kind=="phase" and 350.<=span<=370.)
        key=(id(data),self.kind,int(width),int(height),
             round(self.f_min,7),round(self.f_max,7),
             round(self.display_offset_db,7),round(span,7),periodic,self.theme)
        cached=self._paint_cache
        if cached is not None and cached["key"]==key:
            delta=(self.y_max-cached["anchor_top"])*height/span
            if periodic:
                y_shift=delta%height
                return cached,(y_shift-height,y_shift)
            if abs(delta)<=2.7*height:
                return cached,(cached["origin_shift"]+delta,)
        if periodic:
            y_lo,y_hi=self.y_min,self.y_max
            build_h=height
            origin_shift=0
        else:
            y_lo=self.y_min-3.*span
            y_hi=self.y_max+3.*span
            build_h=7*height
            origin_shift=-3*height
        geometry=make_geometry(data.hz,values,trusted,
                               self.f_min,self.f_max,
                               y_lo,y_hi,width,build_h,self.kind)
        paths={"high":QPainterPath(),"low":QPainterPath()}
        last_end={"high":None,"low":None}
        subpath_count=0
        for edge in geometry.edges:
            path=paths[edge.quality]
            previous=last_end[edge.quality]
            if (previous is None or
                abs(previous[0]-edge.x0)>1e-4 or
                abs(previous[1]-edge.y0)>1e-4):
                path.moveTo(edge.x0,edge.y0)
                subpath_count+=1
            path.lineTo(edge.x1,edge.y1)
            last_end[edge.quality]=(edge.x1,edge.y1)
        # Cache already-antialiased trace as a transparent bitmap.
        # The following Y-only pan paints 1-2 pixmaps rather than
        # stroking 4000+ QPainterPath segments at every 16ms tick.
        surface=QPixmap(int(width),int(build_h))
        surface.fill(Qt.GlobalColor.transparent)
        raster=QPainter(surface)
        for quality in ("low","high"):
            raster.setRenderHint(QPainter.RenderHint.Antialiasing,True)
            # V8.115 (user request): every measured SUM bin is drawn with
            # the same solid 3.5 px pen; unmeasured bins are NaN (not drawn).
            # Neon on dark; deep green on light (legible against white).
            color=QColor("#006F3C" if self.theme=="light" else "#39FF14")
            raster.setPen(QPen(color,SUM_PEN_WIDTH,
                             Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                             Qt.PenJoinStyle.RoundJoin))
            raster.drawPath(paths[quality])
        raster.end()
        cached={"key":key,"paths":paths,"anchor_top":self.y_max,
                "origin_shift":origin_shift,"geometry":geometry,
                "subpath_count":subpath_count,"trace_bitmap":surface}
        self._paint_cache=cached
        self._cache_rebuilds+=1
        return cached,((origin_shift,) if not periodic
                       else (-height,0))

    def showEvent(self,event):
        super().showEvent(event)
        hwnd=int(self.winId())
        ex=win32gui.GetWindowLong(hwnd,win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd,win32con.GWL_EXSTYLE,
           ex|win32con.WS_EX_TRANSPARENT|win32con.WS_EX_LAYERED|win32con.WS_EX_NOACTIVATE)

    def paintEvent(self,event):
        self.draw_count+=1
        if self.fir_roi_active:
            painter=QPainter(self)
            if self.fir_source is not None and self.fir_frame is not None:
                self._paint_fir(painter)
            else:
                self._paint_fir_guide(painter)
            painter.end()
            return
        if self.fir_source is not None and self.fir_frame is not None:
            painter=QPainter(self)
            self._paint_fir(painter)
            painter.end()
            return
        if self.kind=="mag" and self.eq_roi_active:
            painter=QPainter(self)
            if self.mageq_source is not None:
                self._paint_mageq(painter)
            self._paint_eq_roi(painter)
            painter.end()
            return
        if self.kind=="mag" and self.mageq_source is not None:
            painter=QPainter(self)
            self._paint_mageq(painter)
            painter.end()
            return
        if self.data is None:return
        # Smaart 8's native TF X span is NOT always 20Hz..20kHz.
        # Show no misleading SUM PHASE before current native X is proven.
        if (self.kind=="phase" and self.require_native_x_axis and
                not self.native_x_axis_ready):
            painter=QPainter(self)
            painter.setPen(QColor("#ffbd61"))
            painter.drawText(80,19,"SUM PHASE: CHO X NATIVE XAC MINH")
            painter.end()
            return
        native_y_hold=(self.kind=="mag" and self.require_native_axis
                       and not self.native_axis_ready)
        d=self.data
        w,h=self.width(),self.height()
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        if self.roi_guides and self.f_min <= self.lf_hz < self.hf_hz <= self.f_max:
            xlf=hz_to_x(self.lf_hz,0,w,self.f_min,self.f_max)
            xhf=hz_to_x(self.hf_hz,0,w,self.f_min,self.f_max)
            # V8.35: visible crossover/ROI highlight, NOT SUM raster cache.
            # Lower Mag opacity preserves the readability of the native plot.
            # Geometry is derived from LF/HF at paint time, so neither Y-pan
            # nor an ROI-marker drag rebuilds the 4096-bin SUM bitmap.
            roi_width=xhf-xlf
            band=QRectF(xlf,0.,roi_width,float(h))
            painter.fillRect(band,QColor(14,177,189,
                43 if self.kind=="phase" else 31))
            # Top/bottom cyan rails make the ROI easy to identify even when
            # numerous native TF traces intersect the crossover region.
            rail=QColor(55,226,229,155 if self.kind=="phase" else 129)
            painter.setPen(QPen(rail,1.35,Qt.PenStyle.SolidLine))
            painter.drawLine(QPointF(xlf,1.5),QPointF(xhf,1.5))
            painter.drawLine(QPointF(xlf,h-1.5),QPointF(xhf,h-1.5))
            for x,color in ((xlf,QColor("#42eab6")),(xhf,QColor("#ffaf54"))):
                painter.setPen(QPen(color,1.65,Qt.PenStyle.DashLine))
                painter.drawLine(int(x),0,int(x),h)
            # One quiet label below the Mag SUM, never over the Phase Match
            # pill. Skip it when the selected crossover band is too narrow.
            if self.kind=="mag" and roi_width>=165.:
                caption=f"CROSSOVER  {self.lf_hz:.0f}–{self.hf_hz:.0f} Hz"
                cap_w=min(roi_width-12.,174.)
                cap_x=(xlf+xhf-cap_w)/2.
                caption_box=QRectF(cap_x,h-27.,cap_w,20.)
                painter.setPen(QPen(QColor(44,192,211,128),.8))
                painter.setBrush(QColor(4,29,37,190))
                painter.drawRoundedRect(caption_box,5.,5.)
                painter.setPen(QColor(167,244,245,226))
                previous_font=painter.font()
                fnt=painter.font()
                fnt.setPointSize(8)
                fnt.setBold(True)
                painter.setFont(fnt)
                painter.drawText(caption_box,Qt.AlignmentFlag.AlignCenter,caption)
                painter.setFont(previous_font)
                painter.setBrush(Qt.BrushStyle.NoBrush)
        if native_y_hold:
            # LF/HF is frequency/X-only and never depends on Y-axis fit.
            # Untrusted SUM amplitude remains hidden until registered.
            painter.setPen(QColor("#ffbd61"))
            painter.drawText(80,19,"SUM MAG: Y CHUA XAC MINH (NATIVE MATCH)")
            painter.end()
            return
        base=QColor("#006F3C" if self.theme=="light" else "#39FF14")
        values=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        # Confidence ONLY changes opacity. Preserve physical SUM in weak
        # coherence and phase-smoothing cancellation regions rather than
        # dropping the whole line. Missing/nonfinite source data is not joined.
        trusted=np.asarray(d.valid,dtype=bool)
        if self.kind=="phase" and d.phase_valid is not None:
            trusted=trusted & np.asarray(d.phase_valid,dtype=bool)
        cached,shifts=self._viewport_paths(d,w,h,values,trusted)
        if cached is None:
            painter.end()
            return
        geometry=cached["geometry"]
        self._last_subpaths=cached["subpath_count"]
        self._last_points=len(geometry.edges)
        self._last_segments=geometry.wrap_splits+geometry.data_gaps
        self._last_low_coh=geometry.low_edges
        self._last_clipped=geometry.clipped_edges
        self._last_wraps=geometry.wrap_splits
        painter.setClipRect(QRectF(0.,0.,float(w),float(h)))
        bitmap=cached["trace_bitmap"]
        for shift in shifts:
            painter.drawPixmap(0,int(round(float(shift))),bitmap)
        painter.setClipping(False)
        painter.setPen(base)
        painter.setOpacity(.95)
        painter.setFont(self.font())
        offset=(f" | DISPLAY {self.display_offset_db:+.1f} dB"
                if self.kind=="mag" and self.display_offset_db else "")
        label=(f"SUM MAG NATIVE Y | {self.native_axis_label}"
               if self.kind=="mag" and self.native_axis_ready else
               f"SUM {self.kind.upper()} MODEL"+offset)
        painter.drawText(80,19,label)
        # Floating phase agreement above the Phase SUM, strictly inside LF-HF.
        if (self.kind=="phase" and self.roi_guides and
                self.phase_match_value is not None and
                self.f_min <= self.lf_hz < self.hf_hz <= self.f_max):
            xlf=hz_to_x(self.lf_hz,0,w,self.f_min,self.f_max)
            xhf=hz_to_x(self.hf_hz,0,w,self.f_min,self.f_max)
            mid=(xlf+xhf)/2
            tag_w=165
            tag_x=max(3.,min(float(w)-tag_w-3.,mid-tag_w/2))
            rect=QRectF(tag_x,34.,tag_w,30.)
            painter.setPen(QPen(QColor("#39FF14"),1.4))
            painter.setBrush(QColor(9,22,12,228))
            painter.drawRoundedRect(rect,6,6)
            painter.setPen(QColor("#39FF14"))
            font=painter.font()
            font.setBold(True)
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,
                            f"PHASE MATCH {self.phase_match_value:.0f}%")
        painter.end()

class QAHost(QWidget):
    """For runtime acceptance only; never presented as actual Smaart."""
    ticked=pyqtSignal(object)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RemiX Duo 8.180 · Auto Phase")
        self.setGeometry(65,40,1530,930)
        self.setStyleSheet("background:#080b12;color:#c7d5e8")
        self.sources=[str(DIR/"QA_A.trf"),str(DIR/"QA_B.trf")]
        self.targets=[
          [str(DIR/"QA_A.trf"),str(DIR/"QA_B.trf")],
          [str(DIR/"QA_C.trf"),str(DIR/"QA_D.trf")],
          [str(DIR/"QA_A.trf")],
          [str(DIR/"QA_A.trf"),str(DIR/"QA_B.trf"),str(DIR/"QA_C.trf")],
        ]
        self.tick_index=0
        self._buttons=[]
        self.setMinimumSize(1200,850)
        for i,text in enumerate(["Pair A+B","Pair C+D","Only A","Three ticks"]):
            b=QPushButton(text,self)
            b.setGeometry(16,90+i*46,200,35)
            b.clicked.connect(lambda _,j=i:self.change(j))
            self._buttons.append(b)
        self.show()

    def change(self,index):
        self.tick_index=index
        self.ticked.emit(self.targets[index])
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.fillRect(self.rect(),QColor("#070b11"))
        p.setPen(QColor("#dce9f4"));p.drawText(20,38,"SIMULATED Smaart Data Bar - runtime QA")
        for text in ("PHASE", "MAGNITUDE"):
            box=self.plot_boxes()[text]
            p.fillRect(*box,QColor("#04080d"))
            p.setPen(QPen(QColor("#233545"),1))
            x,y,w,h=box
            for j in range(1,12):
                p.drawLine(x+int(w*j/12),y,x+int(w*j/12),y+h)
            for j in range(1,6):
                p.drawLine(x,y+int(h*j/6),x+w,y+int(h*j/6))
            p.setPen(QColor("#e0eaf5"));p.drawText(x+10,y+23,text+" - QA reference")
        p.end()

    def plot_boxes(self):
        return {"PHASE":(260,105,self.width()-480,340),
                "MAGNITUDE":(260,500,self.width()-480,340)}

def _solve_autophase(a,b,*,lf,hf,max_delay_ms):
    """Worker-thread AutoPhase: unchanged solver + V8.104 noise confidence.

    `auto_align` is looked up at call time (tests may substitute it). A failed
    confidence assessment never hides solver candidates; it reports None.
    """
    results=auto_align(a,b,lf=lf,hf=hf,max_delay_ms=max_delay_ms)
    confidence=None
    if results:
        try:
            confidence=assess_alignment(a,b,results[0],lf=lf,hf=hf,
                                        max_delay_ms=max_delay_ms)
        except Exception:
            confidence=None
    return results,confidence


def _confidence_note(confidence):
    if confidence is None:
        return ""
    if confidence.verdict=="LOW":
        return (f" ⚠ ĐỘ TIN CẬY THẤP ({confidence.agreement:.0%}): nhiễu hoặc "
                "Averaging thấp — tăng Averaging Smaart rồi lưu lại Trace.")
    if confidence.verdict=="OK":
        return f" Tin cậy #1: {confidence.agreement:.0%}."
    return ""


class App(QWidget):
    def __init__(self,demo=False):
        super().__init__()
        self.demo=demo
        self.managed_mode=False
        self.ui_tool_enabled=True
        # V8.25: authoritative model-overlay visibility state;
        # false means native Smaart Tuning Live with NO RemiX overlays.
        self.overlay_workspace_visible=True
        self.overlay_tool_mode="phase"
        self.setWindowTitle("RemiX Duo V8.25 · Auto Phase")
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # RemiX Duo: compact, dark, high-contrast Smaart companion.
        # All original widget attributes and calculation callbacks are
        # preserved so engineering behavior remains identical to V8.4.
        # V8.6 compact UI: hide presentation rows only. Underlying widgets
        # stay alive so TF, ROI markers and running Auto Align are unchanged.
        self.setFixedSize(205,400)
        self.setObjectName("rootPanel")
        self.setStyleSheet("""
            QWidget { color:#DFEDF3; font-family:'Segoe UI'; font-size:11px; }
            QWidget#rootPanel {background:#090E15;}
            QLabel {background:transparent;}
            QFrame#panelCard {background:#111C29; border:1px solid #284055;
                               border-radius:7px;}
            QFrame#header {background:#091821; border:1px solid #295061;
                            border-radius:11px;}
            QLabel#brand {font-size:15px;font-weight:700;color:#53E7F5;}
            QLabel#version {font-size:10px;color:#91AABB;}
            QLabel#sectionTitle {font-weight:700;font-size:9px;
                                  color:#8EC7D5;}
            QLabel#tracePair {font-size:12px; font-weight:600;
                               color:#F1F9FB;}
            QLabel#match {font-size:17px;font-weight:700;color:#71FEA4;
                           border:1px solid #367B5B;background:#09261F;
                           border-radius:7px;padding:5px;}
            QLabel#delta {color:#AFEED9;font-size:11px;
                           background:#102B29;border-radius:6px;
                           padding:5px;}
            QLabel#caption {color:#8BA6B6;font-size:10px;}
            QLabel#amber {color:#F8C78D;font-size:10px;}
            QLabel#diagnostic {color:#A5C2D2;font-size:10px;}
            QLabel#result {color:#D8E8F2;font-size:11px;
                           padding-left:5px;}
            QLabel#footer {color:#B9D3DD;font-size:10px;
                           padding:5px;background:#10212C;
                           border:1px solid #284558;border-radius:7px;}
            QDoubleSpinBox,QComboBox {background:#192C3D;color:#F0FCFF;
                            border:1px solid #335269;border-radius:6px;
                            min-height:25px;padding:1px 5px;}
            QDoubleSpinBox:focus,QComboBox:focus {border:1px solid #30C9E1;}
            QComboBox::drop-down {border:0; width:18px;}
            QCheckBox {color:#D2E9F0;spacing:5px;}
            QCheckBox::indicator {width:15px;height:15px;}
             QPushButton#run {background:#39FF14;color:#041006;
                             font-weight:800;font-size:10px;
                             border:1px solid #78FF66;border-radius:6px;
                             min-height:24px;padding:0px 6px;}
             QPushButton#candidateOption {
                 background:#172C3D;color:#E8F8FF;
                 border:1px solid #355669;border-radius:7px;
                 font:bold 11px 'Segoe UI';text-align:left;
                 padding:3px 6px;min-height:40px;}
             QPushButton#candidateOption:hover {
                 background:#21465B;border:1px solid #6BC5E0;}
             QPushButton#candidateOption:checked {
                 background:#174535;color:#ACFFBE;
                 border:2px solid #52ED93;}
             QPushButton#candidateOption:disabled {
                 background:#111C28;color:#536F7C;
                 border:1px solid #233D4A;}
            QPushButton#run:hover {background:#65FF48;}
            QPushButton#run:pressed {background:#29D70B;}
            QTabWidget::pane {border:1px solid #2D485B;
                              background:#111C29;border-radius:8px;}
            QTabBar::tab {background:#132739;color:#9AB5C6;
                           font-size:9px;padding:5px 3px;min-width:38px;}
            QTabBar::tab:selected {background:#224354;
                                   color:#65EFF4;font-weight:700;}
        """)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(4,2,4,5)
        layout.setSpacing(4)

        def make_card(heading,number):
            frame=QFrame(self)
            frame.setObjectName("panelCard")
            col=QVBoxLayout(frame)
            col.setContentsMargins(6,5,6,5)
            col.setSpacing(3)
            # Hide the entire heading row for button-only cards.
            # Preserve unnumbered headings for Trace and Top 3.
            if heading:
                title=(f"{number}  {heading}" if number else heading)
                label=QLabel(title)
                label.setObjectName("sectionTitle")
                col.addWidget(label)
            else:
                col.setContentsMargins(6,3,6,3)
            layout.addWidget(frame)
            return col

        def tag(text):
            label=QLabel(text)
            label.setObjectName("caption")
            return label

        header=QFrame(self)
        header.setObjectName("header")
        hrow=QHBoxLayout(header)
        hrow.setContentsMargins(6,5,5,5)
        names=QVBoxLayout()
        names.setSpacing(0)
        brand=QLabel("RemiX Duo")
        brand.setObjectName("brand")
        names.addWidget(brand)
        edition=QLabel("SMAART · V8.25")
        edition.setObjectName("version")
        names.addWidget(edition)
        hrow.addLayout(names,1)
        readonly=QLabel("READ ONLY")
        readonly.setStyleSheet("color:#7DEAD2;border:1px solid #247F71;"
                               "background:#0F302D;border-radius:8px;"
                               "font:bold 10px 'Segoe UI';padding:4px 8px;")
        hrow.addWidget(readonly)
        readonly.hide()  # red circle 1: top-right READ ONLY badge
        layout.addWidget(header)
        self.header=header  # Unified V8.14 parent hides duplicate header.

        # TRACE / REFERENCE
        trace=make_card("TRACE ĐANG CHỌN",None)
        self.trace_title=trace.itemAt(0).widget()
        self._compact_layout=False
        self.trace_card=trace.parentWidget()
        self.trace_card.setObjectName("traceCard")
        self.trace_card.setSizePolicy(
            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        self.trace_card.setFixedHeight(138)
        self.pair_label=QLabel("Đang chờ 2 Trace được chọn")
        self.pair_label.setObjectName("tracePair")
        self.pair_label.setWordWrap(True)
        self.pair_label.setMinimumHeight(29)
        self.pair_label.setMaximumHeight(38)
        trace.addWidget(self.pair_label)
        self.pair_label.hide()  # Preserve legacy name updates, use per-row UI.
        # Two read-only lines per source:
        # name (full name in tooltip), then "Delay 0.00ms · Không đảo".
        # This fits a 164px app anchored entirely in Smaart's side column.
        self.trace_grid=QGridLayout()
        self.trace_grid.setContentsMargins(0,0,0,0)
        self.trace_grid.setHorizontalSpacing(0)
        self.trace_grid.setVerticalSpacing(2)
        self.trace_name_labels=[]
        # V8.123: red frame around a trace row whose delay/polarity changes.
        self.trace_change_frames=[]
        self.trace_changed=[False,False]
        self.trace_name_colors=[None,None]
        self.trace_delay_static=[]
        self.trace_polarity_static=[]
        self.trace_delay_tags=[]
        self.trace_compact_result=[]
        self.trace_gain_db=[0.,0.]
        self._raw_traces=None
        for idx in range(2):
            frame=QFrame(self)
            frame.setObjectName("traceChangeFrame")
            frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            frame.setStyleSheet(self._change_frame_css(False))
            self.trace_change_frames.append(frame)
            # Spans the name + result rows; added first so labels stay on top.
            self.trace_grid.addWidget(frame,idx*2,0,2,1)
            name=QLabel(f"{idx+1:02d}  —")
            name.setObjectName("traceNameLarge")
            name.setIndent(5)
            name.setStyleSheet(self._trace_name_css(None))
            name.setMinimumHeight(22)
            name.setToolTip("Tên Trace được chọn trong Smaart")
            self.trace_name_labels.append(name)
            self.trace_grid.addWidget(name,idx*2,0)
            # These existing attrs must remain for internal tests/tooltips.
            delay_tag=QLabel("Delay:")
            self.trace_delay_tags.append(delay_tag)
            delay_tag.hide()
            value=QLabel("0.00 ms")
            self.trace_delay_static.append(value)
            value.hide()
            polarity=QLabel("Không đảo")
            self.trace_polarity_static.append(polarity)
            polarity.hide()
            result=QLabel("Delay 0.00ms · Không đảo")
            result.setIndent(5)
            result.setStyleSheet("color:#9EC5D3;font:10px 'Segoe UI';")
            result.setMinimumHeight(25)
            result.setObjectName("traceDelayLarge")
            result.setToolTip("Đề xuất Auto Align, chỉ đọc")
            self.trace_compact_result.append(result)
            self.trace_grid.addWidget(result,idx*2+1,0)
        trace.addLayout(self.trace_grid)
        self.selection_warning=QLabel("")
        self.selection_warning.setObjectName("selectionWarning")
        self.selection_warning.setWordWrap(True)
        self.selection_warning.setStyleSheet(
            "color:#FFCC97;background:#291F19;border:1px solid #80552F;"
            "font:600 10px 'Segoe UI';border-radius:6px;"
            "padding:3px 7px;")
        self.selection_warning.setAlignment(
            Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        self.selection_warning.setFixedHeight(36)
        self.selection_warning.setSizePolicy(
            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        trace.addWidget(self.selection_warning)
        self.selection_warning.hide()
        refrow=QHBoxLayout()
        refrow.setSpacing(8)
        refrow.addWidget(tag("REF CỐ ĐỊNH"),1)
        self.ref_choice=QComboBox()
        self.ref_choice.addItem("TRACE 1",0)
        self.ref_choice.addItem("TRACE 2",1)
        self.ref_choice.setMinimumWidth(125)
        self.ref_choice.setToolTip("Trace giữ nguyên; Delay/INV áp dụng lên Trace còn lại.")
        self.ref_choice.currentIndexChanged.connect(self.on_ref_changed)
        refrow.addWidget(self.ref_choice)
        trace.addLayout(refrow)
        # Red circle 2: no REF chooser or annotation in the compact panel.
        # Keep the real QComboBox and its signal alive; default REF is 1.
        self.ref_choice.setCurrentIndex(0)
        for i in range(refrow.count()):
            item=refrow.itemAt(i)
            widget=item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
        self.correction_target_label=QLabel(
            "REF TRACE 1 GIỮ NGUYÊN · BÙ TRACE 2")
        self.correction_target_label.setObjectName("amber")
        trace.addWidget(self.correction_target_label)
        self.correction_target_label.hide()

        # PHASE MATCH RESULT — visible independently of advanced tabs.
        summary=make_card("ĐỘ ĐỒNG PHA","02")
        self.phase_match_label=QLabel("LF/HF PHASE MATCH: -- % (0 bins)")
        self.phase_match_label.setObjectName("match")
        self.phase_match_label.setMinimumHeight(30)
        summary.addWidget(self.phase_match_label)
        self.sum_ref_label=QLabel("Δ SUM–REF: --°  |  P95: --°")
        self.sum_ref_label.setObjectName("delta")
        self.sum_ref_label.setToolTip("Sai lệch pha trung bình và P95 giữa SUM/REF trong LF–HF.")
        summary.addWidget(self.sum_ref_label)
        # Red circle 3: calculations continue even when this card is hidden.
        self.phase_match_card=summary.parentWidget()
        self.phase_match_card.hide()

        # ALIGN CONTROL: no rows wider than the actual 382px content area.
        control=make_card(None,None)
        self.roi_hint=QLabel("Kéo hai mốc LF / HF trực tiếp trên đồ thị Phase")
        self.roi_hint.setObjectName("caption")
        control.addWidget(self.roi_hint)
        lfrow=QHBoxLayout()
        lfrow.setSpacing(6)
        lfrow.addWidget(tag("LF"))
        self.lf=QDoubleSpinBox()
        self.lf.setRange(20,20000)
        self.lf.setValue(60)
        self.lf.setSuffix(" Hz")
        lfrow.addWidget(self.lf,1)
        lfrow.addWidget(tag("HF"))
        self.hf=QDoubleSpinBox()
        self.hf.setRange(20,20000)
        self.hf.setValue(200)
        self.hf.setSuffix(" Hz")
        lfrow.addWidget(self.hf,1)
        control.addLayout(lfrow)
        # Red circle 4: LF/HF spinboxes stay connected for ROI marker dragging
        # on Smaart's plot, but the number inputs disappear from this panel.
        self.roi_hint.hide()
        for i in range(lfrow.count()):
            item=lfrow.itemAt(i)
            widget=item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
        # Delay and phase inversion now live directly in the affected
        # TRACE row. Reference row displays 0.00ms / Không đảo.
        self.delay=QDoubleSpinBox()
        self.delay.setRange(0,180)
        self.delay.setDecimals(2)
        self.delay.setSingleStep(.1)
        self.delay.setSuffix(" ms")
        self.delay.setMinimumWidth(94)
        self.delay.setMaximumWidth(105)
        self.delay.setToolTip(
            "Delay dương chỉ áp dụng cho Trace được ghi ở dòng này.")
        self.delay.valueChanged.connect(self.recalc)
        self.delay.valueChanged.connect(self._update_delay_route_label)
        self.invert=QCheckBox("Không đảo")
        self.invert.setMinimumWidth(95)
        self.invert.setToolTip(
            "Bật: Đảo pha cho chính Trace được Delay. Tắt: Không đảo.")
        self.invert.stateChanged.connect(self.recalc)
        self.invert.stateChanged.connect(self._update_delay_route_label)
        # V8.9: the solver still owns these values, but no user-editable
        # spinbox or checkbox is shown in any Trace row.
        self.delay.setParent(self)
        self.invert.setParent(self)
        self.delay.hide()
        self.invert.hide()
        # Retain legacy text object for status/tests, but never duplicate
        # its information in the Auto Align section.
        self.delay_route_label=QLabel("")
        self.delay_route_label.hide()
        self.solve=QPushButton("AUTO PHASE")
        self.solve.setObjectName("run")
        # QPushButton.clicked always carries ``checked: bool``.  Pure Python
        # slots may silently discard it, while the Cython-bound release method
        # enforces its signature and raised ``TypeError`` (then PyQt qFatal).
        self.solve.clicked.connect(self._on_align_clicked)
        self.solve.setFixedHeight(26)
        control.addWidget(self.solve)
        # Place the large AUTO PHASE action first, directly below the
        # dock heading, before TRACE DANG CHON. Keep the actual control
        # card, handlers and trace/candidate states untouched.
        phase_action_card=control.parentWidget()
        assert phase_action_card is not None
        # Only the green action card is compact; keep Trace/Top3 unchanged.
        phase_action_card.layout().setContentsMargins(5,1,5,1)
        phase_action_card.layout().setSpacing(0)
        phase_action_card.setFixedHeight(36)  # Only this green-button card is compact.
        layout.removeWidget(phase_action_card)
        layout.insertWidget(1,phase_action_card)

        candidates_card=make_card("TOP 3 PHƯƠNG ÁN",None)
        self.candidate_title=candidates_card.itemAt(0).widget()
        self.candidate_col=candidates_card
        # V8.122: empty in the full page; holds the 3 buttons on ONE row
        # in the compact page (an empty box layout takes no height).
        self.candidate_row=QHBoxLayout()
        self.candidate_row.setContentsMargins(0,0,0,0)
        self.candidate_row.setSpacing(3)
        candidates_card.addLayout(self.candidate_row)
        self.candidate_card=candidates_card.parentWidget()
        self.candidates=[]
        self.active_candidate_index=None
        self._candidate_scope=None
        for i in range(3):
            button=QPushButton(f"#{i+1}  --")
            button.setObjectName("candidateOption")
            button.setFixedHeight(44)
            button.setCheckable(True)
            button.setEnabled(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip("Chọn phương án để xem SUM Mag/Phase. Không ghi DSP.")
            button.clicked.connect(
                lambda checked=False,index=i:self.select_candidate(index))
            self.candidates.append(button)
            candidates_card.addWidget(button)

        # Keep Top3 at its actual content height, not an expanded card.
        self.candidate_card.setSizePolicy(
            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        self.candidate_card.setFixedHeight(167)
        # Compact tabs keep rarely needed Y-axis / diagnostic text away
        # from real-time phase match and solve controls.
        self.tabs=QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        display_page=QWidget(self)
        displaycol=QVBoxLayout(display_page)
        displaycol.setContentsMargins(9,7,9,7)
        displaycol.setSpacing(7)
        showrow=QVBoxLayout()
        self.mag=QCheckBox("SUM MAG")
        self.mag.setChecked(True)
        self.mag.stateChanged.connect(self.refresh_visibility)
        self.phase=QCheckBox("SUM PHASE")
        self.phase.setChecked(True)
        self.phase.stateChanged.connect(self.refresh_visibility)
        showrow.setSpacing(2)
        showrow.addWidget(self.mag)
        showrow.addWidget(self.phase)
        displaycol.addLayout(showrow)
        self.mag_smooth=QComboBox()
        self.phase_smooth=QComboBox()
        for name,value in SMOOTH_OPTIONS:
            self.mag_smooth.addItem(name,value)
            self.phase_smooth.addItem(name,value)
        self.mag_smooth.setCurrentIndex(4)
        self.phase_smooth.setCurrentIndex(4)
        for box in (self.mag_smooth,self.phase_smooth):
            box.currentIndexChanged.connect(self.recalc)
        smoothrow=QGridLayout()
        smoothrow.setHorizontalSpacing(4)
        smoothrow.addWidget(tag("MAG"),0,0)
        smoothrow.addWidget(self.mag_smooth,0,1)
        smoothrow.addWidget(tag("PHASE"),1,0)
        smoothrow.addWidget(self.phase_smooth,1,1)
        displaycol.addLayout(smoothrow)
        self.mag_fit=QCheckBox("Auto-fit Mag")
        self.mag_fit.setChecked(True)
        self.mag_fit.setToolTip("Điều chỉnh vị trí SUM Mag, không thay đổi DSP Gain.")
        self.mag_fit.stateChanged.connect(self.recalc)
        displaycol.addWidget(self.mag_fit)
        displaycol.addStretch(1)
        # V8.11: no display tab. Retain the hidden QObjects for existing
        # solver, visibility and smoothing code paths, but disable the
        # entire display control page and all user-initiated toggles.
        display_page.hide()

        axis_page=QWidget()
        axiscol=QVBoxLayout(axis_page)
        axiscol.setContentsMargins(9,7,9,7)
        axiscol.setSpacing(5)
        self.mag_min=QDoubleSpinBox()
        self.mag_min.setRange(-500,500);self.mag_min.setValue(-80)
        self.mag_max=QDoubleSpinBox()
        self.mag_max.setRange(-500,500);self.mag_max.setValue(20)
        self.phase_min=QDoubleSpinBox()
        self.phase_min.setRange(-2160,2160);self.phase_min.setValue(-180)
        self.phase_max=QDoubleSpinBox()
        self.phase_max.setRange(-2160,2160);self.phase_max.setValue(180)
        for box in (self.mag_min,self.mag_max,self.phase_min,self.phase_max):
            box.valueChanged.connect(self.update_y_ranges)
            box.setDecimals(2 if box in (self.mag_min,self.mag_max) else 1)
        axes=QGridLayout()
        axes.setHorizontalSpacing(3)
        axes.setVerticalSpacing(4)
        axes.addWidget(tag("MAG Y (dB)"),0,0,1,2)
        axes.addWidget(self.mag_min,1,0)
        axes.addWidget(self.mag_max,1,1)
        axes.addWidget(tag("PHASE Y (°)"),2,0,1,2)
        axes.addWidget(self.phase_min,3,0)
        axes.addWidget(self.phase_max,3,1)
        axiscol.addLayout(axes)
        axiscol.addStretch(1)
        self.tabs.addTab(axis_page,"Trục")

        info_page=QWidget()
        self.diag_layout=QVBoxLayout(info_page)
        self.diag_layout.setContentsMargins(9,7,9,7)
        self.diag_layout.setSpacing(5)
        self.notes=QLabel("TF lưu trữ · Không lấy TF trực tiếp qua Smaart API")
        self.notes.setObjectName("diagnostic")
        self.notes.setWordWrap(True)
        self.diag_layout.addWidget(self.notes)
        self.smooth_status=QLabel("Smooth: đang đọc cấu hình Smaart")
        self.smooth_status.setObjectName("diagnostic")
        self.smooth_status.setWordWrap(True)
        self.diag_layout.addWidget(self.smooth_status)
        self.axis_note=QLabel("Trục Y: đang chờ đồng bộ")
        self.axis_note.setObjectName("diagnostic")
        self.axis_note.setWordWrap(True)
        self.diag_layout.addWidget(self.axis_note)
        self.tabs.addTab(info_page,"Info")
        # V8.12 minimal UI: old Trục/Info panels remain in Qt memory
        # for existing axis-calibration and smoothing callbacks, but are
        # not shown or clickable. No tab control is added to the layout.
        self.tabs.hide()
        # Distribute unused space below the content, never inside
        # the warning or Trace rows. Normal Top3 remains unchanged.
        layout.addStretch(1)

        self.status=QLabel("Đang chờ Smaart")
        self.status.setObjectName("footer")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(33)
        self.status.setMaximumHeight(51)
        layout.addWidget(self.status)
        self.status.hide()  # red circle 5: bottom status/footer
        self.events=Events()
        self.events.loaded.connect(self.loaded)
        self.events.found.connect(self.found)
        self.events.aligned.connect(self._finish_alignment)
        self._align_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,thread_name_prefix="remix_autophase")
        self._align_future=None
        self._align_ticket=0
        self._align_closed=False
        # Future callbacks execute on the solver thread. Never touch sip/Qt
        # there: the frozen build can abort inside Qt6Core (0xc0000409).
        # A GUI-thread timer owns completion delivery instead.
        self._align_completion=None
        self._align_completion_timer=QTimer(self)
        self._align_completion_timer.setInterval(16)
        self._align_completion_timer.timeout.connect(
            self._poll_alignment_completion)
        self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
        # Dedicated worker avoids stalling Qt/AutoAlign while native
        # PrintWindow + multi-region correlation is running.
        self.axis_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.axis_follower=NativeAxisFollower()
        self.axis_future=None
        self.axis_requested=0.0
        self._axis_poll_identity=None
        self.pan_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.pan_tracker=NativeDualFastPan()
        self.pan_future=None
        self.pan_requested=0.0
        self.pan_last_move=0.0
        self.pan_last_log=0.0
        self.pan_accepted=0
        self.pan_rejected=0
        self.mag_pan_accepted=0
        self.mag_pan_rejected=0
        self.mag_pan_last_move=0.0
        self.mag_pan_last_status=0.0
        self.mag_pan_last_spin=0.0
        self.mag_pan_last_log=0.0
        self._phase_pan_last_frame=0.0
        self._mag_pan_last_frame=0.0
        self._phase_axis_generation=0
        self._mag_axis_generation=0
        self.axis_last_spin=0.0
        self.axis_last_status=0.0
        self.axis_accepted=0
        self.axis_rejected=0
        self.axis_render_ms=[]
        self.axis_task_ms=[]
        self.axis_previous_fit=0.0
        self.mag_anchor_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.mag_anchor_future=None
        self.mag_anchor_requested=0.0
        self._mag_anchor_poll_identity=None
        self.mag_anchor_accepted=0
        self.mag_anchor_failed=0
        # V8.114: Smaart per-trace dB offset (not in .trf, not readable by
        # API). Auto-measured from native pixels, or set by hand.
        self.offset_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.offset_future=None
        self.offset_requested=0.0
        self._offset_poll_identity=None
        self.events.trace_offsets.connect(self.on_trace_offsets)
        # V8.115: live Smaart smoothing via UIA (saved XML lags the GUI).
        self.events.live_smooth.connect(self.on_live_smoothing)
        self.events.update_ready.connect(self._on_update_ready)
        self._update_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,thread_name_prefix="remix_update")
        self._update_future=None
        self._update_closed=False
        self._update_notified=False
        self._update_prompt=None
        self._update_cache_path=app_paths().data/"github_update_check.json"
        self._update_timer=QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._start_update_check)
        self._update_timer.start(1800)
        self.live_smooth_future=None
        self.live_smooth_requested=0.0
        self._live_smooth_at=-1e9

        self.controller=SelectionController(self.on_selection)
        # Unknown or transient PrintWindow captures must NOT erase the
        # selected pair. Hide model overlays until a complete verified
        # tick snapshot has been received.
        self._selection_verified=bool(self.demo)
        self._selection_last_status="Awaiting verified Data Bar ticks"
        self.tick_gate=StableTickGate(required=3)
        self._selection_quality="transient"
        self.current_pair=None
        self.current_traces=None
        self.current_sum=None
        self.last_solve=None
        self.last_confidence=None
        # The Mag preview offset is a display-only alignment, never a DSP gain.
        # Freeze it for a selected pair so viewport pan/Auto Align cannot
        # cause the drawn SUM to jump to a new display baseline.
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        self.graph_mag=SumGraph("mag")
        self.graph_mag.require_native_axis=not self.demo
        # V8.51: 30x22 non-focus PEQ grips are the ONLY interactive
        # regions; original Smaart plots and SumGraph remain click-through.
        self.eq_peq_drag_callback=None
        self.eq_peq_grips={
            i:PEQMarkerGrip(i,self.on_peq_marker_drag) for i in range(1,13)}
        self.graph_phase=SumGraph("phase")
        self.roi_updating=False
        self.roi_markers={name:ROIMarker(name,self.on_roi_drag)
                          for name in ("LF","HF")}
        self.roi_line_grips={name:ROILineGrip(name,self.on_roi_drag)
                             for name in ("LF","HF")}
        # V8.32: Mag uses separate hit-tested grips. Both plots share
        # the same LF/HF spinboxes and DSP/ROI semantics.
        self.mag_roi_line_grips={
            name:ROILineGrip(name,
                lambda kind,x:self.on_roi_drag(kind,x,source_plot="mag"))
            for name in ("LF","HF")}
        self.eq_roi_lf_hz=60.0
        self.eq_roi_hf_hz=8000.0
        self.eq_roi_drag_callback=None
        self.eq_roi_markers={name:ROIMarker(name,self.on_eq_roi_drag)
                             for name in ("LF","HF")}
        self.eq_roi_line_grips={name:ROILineGrip(name,self.on_eq_roi_drag)
                               for name in ("LF","HF")}
        # FIR drag belongs only to its own Mag/Phase working range.
        self.fir_roi_lf_hz=30.0
        self.fir_roi_hf_hz=16000.0
        self.fir_roi_mode="mag"
        self.fir_roi_drag_callback=None
        self.fir_roi_markers={name:ROIMarker(name,self.on_fir_roi_drag)
                              for name in ("LF","HF")}
        self.fir_roi_line_grips={name:ROILineGrip(name,self.on_fir_roi_drag)
                                 for name in ("LF","HF")}
        for marker in self.fir_roi_markers.values():
            marker.setToolTip("Keo " + marker.kind + " de doi FIR Working Range")
        for grip in self.fir_roi_line_grips.values():
            grip.setToolTip("Keo vach " + grip.kind + " de doi FIR Working Range")
        for widget in (self.lf,self.hf):
            widget.setDecimals(1)
            widget.setSingleStep(1.0)
            widget.valueChanged.connect(self.on_roi_changed)
        self._sync_roi_to_graphs()
        saved_axes=read_saved_axes()
        if saved_axes:
            for box,val in ((self.mag_min,saved_axes["mag"][0]),
                            (self.mag_max,saved_axes["mag"][1]),
                            (self.phase_min,saved_axes["phase"][0]),
                            (self.phase_max,saved_axes["phase"][1])):
                box.setValue(val)
            self.axis_note.setText("Axes from saved SmaartConfig.xml")
        else:
            self.axis_note.setText("Smaart Y axes unknown - check before comparing")
        self.update_y_ranges()
        self.overlay_positioned=False
        self.host=QAHost() if demo else None
        from smaart_runtime_paths_v868 import trace_directory
        self.observer=LiveDataBarV7(trace_directory() or SMAART_TRF) if not demo else None
        self.plot_layout=None
        self.plot_hwnd=None
        # V8.175 QA hotfix: native plot-role verification must not queue behind
        # the 3/3 tick observer and TRF reader when switching Smaart editions.
        self.plot_pool=concurrent.futures.ThreadPoolExecutor(
            max_workers=1,thread_name_prefix="remix_plot_roles")
        self.plot_future=None
        self.plot_requested=0.
        self.events.layout_ready.connect(self.on_plot_layout)
        self.events.axis_snapshot.connect(self.on_absolute_phase_axis)
        self.events.pan_snapshot.connect(self.on_native_dual_pan)
        self.events.mag_anchor_ready.connect(self.on_mag_ref_anchor)
        self.axis_drag=None
        self._axis_was_pressed=False
        self.mag_axis_drag=None
        self._mag_was_pressed=False
        self._viewport_epoch=0
        self._drag_spin_tick=0.0
        self.phase_axis_note=QLabel(
            "Phase Y FAST: native REF, redraw latest-wins")
        self.phase_axis_note.setStyleSheet("color:#9cd3f2;font:10px 'Segoe UI'")
        self.phase_axis_note.setObjectName("diagnostic")
        self.phase_axis_note.setWordWrap(True)
        self.diag_layout.addWidget(self.phase_axis_note)
        self.mag_axis_note=QLabel(
            "Mag Y FAST: theo doi truc Y rieng, read-only")
        self.mag_axis_note.setStyleSheet("color:#b1e7a6;font:10px 'Segoe UI'")
        self.mag_axis_note.setObjectName("diagnostic")
        self.mag_axis_note.setWordWrap(True)
        self.diag_layout.addWidget(self.mag_axis_note)
        self.diag_layout.addStretch(1)
        # Initial UIA map not verified: fail-closed rather than mislabel.
        if self.host:
            self.host.ticked.connect(lambda names:self.controller.apply(names,"QA toggle"))
            self.host.change(0)
        self.last_poll=0.
        self.poll_future=None
        self.timer=QTimer(self)
        self._last_smooth_poll=0.0
        self._last_smooth_ns=-1
        self._smooth_snapshot=None
        self._refresh_saved_smoothing(force=True)
        self.timer.timeout.connect(self.tick)
        # V8.167 QA: 33ms coordinator repeats UI/window probes although
        # native tick screenshots run on an independent ~160ms cadence.
        # The 16ms drag timer remains unchanged for direct manipulation.
        self.timer.start(66)
        # Dedicated 60Hz lightweight cursor path: no GDI, TRF or FFT on Qt.
        self.drag_timer=QTimer(self)
        self.drag_timer.timeout.connect(self._fast_y_drag_tick)
        self.drag_timer.start(16)
        self._update_delay_route_label()
        self.show()

    def _start_update_check(self):
        if (self._update_closed or self._update_future is not None or
                self._update_notified):
            return
        self._update_future=self._update_pool.submit(
            check_for_update,__version__,cache_path=self._update_cache_path)
        def finished(task):
            if self._update_closed or sip.isdeleted(self.events):
                return
            try:
                result=task.result()
            except Exception:
                return
            self.events.update_ready.emit(result)
        self._update_future.add_done_callback(finished)

    def _on_update_ready(self,result):
        if (self._update_closed or self._update_notified or
                not isinstance(result,ReleaseResult) or not result.available):
            return
        self._update_notified=True
        self._show_update_prompt(result)

    def _show_update_prompt(self,result):
        version=".".join(str(value) for value in result.version)
        box=QMessageBox(QMessageBox.Icon.Information,
            "RemiX Duo · Có bản cập nhật",
            f"Đã có RemiX Duo {version}. Bạn có muốn mở trang cập nhật?",
            parent=self)
        box.setInformativeText(result.title)
        update=box.addButton("Cập nhật",QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Để sau",QMessageBox.ButtonRole.RejectRole)
        box.setModal(False)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.buttonClicked.connect(
            lambda button:self._open_update_url(result) if button is update else None)
        box.finished.connect(lambda _code:setattr(self,"_update_prompt",None))
        self._update_prompt=box
        box.open()

    def _open_update_url(self,result):
        tag="v"+".".join(str(value) for value in result.version)
        if valid_release_url(result.url,tag):
            QDesktopServices.openUrl(QUrl(result.url))

    def on_selection(self,record):
        print("V7_PAIR_EVENT",record.names if record else None,flush=True)
        # Invalidate previously drawn lines immediately; never keep stale SUM.
        self.current_pair=None;self.current_sum=None;self.current_traces=None
        self._raw_traces=None
        self._reset_trace_gains()
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        self.graph_phase.set_data(None);self.graph_mag.set_data(None)
        self._clear_phase_match()
        self.last_solve=None
        self._clear_candidate_buttons()
        self.ref_choice.blockSignals(True)
        self.ref_choice.setCurrentIndex(0)
        self.ref_choice.blockSignals(False)
        self.delay.blockSignals(True);self.delay.setValue(0.);self.delay.blockSignals(False)
        self.invert.blockSignals(True);self.invert.setChecked(False);self.invert.blockSignals(False)
        self._update_delay_route_label()
        if record is None:
            self.pair_label.setText("Ch\u01b0a c\u00f3 2 Trace - SUM \u0111\u00e3 \u1ea9n")
            self.refresh_visibility()
            return
        self.current_pair=record.names
        self.pair_label.setText("01  "+Path(record.names[0]).stem+"\n02  "+Path(record.names[1]).stem)
        self._update_delay_route_label()
        self.status.setText("Loading selected pair...")
        gen=record.generation
        if self.demo:
            def loader():
                f=np.geomspace(20,20000,1050)
                if Path(record.names[0]).stem=="QA_C":
                    return synthetic("QA_C",f,db=-2,delay_ms=1.8),synthetic("QA_D",f,db=3,delay_ms=-1.1)
                return synthetic("QA_A",f),synthetic("QA_B",f,delay_ms=-2.4)
        else:
            def loader():
                return read_trf(record.names[0]),read_trf(record.names[1])
        task=self.pool.submit(loader)
        task.add_done_callback(lambda result:self.events.loaded.emit(gen,record.names,result,None))

    def loaded(self,gen,pair,future,_unused):
        if not self.controller.is_current(gen,pair):return
        try:
            self._raw_traces=tuple(future.result())
            self.current_traces=self._gained_traces()
        except Exception as exc:
            self._raw_traces=None
            self.status.setText("Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c Trace: "+str(exc)[:120])
            self.current_traces=None
            # V8.113: the status label is hidden in the compact panel; make
            # the failure visible instead of a verified pair with no SUM.
            names=" + ".join(Path(n).stem for n in pair)
            self.selection_warning.setText("Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c Trace: "+names)
            self.selection_warning.setToolTip(str(exc)[:200])
            self.selection_warning.show()
            from signal_tools_gui_v813 import show_notice
            target=self.graph_phase if self.graph_phase.isVisible() else self
            show_notice(target,f"Kh\u00f4ng \u0111\u1ecdc \u0111\u01b0\u1ee3c file Trace ({names}): {str(exc)[:120]}")
            return
        self.recalc()
        self.solve.setEnabled(bool(self._selection_verified))
        print("V7_SUM_RENDER_READY",self.current_sum.sources if self.current_sum else None,
              len(self.current_sum.hz) if self.current_sum else 0,flush=True)
        self.status.setText("Pair ready - SUM Mag/Phase follows Smaart" if not self.demo
                            else "QA: hai \u0111\u01b0\u1eddng SUM \u0111\u00e3 v\u1ebd tr\u00ean \u0111\u1ed3 th\u1ecb m\u00f4 ph\u1ecfng")

    # ---- V8.114 per-trace level (Smaart dB offset) -----------------------
    def _gained_traces(self):
        if not self._raw_traces:return None
        return tuple(with_gain_db(t,g) for t,g in zip(self._raw_traces,self.trace_gain_db))

    def _reset_trace_gains(self):
        self.trace_gain_db=[0.,0.]
        self._offset_reasons=("","")

    def set_trace_gain(self,index,gain_db):
        """Apply a measured Smaart trace offset to SUM; Top 3 becomes stale."""
        gain=round(float(np.clip(gain_db,-TRACE_GAIN_LIMIT_DB,TRACE_GAIN_LIMIT_DB)),1)
        if abs(gain-self.trace_gain_db[index])<.05:return False
        self.trace_gain_db[index]=gain
        if self._raw_traces:
            self.current_traces=self._gained_traces()
            if self.last_solve:
                self.last_solve=None
                self._clear_candidate_buttons()
                self.status.setText("Mức dB Trace đổi — bấm AUTO PHASE để tính lại Top 3")
            self.recalc()
        return True

    def _verified_mag_smoothing_for_offset(self):
        """Only a recent live Smaart UI reading may condition pixel fitting."""
        age=time.monotonic()-getattr(self,"_live_smooth_at",-1e30)
        if not 0<=age<=3.5:
            return 0.
        box=getattr(self,"mag_smooth",None)
        if box is None:
            return 0.
        try:
            value=float(box.currentData())
            return value if any(abs(value-option[1])<1e-9
                                for option in SMOOTH_OPTIONS) else 0.
        except (ValueError,TypeError,AttributeError):
            return 0.

    def _schedule_trace_offsets(self,target):
        if (self.demo or not self._raw_traces or not self.plot_layout or
                not self._mag_anchor_verified or not self._selection_verified):
            return
        now=time.monotonic()
        if now-self.mag_pan_last_move<.65:return
        y_min,y_max=float(self.graph_mag.y_min),float(self.graph_mag.y_max)
        smoothing_oct=self._verified_mag_smoothing_for_offset()
        key=(target.hwnd,tuple(self.plot_layout.mag),tuple(self.current_pair or ()),
             round(y_min,3),round(y_max,3),smoothing_oct)
        # New identity => immediate native proof. Stable identity => sample
        # external Smaart dB-offset edits periodically, not every 0.8 sec.
        from native_poll_budget_v8162 import (
            poll_due,TRACE_OFFSETS_STEADY_SECONDS)
        if not poll_due(now=now,last_started=self.offset_requested,
                        key=key,last_key=self._offset_poll_identity,
                        steady_seconds=TRACE_OFFSETS_STEADY_SECONDS):
            return
        if self.offset_future is not None and not self.offset_future.done():return
        self.offset_requested=now
        self._offset_poll_identity=key
        traces=self._raw_traces
        plot=tuple(self.plot_layout.mag)
        def work():
            from smaart_native_mag_fit import capture_native_window
            from trace_offset_native_v8114 import measure_trace_offsets
            image,winrect=capture_native_window(target.hwnd)
            return measure_trace_offsets(image,plot,winrect,traces,y_min,y_max,
                                         smoothing_oct=smoothing_oct)
        self.offset_future=self.offset_pool.submit(work)
        def done(task,k=key):
            try:result=task.result()
            except Exception as exc:result=exc
            if not sip.isdeleted(self.events):
                self.events.trace_offsets.emit((k,result))
        self.offset_future.add_done_callback(done)

    def on_trace_offsets(self,payload):
        key,result=payload
        if (not self._raw_traces or not self.plot_layout or isinstance(result,Exception)
                or key[0]!=self.plot_hwnd or key[1]!=tuple(self.plot_layout.mag)
                or key[2]!=tuple(self.current_pair or ())
                or key[3:5]!=(round(float(self.graph_mag.y_min),3),
                              round(float(self.graph_mag.y_max),3))
                or (len(key)>5 and
                    key[5]!=self._verified_mag_smoothing_for_offset())):
            return  # stale or failed capture: keep current levels
        changed=False
        reasons=tuple(item.reason if item.offset_db is None else "" for item in result[:2])
        if reasons!=getattr(self,"_offset_reasons",None):
            self._offset_reasons=reasons
            if any(reasons):print("V8114_TRACE_OFFSET_HOLD",reasons,flush=True)
        for i,item in enumerate(result[:2]):
            # V8.116: pixel measurement jitters ±0.1 dB (live log 3.9<->4.0);
            # every applied change wipes Top 3, so ignore sub-step noise.
            if (item.offset_db is not None and
                    abs(item.offset_db-self.trace_gain_db[i])>=OFFSET_APPLY_DB):
                changed|=self.set_trace_gain(i,item.offset_db)
        if changed:
            print("V8114_TRACE_OFFSETS",self.trace_gain_db,flush=True)

    def _reference_index(self):
        return int(self.ref_choice.currentData() or 0)

    def _ordered_traces(self):
        if not self.current_traces:
            return None
        a,b=self.current_traces
        return (a,b) if self._reference_index()==0 else (b,a)

    @staticmethod
    def _change_frame_css(changed):
        return ("QFrame#traceChangeFrame{background:transparent;border-radius:5px;"
                "border:2px solid "+("#FF3B3B" if changed else "transparent")+";}")

    @staticmethod
    def _readable_trace_color(color):
        """Smaart icon colour, same hue, bright enough on the dark panel."""
        if not color:
            return "#F5FDFF"
        c=QColor(color)
        if not c.isValid():
            return "#F5FDFF"
        h,sat,val,_=c.getHsvF()
        if sat<.15:
            return "#F5FDFF"
        return QColor.fromHsvF(max(h,0.),min(sat,.80),max(val,.95)).name().upper()

    def _trace_name_css(self,color):
        return ("color:"+self._readable_trace_color(color)+
                ";font:bold 12px 'Segoe UI';padding-top:2px;background:transparent;")

    def _trace_color_for(self,name):
        lookup=getattr(getattr(self,"observer",None),"trace_color",None)
        if not callable(lookup) or not name:
            return None
        try:
            return lookup(name)
        except Exception:
            return None

    def _refresh_trace_name_colors(self):
        """V8.123: trace name in the trace's own Smaart colour (Data Bar icon)."""
        names=tuple(self.current_pair or ())
        for i,label in enumerate(self.trace_name_labels):
            color=self._trace_color_for(names[i]) if len(names)==2 else None
            if color!=self.trace_name_colors[i]:
                self.trace_name_colors[i]=color
                label.setStyleSheet(self._trace_name_css(color))

    def _update_delay_route_label(self,*_):
        """Render model results with no editable delay or invert controls."""
        ref=self._reference_index()
        target=1-ref
        names=tuple(self.current_pair or ())
        for i,label in enumerate(self.trace_name_labels):
            full=Path(names[i]).stem if len(names)==2 else "—"
            shortened=full if len(full)<=17 else full[:16]+"…"
            label.setText(f"TRACE {i+1} · {shortened}")
            label.setToolTip(f"Trace {i+1}: {full}")
            val=self.delay.value() if i==target else 0.0
            inv=i==target and self.invert.isChecked()
            polarity="Đảo pha" if inv else "Không đảo"
            self.trace_delay_static[i].setText(f"{val:.2f} ms")
            self.trace_polarity_static[i].setText(polarity)
            self.trace_compact_result[i].setText(
                f"Delay: {val:.2f} ms · {polarity}")
            self.trace_compact_result[i].setStyleSheet(
                "font:bold 12px 'Segoe UI';color:"
                +("#FFB46A;" if inv else
                  "#7DF1BF;" if i==target and val>0 else "#D6E9F4;"))
            self.trace_compact_result[i].setToolTip(
                f"Trace {i+1} · Delay: {val:.2f} ms · {polarity} "
                "(kết quả mô phỏng, không nạp DSP)")
            # V8.123: frame every trace that is delayed or inverted.
            changed=bool(len(names)==2 and (val>=0.005 or inv))
            if changed!=self.trace_changed[i]:
                self.trace_changed[i]=changed
                self.trace_change_frames[i].setStyleSheet(
                    self._change_frame_css(changed))
        self._refresh_trace_name_colors()
        if hasattr(self,"delay_route_label"):
            self.delay_route_label.setText(
                f"Delay Trace {target+1}: +{self.delay.value():.2f} ms | "
                f"{'Đảo pha' if self.invert.isChecked() else 'Không đảo'} "
                f"| giữ Trace {ref+1}")
        if hasattr(self,"correction_target_label"):
            self.correction_target_label.setText(
                f"TRACE {ref+1} GIỮ NGUYÊN | TRỄ TRACE {target+1}")

    def on_ref_changed(self,*_):
        # A reference change changes the PHYSICAL delayed target; it must
        # never negate an already-positive DSP delay or silently advance.
        self._update_delay_route_label()
        self.last_solve=None
        self._clear_candidate_buttons()
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        if self.current_traces:
            self.recalc()
            ref=self._reference_index()+1
            target=2 if ref==1 else 1
            self.status.setText(
                f"REF TRACE {ref} | TRỄ TRACE {target} "
                f"+{self.delay.value():.2f}ms, chọn AUTO ALIGN để tối ưu.")
        else:
            self._clear_phase_match()

    def _schedule_live_smoothing(self,target):
        if self.demo or not self.plot_layout:return
        now=time.monotonic()
        if now-self.live_smooth_requested<1.5:return
        if self.live_smooth_future is not None and not self.live_smooth_future.done():return
        self.live_smooth_requested=now
        phase,mag=tuple(self.plot_layout.phase),tuple(self.plot_layout.mag)
        def work():
            from smaart_live_smooth_v8115 import read_live_smoothing
            return read_live_smoothing(target.hwnd,phase,mag)
        self.live_smooth_future=self.pool.submit(work)
        def done(task):
            try:result=task.result()
            except Exception:return  # keep last confirmed smoothing
            if not sip.isdeleted(self.events):
                self.events.live_smooth.emit(result)
        self.live_smooth_future.add_done_callback(done)

    def on_live_smoothing(self,result):
        """Apply Smaart's on-screen smoothing; it overrides the saved XML."""
        if not isinstance(result,dict) or not result:return
        changed=False
        for kind,box in (("mag",self.mag_smooth),("phase",self.phase_smooth)):
            if kind not in result:continue
            ix=next((i for i in range(box.count())
                     if abs(float(box.itemData(i) or 0)-result[kind])<1e-9),-1)
            if ix<0:continue  # Smaart value outside SUM options: keep current
            self._live_smooth_at=time.monotonic()
            if box.currentIndex()!=ix:
                box.blockSignals(True);box.setCurrentIndex(ix);box.blockSignals(False)
                changed=True
        if changed:
            self.smooth_status.setText(
                f"Smooth theo Smaart (live): Mag {self.mag_smooth.currentText()}, "
                f"Phase {self.phase_smooth.currentText()}")
            print("V8115_LIVE_SMOOTH",result,flush=True)
            if self.current_traces:self.recalc()

    def _refresh_saved_smoothing(self,force=False):
        """Watch SmaartConfig.xml at 1.5s intervals; never touch Smaart."""
        now=time.monotonic()
        # V8.115: a recent live UIA reading wins over the lagging saved XML.
        if not force and now-getattr(self,"_live_smooth_at",-1e9)<6.0:return
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

    def recalc(self,*_):
        self._enforce_display_always_on()
        if not self.current_traces:return
        self.current_sum=compute_sum(*self._ordered_traces(),
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),
             coh_gate=.60,
             mag_oct=float(self.mag_smooth.currentData() or 0),
             phase_oct=float(self.phase_smooth.currentData() or 0))
        # V8.26: Never invent a provisional +dB centering shift.
        # A native REF (either stored Trace, whichever is visibly present)
        # must be identified before drawing SUM Mag over Smaart's Y axis.
        mag_fit_key=(tuple(self.current_pair or self.current_sum.sources),
                     self._reference_index(),
                     tuple(t.file_mtime_ns for t in self.current_traces),
                     bool(self.mag_fit.isChecked()))
        if mag_fit_key!=self._mag_offset_key:
            self._mag_offset_key=mag_fit_key
            self._mag_anchor_verified=False
            self.graph_mag.native_axis_ready=False
            self.graph_mag.native_axis_label=""
        self.graph_mag.display_offset_db=0.0
        if not self._mag_anchor_verified:
            if getattr(self,"_active_smaart_major",None)==8:
                self.graph_phase.native_x_axis_ready=False
                self.graph_phase.update()
            self.axis_note.setText(
                "SUM MAG Y: Chua xac minh native trace/pixel. Khong tu offset.")
        self.graph_mag.set_data(self.current_sum)
        self.graph_phase.set_data(self.current_sum)
        self._update_phase_match()
        self.refresh_visibility()

    def _candidate_key(self):
        if not self.current_pair or not self.current_traces:
            return None
        return (tuple(self.current_pair),
                tuple(id(trace) for trace in self.current_traces),
                round(float(self.lf.value()),1),
                round(float(self.hf.value()),1))

    def _clear_candidate_buttons(self):
        self.active_candidate_index=None
        self._candidate_scope=None
        for i,button in enumerate(self.candidates):
            button.setEnabled(False)
            button.setChecked(False)
            button.setText(f"#{i+1}  --")
            button.setToolTip("Nhấn AUTO ALIGN để tính lại Top 3")

    def _display_candidates(self):
        for i,button in enumerate(self.candidates):
            if self.last_solve and i<len(self.last_solve):
                route=route_candidate(self.last_solve[i])
                polarity="Đảo pha" if route.invert_target else "Không đảo"
                if self._compact_layout:
                    # V8.122: ~55 px wide button; full text in tooltip.
                    button.setText(
                        f"#{i+1} T{route.delay_trace}"
                        f"{' INV' if route.invert_target else ''}\n"
                        f"{route.delay_ms:.2f} ms")
                else:
                    button.setText(
                        f"#{i+1}  Trace {route.delay_trace} · {polarity}\n"
                        f"Delay: {route.delay_ms:.2f} ms")
                button.setToolTip(
                    f"Phương án #{i+1}: Delay Trace {route.delay_trace} "
                    f"+{route.delay_ms:.2f} ms; {polarity}; "
                    f"giữ nguyên Trace {route.reference_trace}. "
                    f"Điểm tối ưu: {route.score_db:+.3f} dB. "
                    "Chọn để xem SUM Mag/Phase; không ghi DSP.")
                button.setEnabled(True)
            else:
                button.setEnabled(False)
                button.setText(f"#{i+1}  --")
            button.setChecked(self.active_candidate_index==i)

    def select_candidate(self,index):
        """Preview selected signed-solver route, not physical DSP action."""
        if (self.last_solve is None or self._candidate_scope is None or
            self._candidate_scope!=self._candidate_key() or
            not isinstance(index,int) or index<0 or
            index>=min(3,len(self.last_solve))):
            # V8.116: an out-of-scope Top 3 is dropped, not kept hidden.
            if self._candidate_scope!=self._candidate_key():
                self.last_solve=None
            self._clear_candidate_buttons()
            return False
        route=route_candidate(self.last_solve[index])
        before_ref=self._reference_index()
        # Atomic, positive, physical target selection; no transient
        # recomputations while changing REF/delay/invert together.
        self.ref_choice.blockSignals(True)
        self.delay.blockSignals(True)
        self.invert.blockSignals(True)
        try:
            self.ref_choice.setCurrentIndex(route.reference_index)
            self.delay.setValue(route.delay_ms)
            self.invert.setChecked(route.invert_target)
        finally:
            self.ref_choice.blockSignals(False)
            self.delay.blockSignals(False)
            self.invert.blockSignals(False)
        if before_ref!=route.reference_index:
            self._mag_offset_key=None
            self._mag_anchor_verified=False
        self.active_candidate_index=index
        self._display_candidates()
        self._update_delay_route_label()
        self.recalc()
        polarity="Đảo pha" if route.invert_target else "Không đảo"
        self.status.setText(
            f"XEM THỬ #{index+1}: Trace {route.delay_trace} · "
            f"Delay: {route.delay_ms:.2f} ms · {polarity}. "
            f"Giữ Trace {route.reference_trace}. "
            "Chưa áp dụng lên Smaart/DSP."+
            _confidence_note(getattr(self,"last_confidence",None)))
        return True

    def _on_align_clicked(self,checked=False):
        """Cython-safe Qt slot: consume QPushButton.clicked(bool)."""
        self.align()

    def align(self):
        if self._align_closed or self._align_future is not None:
            return  # one running request, no unbounded worker queue
        if not self._selection_verified:
            self.status.setText("Chưa xác minh ổn định 2 Trace được tick")
            return
        if not self.current_traces:
            self._clear_candidate_buttons()
            self.status.setText("Cần đủ 2 Trace đã xác nhận.")
            return
        gen=self.controller.generation
        pair=self.controller.last_pair
        # Use ORIGINAL trace order for solver, never reference-swapped order.
        a,b=self.current_traces
        key=self._candidate_key()
        try:
            signatures=self._alignment_files()
        except OSError:
            self.status.setText("Trace thay đổi hoặc không còn đọc được; xác minh lại tick")
            return
        copies=[]
        for trace in (a,b):
            arrays=[np.array(x,copy=True) for x in (trace.hz,trace.h,trace.coherence)]
            for array in arrays:array.setflags(write=False)
            copies.append(replace(trace,hz=arrays[0],h=arrays[1],coherence=arrays[2]))
        self._align_ticket+=1
        ticket=self._align_ticket
        context=(gen,pair,key,signatures)
        self._clear_candidate_buttons()
        self.last_solve=None
        self.solve.setEnabled(False)
        self.solve.setText("ĐANG TÍNH…")
        self.status.setText("Auto Phase đang tính trên worker; không ghi DSP")
        self.last_confidence=None
        self._align_started_at=time.perf_counter()
        future=self._align_pool.submit(_solve_autophase,*copies,
            lf=self.lf.value(),hf=self.hf.value(),max_delay_ms=180)
        self._align_future=future
        self._align_completion=(ticket,context,future)
        self._align_completion_timer.start()
        from signal_tools_gui_v813 import schedule_auto_wait_notice
        schedule_auto_wait_notice(
            self,lambda t=ticket,f=future:
                t==self._align_ticket and self._align_future is f and not f.done(),
            getattr(self,"graph_phase",None))

    def _poll_alignment_completion(self):
        """Deliver an Auto Phase result only from the Qt GUI thread."""
        pending=self._align_completion
        if self._align_closed or pending is None:
            self._align_completion_timer.stop()
            return
        ticket,context,future=pending
        if not future.done():
            return
        self._align_completion=None
        self._align_completion_timer.stop()
        self._finish_alignment(ticket,context,future)

    def _alignment_files(self):
        if self.demo:return ()
        signatures=[]
        for trace in self.current_traces or ():
            stat=trace.path.stat()
            if stat.st_mtime_ns!=trace.file_mtime_ns:
                raise OSError("TRF changed since it was loaded")
            signatures.append((str(trace.path),stat.st_mtime_ns,stat.st_size))
        return tuple(signatures)

    def _finish_alignment(self,ticket,context,future):
        if self._align_closed or ticket!=self._align_ticket:return
        self._align_future=None
        self.solve.setText("AUTO PHASE")
        self.solve.setEnabled(bool(self._selection_verified and self.current_traces))
        gen,pair,key,signatures=context
        valid=(self._selection_verified and self.controller.is_current(gen,pair)
               and key==self._candidate_key())
        # V8.168: the observer may be absent in synthetic QA or detached
        # between async solve and result delivery. Even the HOLD diagnostic
        # must never dereference it or raise inside the Qt timer callback.
        observer=self.observer
        observer_pair_ready=bool(
            observer is not None and observer.ready and observer.last_pair==pair)
        if valid and not self.demo:
            valid=observer_pair_ready and observer._pair()==pair
        if valid and self.managed_mode:
            valid=(self.overlay_workspace_visible and self.overlay_tool_mode=="phase")
        try:
            valid=valid and signatures==self._alignment_files()
        except OSError:
            valid=False
        if not valid:
            print("V8155_AUTO_PHASE_HOLD", "tick",self._selection_verified,
                  "generation",self.controller.is_current(gen,pair),
                  "scope",key==self._candidate_key(),
                  "observer",observer_pair_ready,
                  "elapsed_ms",round(1000*(time.perf_counter()-getattr(self,"_align_started_at",time.perf_counter())),1),
                  flush=True)
            self._clear_candidate_buttons()
            self.status.setText("Bỏ kết quả Auto Phase cũ: Trace, tick hoặc ROI đã đổi")
            return
        try:
            results,confidence=future.result()
        except Exception as exc:
            self._clear_candidate_buttons()
            self.status.setText("Auto Phase không tính được: "+str(exc)[:160])
            return
        if confidence is not None and confidence.verdict=="HOLD_SATURATED":
            # Fail closed: coherence ~1.0 on a rough response is the
            # low-average estimator artefact, not a trustworthy measurement.
            self.last_solve=None
            self.last_confidence=confidence
            self._clear_candidate_buttons()
            self.status.setText(
                f"HOLD: Coherence ≈1.0 trên {confidence.saturated_fraction:.0%} bin "
                f"nhưng Mag gồ ghề {confidence.mag_roughness_db:.1f} dB — Smaart "
                "Averaging quá thấp. Tăng Averaging rồi lưu lại Trace.")
            return
        self.last_confidence=confidence
        self.last_solve=results
        print("V8155_AUTO_PHASE_READY",len(results),"elapsed_ms",
              round(1000*(time.perf_counter()-getattr(self,"_align_started_at",time.perf_counter())),1),
              flush=True)
        self._candidate_scope=key
        self.active_candidate_index=None
        if not results:
            self._clear_candidate_buttons()
            self.status.setText("Không đủ Coherence trong vùng LF/HF.")
            return
        self._display_candidates()
        self.select_candidate(0)

    # V8.122 compact page (dock < 424 px, many TF engines): AUTO PHASE,
    # the two trace rows and Top 3 on ONE row fit in ~176 px.
    COMPACT_TRACE_H=(80,52)       # (verified pair, invalid/warning)
    COMPACT_CANDIDATE_H=44
    COMPACT_PAGE_H=176
    _COMPACT_CANDIDATE_CSS=("min-height:0px;padding:1px 2px;"
                            "font:bold 9px 'Segoe UI';text-align:center;")

    def _trace_card_height(self,valid):
        if self._compact_layout:
            return self.COMPACT_TRACE_H[0 if valid else 1]
        return 138 if valid else 70

    def set_compact_layout(self,compact)->bool:
        """V8.122: switch the Auto Phase page between full (400) and compact.

        Presentation only: the same buttons/labels/signals are moved, never
        recreated. Returns True when the layout changed.
        """
        compact=bool(compact)
        if compact==self._compact_layout:
            return False
        self._compact_layout=compact
        self.trace_title.setVisible(not compact)
        self.candidate_title.setVisible(not compact)
        for label in self.trace_name_labels:
            label.setMinimumHeight(16 if compact else 22)
        for label in self.trace_compact_result:
            label.setMinimumHeight(16 if compact else 25)
        self.trace_grid.setVerticalSpacing(0 if compact else 2)
        for button in self.candidates:
            if compact:
                self.candidate_col.removeWidget(button)
                self.candidate_row.addWidget(button,1)
            else:
                self.candidate_row.removeWidget(button)
                self.candidate_col.insertWidget(
                    self.candidate_col.indexOf(self.candidate_row),button)
            button.setFixedHeight(36 if compact else 44)
            button.setStyleSheet(self._COMPACT_CANDIDATE_CSS if compact else "")
        self.candidate_col.setContentsMargins(*((4,4,4,4) if compact
                                                else (6,5,6,5)))
        self.candidate_card.setFixedHeight(
            self.COMPACT_CANDIDATE_H if compact else 167)
        self.trace_card.setFixedHeight(
            self._trace_card_height(bool(self._selection_verified)))
        if self.last_solve and self._candidate_scope is not None:
            self._display_candidates()
        return True

    def _set_tick_presentation(self,valid:bool,*,preserve_candidates=False):
        # Verified pair = two compact trace name/result rows; invalid
        # count = only section title + slim warning message.
        self.trace_card.setFixedHeight(self._trace_card_height(valid))
        self._selection_verified=bool(valid)
        self.solve.setEnabled(bool(valid and self.current_traces and self._align_future is None))
        self.candidate_card.setVisible(bool(valid))
        for widget in (*self.trace_name_labels,*self.trace_compact_result,
                       *self.trace_change_frames):
            widget.setVisible(bool(valid))
        if not valid and not preserve_candidates:
            self.last_solve=None
            self._clear_candidate_buttons()
        elif valid and self.last_solve is not None:
            # Re-arm only the SAME verified pair/source/ROI after a short
            # incomplete tick scan. Never resurrect a changed selection.
            if self._candidate_scope==self._candidate_key():
                self._display_candidates()
            else:
                self.last_solve=None
                self._clear_candidate_buttons()
        self.refresh_visibility()

    def found(self,result):
        # Worker-owned tick classification is captured as an immutable
        # snapshot; UI must not inspect mutable observer.states after worker
        # already started a newer screenshot. Legacy tests may omit the
        # snapshot, in which case a safe fallback reads the cached map.
        if isinstance(result,SyncResult):
            names=result.active_names
            ambiguous=result.ambiguous
            if names is None:
                names=tuple(
                    str(self.observer.order[i])
                    for i,state in sorted(self.observer.states.items())
                    if state=="on" and 0<=i<len(self.observer.order))
                ambiguous+=sum(state not in ("on","off")
                               for state in self.observer.states.values())
        else:
            names=()
            ambiguous=1
        decision=self.tick_gate.evaluate(result,names,ambiguous)
        if os.environ.get("REMIX_QA_TRACE_REARM")=="1":
            now=time.monotonic()
            key=(decision.state,decision.reason,decision.stable,
                 bool(self.current_sum),bool(self.overlay_positioned),
                 getattr(self.observer,"hwnd",0))
            last=getattr(self,"_qa_rearm_last",0.)
            previous=getattr(self,"_qa_rearm_key",None)
            if key!=previous and (decision.state!="valid" or now-last>1.):
                self._qa_rearm_key=key
                self._qa_rearm_last=now
                print("QA_REARM_FOUND","status",str(result.status)[:110],
                      "state",decision.state,"why",decision.reason,
                      "stable",decision.stable,"on",len(names),
                      "observer_hwnd",getattr(self.observer,"hwnd",None),
                      "source",getattr(result,"source_id",None),
                      "frame",getattr(result,"frame_id",None),
                      "sum",bool(self.current_sum),
                      "positioned",bool(self.overlay_positioned),
                      flush=True)
        self._selection_quality=decision.state
        self._refresh_trace_name_colors()
        self._selection_last_status=decision.reason
        if self._hold_selection_display(decision):
            # V8.107 display-only bridge of a 3/3 re-arm: SUM stays drawn,
            # but no new solve is authorized until the lock is valid again.
            self.solve.setEnabled(False)
            self.selection_warning.setText("Đang xác minh lại tick…")
            self.selection_warning.setToolTip(decision.reason)
            self.selection_warning.show()
            return
        if decision.state in ("transient","pending"):
            # V8.156: the short, provenance-checked SUM bridge already
            # returned above in _hold_selection_display(). If that gate
            # declined (unsafe reason, changed source, or grace expired),
            # old Auto Phase candidates must be discarded, not left in RAM.
            # EQ/FIR computed data are retained separately with strict
            # source/tick/export gates; Auto Phase results are not reusable
            # without a fresh verified pair.
            self._set_tick_presentation(False)
            self.selection_warning.setText(
                ("Chưa xác minh tick — giữ các Trace đang chọn trong vùng nhìn thấy" if decision.state=="transient" else
                 f"Xác minh tick {decision.stable}/3"))
            self.selection_warning.setToolTip(decision.reason)
            self.selection_warning.show()
            notice_key=(decision.state, decision.reason)
            if (decision.state=='transient' and
                    getattr(self,'_last_tick_notice',None)!=notice_key):
                from signal_tools_gui_v813 import show_notice
                target=self.graph_phase if self.graph_phase.isVisible() else self
                show_notice(target, 'Chưa xác minh được tick. Giữ hàng Trace trong vùng nhìn thấy; '
                            'chờ quét ổn định. Chi tiết: '+decision.reason)
                self._last_tick_notice=notice_key
            return
        if decision.state=="invalid":
            if self.controller.last_pair:
                self.controller.invalidate("Verified active count != 2")
            self._set_tick_presentation(False)
            count=decision.count or 0
            self.selection_warning.setText(
                f"Đang bật {count} Trace — cần đúng 2")
            self.selection_warning.setToolTip(
                "Trace bật: "+", ".join(Path(n).stem for n in names))
            self.selection_warning.show()
            if getattr(self,'_last_tick_notice',None)!=('count',count):
                from signal_tools_gui_v813 import show_notice
                target=self.graph_phase if self.graph_phase.isVisible() else self
                show_notice(target, f'Auto Phase cần đúng 2 Trace được tick; đang thấy {count}. '
                            'Auto EQ và FIR cần đúng 1 Trace.')
                self._last_tick_notice=('count',count)
            return
        # Pair can be committed ONLY after three matching complete scans.
        self._selection_valid_at=_selection_now()
        self.selection_warning.hide()
        self._last_tick_notice=None
        if decision.changed or self.controller.last_pair!=decision.pair:
            self.controller.apply(decision.pair,"Win UIA tick stable 3/3")
        self._set_tick_presentation(True)
        if self.current_traces:self.solve.setEnabled(True)
        self.status.setText("Trace verified, stable 3/3")

    def _hold_selection_display(self,decision):
        """V8.107: keep the committed pair DRAWN across one 3/3 re-arm.

        Only an incomplete scan (transient) or a re-arm of the SAME committed
        pair (pending) is bridged, for at most TRANSIENT_DISPLAY_GRACE_S since
        the last valid decision. Any complete contradicting evidence (other
        pair, count != 2, scanner pair/path mismatch) is never bridged.
        """
        if not getattr(self,"_selection_verified",False):return False
        committed=self.tick_gate.committed
        if committed is None or self.controller.last_pair!=committed:
            return False
        if decision.state=="transient":
            # V8.109: only a transient pixel/viewport READ failure can
            # bridge a previously verified pair. A new HWND, uninitialized
            # Data Bar, unsupported Smaart edition or absent host cannot.
            safe_scan_prefixes=(
                "Scroll changed during capture",
                "No unambiguous rows in viewport",
                "Visible tick ambiguous",
                "Tick chưa xác minh:",
                "READ ERROR:",
            )
            if not decision.reason.startswith(safe_scan_prefixes):
                return False
        elif decision.state=="pending":
            if self.tick_gate.signature!=("valid",committed):return False
        else:
            return False
        from mageq_presentation_gate_v853 import TRANSIENT_DISPLAY_GRACE_S
        age=_selection_now()-getattr(self,"_selection_valid_at",-1e30)
        return 0<=age<=TRANSIENT_DISPLAY_GRACE_S

    def should_poll_selection(self,target):
        # The companion popup may have focus while Smaart still hosts
        # the native Data Bar. A second application cannot poll.
        return bool(target and self._target_is_foreground(target.hwnd))

    def _handle_scan_future(self,task):
        try:
            result=task.result()
        except Exception as exc:
            result=SyncResult(None,"READ ERROR: "+str(exc)[:120],
                              0,max(0,len(self.observer.order)),
                              True,time.perf_counter())
        self.events.found.emit(result)

    def _clear_phase_match(self):
        if hasattr(self,"phase_match_label"):
            self.phase_match_label.setText("LF/HF PHASE MATCH: -- % (0 bins)")
        if hasattr(self,"sum_ref_label"):
            self.sum_ref_label.setText("Δ SUM–REF: -- °  |  P95: -- °")
        if hasattr(self,"graph_phase"):
            self.graph_phase.phase_match_value=None
            self.graph_phase.phase_match_bins=0
            self.graph_phase.update()

    def _update_phase_match(self):
        if not getattr(self,"current_traces",None):
            self._clear_phase_match()
            return
        try:
            percentage,bins=phase_match_percent(
                *self._ordered_traces(),
                delay_ms=self.delay.value(),
                invert_trace2=self.invert.isChecked(),
                lf=self.lf.value(),hf=self.hf.value(),coh_gate=.60)
        except (ValueError,FloatingPointError):
            percentage,bins=None,0
        self.graph_phase.phase_match_value=percentage
        self.graph_phase.phase_match_bins=bins
        try:
            delta,p95,delta_bins=sum_ref_phase_delta(
                *self._ordered_traces(),
                delay_ms=self.delay.value(),
                invert_other=self.invert.isChecked(),
                lf=self.lf.value(),hf=self.hf.value(),coh_gate=.60)
        except (ValueError,FloatingPointError):
            delta,p95,delta_bins=None,None,0
        if delta is None:
            self.sum_ref_label.setText(
                f"Δ SUM–REF: -- ° | P95: -- ° ({delta_bins} bins)")
        else:
            self.sum_ref_label.setText(
                f"Δ SUM–REF: {delta:.2f}° | P95: {p95:.2f}°")
        if percentage is None:
            self.phase_match_label.setText(
                f"LF/HF PHASE MATCH: -- % ({bins} bins)")
        else:
            self.phase_match_label.setText(
                f"LF/HF PHASE MATCH: {percentage:.1f}% ({bins} bins)")
        self.graph_phase.update()

    def _sync_roi_to_graphs(self):
        lf=float(self.lf.value());hf=float(self.hf.value())
        for graph in (self.graph_phase,self.graph_mag):
            graph.lf_hz=lf
            graph.hf_hz=hf
            graph.update()
        for marker in self.roi_markers.values():
            marker.set_frequency(lf if marker.kind=="LF" else hf)
        self._position_roi_markers()
        self._update_phase_match()

    def on_roi_changed(self,*_):
        if self.roi_updating:
            return
        self.roi_updating=True
        try:
            lf=float(self.lf.value())
            hf=float(self.hf.value())
            if lf>=hf / (2**0.025):
                if self.sender() is self.lf:
                    self.lf.setValue(bound_drag("LF",lf,lf,hf))
                else:
                    self.hf.setValue(bound_drag("HF",hf,lf,hf))
            self._sync_roi_to_graphs()
            if self.last_solve is not None:
                self.last_solve=None
                self._clear_candidate_buttons()
                self.status.setText("ROI changed - nhan AUTO ALIGN de tinh lai")
        finally:
            self.roi_updating=False

    def on_roi_drag(self,kind,global_x,source_plot="phase"):
        if not self.plot_layout:
            return
        if source_plot not in ("phase","mag"):
            raise ValueError("Unknown ROI plot")
        x,y,w,h=getattr(self.plot_layout,source_plot)
        graph=getattr(self,"graph_"+source_plot)
        frequency=x_to_hz(global_x,x,w,graph.f_min,graph.f_max)
        lf=float(self.lf.value())
        hf=float(self.hf.value())
        bounded=bound_drag(kind,frequency,lf,hf)
        widget=self.lf if kind=="LF" else self.hf
        if abs(widget.value()-bounded) >= 0.05:
            widget.setValue(round(bounded,1))
        print(f"V73_ROI_DRAG {kind} {widget.value():.1f} Hz",flush=True)

    def set_eq_roi_range(self,lf,hf):
        lf,hf=float(lf),float(hf)
        if not (20.<=lf<hf<=20000.):
            raise ValueError("Invalid Auto EQ ROI frequencies")
        self.eq_roi_lf_hz,self.eq_roi_hf_hz=lf,hf
        self.graph_mag.eq_lf_hz,self.graph_mag.eq_hf_hz=lf,hf
        for name,marker in self.eq_roi_markers.items():
            marker.set_frequency(lf if name=="LF" else hf)
        self._position_eq_roi_markers()
        self.graph_mag.update()

    def on_eq_roi_drag(self,kind,global_x):
        if getattr(self,"overlay_tool_mode",None)!="eq" or not self.plot_layout:
            return
        x,_,w,_=self.plot_layout.mag
        callback=self.eq_roi_drag_callback
        if callable(callback):
            callback(kind,x_to_hz(global_x,x,w,
                    self.graph_mag.f_min,self.graph_mag.f_max))

    def _position_eq_roi_markers(self):
        if not hasattr(self,"eq_roi_markers") or not self.plot_layout:return
        x,y,w,h=self.plot_layout.mag
        for name,marker in self.eq_roi_markers.items():
            hz=self.eq_roi_lf_hz if name=="LF" else self.eq_roi_hf_hz
            mid=round(hz_to_x(hz,x,w,self.graph_mag.f_min,self.graph_mag.f_max))
            pos=(mid-marker.width()//2,y+5)
            if (marker.x(),marker.y())!=pos:marker.move(*pos)
        for name,grip in self.eq_roi_line_grips.items():
            hz=self.eq_roi_lf_hz if name=="LF" else self.eq_roi_hf_hz
            grip.set_line_geometry((x,y,w,h),hz,
                                  fmin=self.graph_mag.f_min,fmax=self.graph_mag.f_max)

    def set_fir_roi_range(self,lf,hf,mode="mag"):
        """Synchronize the independent FIR edit guides with its sidebar."""
        if mode not in ("mag","phase"):
            raise ValueError("Unknown FIR plot mode")
        lf,hf=float(lf),float(hf)
        self.fir_roi_lf_hz,self.fir_roi_hf_hz=lf,hf
        self.fir_roi_mode=mode
        for graph in (self.graph_phase,self.graph_mag):
            graph.fir_lf_hz=lf
            graph.fir_hf_hz=hf
            graph.update()
        for name,marker in self.fir_roi_markers.items():
            marker.set_frequency(lf if name=="LF" else hf)
        self._position_fir_roi_markers()
        self.refresh_visibility()

    def on_fir_roi_drag(self,kind,global_x):
        if (self.overlay_tool_mode!="fir" or
                not self.overlay_workspace_visible or
                not self.overlay_positioned or
                self.plot_layout is None):
            return
        callback=self.fir_roi_drag_callback
        if callable(callback):
            x,_,w,_=getattr(self.plot_layout,self.fir_roi_mode)
            graph=getattr(self,'graph_'+self.fir_roi_mode)
            callback(kind,x_to_hz(global_x,x,w,graph.f_min,graph.f_max))

    def _position_fir_roi_markers(self):
        if not getattr(self,"fir_roi_markers",None) or self.plot_layout is None:
            return
        x,y,w,h=getattr(self.plot_layout,self.fir_roi_mode)
        for name,marker in self.fir_roi_markers.items():
            hz=self.fir_roi_lf_hz if name=="LF" else self.fir_roi_hf_hz
            graph=getattr(self,'graph_'+self.fir_roi_mode)
            mid=round(hz_to_x(hz,x,w,graph.f_min,graph.f_max))
            pos=(mid-marker.width()//2,y+5)
            if (marker.x(),marker.y())!=pos:
                marker.move(*pos)
        for name,grip in self.fir_roi_line_grips.items():
            hz=self.fir_roi_lf_hz if name=="LF" else self.fir_roi_hf_hz
            graph=getattr(self,'graph_'+self.fir_roi_mode)
            grip.set_line_geometry((x,y,w,h),hz,
                                   fmin=graph.f_min,fmax=graph.f_max)

    def _position_roi_markers(self):
        if not hasattr(self,"roi_markers") or not getattr(self,"plot_layout",None):
            return
        x,y,w,h=self.plot_layout.phase
        for name,marker in self.roi_markers.items():
            hz=self.lf.value() if name=="LF" else self.hf.value()
            mid=round(hz_to_x(hz,x,w,
                              self.graph_phase.f_min,self.graph_phase.f_max))
            px=mid-marker.width()//2
            py=y+5
            if marker.pos().x()!=px or marker.pos().y()!=py:
                marker.move(px,py)
        # Each narrow interactive strip covers the dashed line from
        # below the label to the bottom of the Phase plot. Reanchor on
        # ROI frequency, Smaart move/resize and Mag/Phase plot swap.
        for plot,grips in (("phase",self.roi_line_grips),
                           ("mag",self.mag_roi_line_grips)):
            rect=getattr(self.plot_layout,plot)
            for name,grip in grips.items():
                hz=self.lf.value() if name=="LF" else self.hf.value()
                graph=getattr(self,"graph_"+plot)
                grip.set_line_geometry(rect,hz,
                     label_margin=0 if plot=="mag" else None,
                     fmin=graph.f_min,fmax=graph.f_max)
        self._position_eq_roi_markers()
        self._position_fir_roi_markers()

    def update_y_ranges(self,*_):
        """Pure viewport transform: NEVER rerun complex SUM or Auto Align."""
        if not hasattr(self,"graph_mag"):return
        if self.mag_max.value()>self.mag_min.value():
            self.graph_mag.y_min=self.mag_min.value()
            self.graph_mag.y_max=self.mag_max.value()
        if self.phase_max.value()>self.phase_min.value():
            self.graph_phase.y_min=self.phase_min.value()
            self.graph_phase.y_max=self.phase_max.value()
        self.graph_mag.update()
        self.graph_phase.update()

    def _apply_phase_pan(self,shift_px,drag_state,verified=False,confidence=0.):
        if not getattr(self,"plot_layout",None):
            return
        _,_,_,height=self.plot_layout.phase
        if height<=0:
            return
        lo,hi=shifted_y_range(drag_state["lo"],drag_state["hi"],
                             height,shift_px)
        now=time.monotonic()
        if now-getattr(self,"_drag_spin_tick",0.)>.15:
            self._drag_spin_tick=now
            self.phase_min.blockSignals(True)
            self.phase_max.blockSignals(True)
            try:
                self.phase_min.setValue(lo)
                self.phase_max.setValue(hi)
            finally:
                self.phase_min.blockSignals(False)
                self.phase_max.blockSignals(False)
        self.graph_phase.y_min=lo
        self.graph_phase.y_max=hi
        self.graph_phase.update()
        label=("Native-trace verified" if verified else
               "Mouse-motion preview (Y cần kiểm tra)")
        self.phase_axis_note.setText(
            f"Phase Y sync {label}: shift {shift_px:+.0f}px"
            + (f" | confidence {confidence:.2f}" if verified else ""))

    def on_absolute_phase_axis(self,payload):
        """Idle-only absolute Y anchor; never fight live gesture tracking."""
        key,result=payload
        if getattr(self,"axis_drag",None) is not None:return
        if (getattr(self,"mag_axis_drag",None) is not None or
            time.monotonic()-self.pan_last_move < .65):
            return
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index(),
                  self._phase_axis_generation)
        if key!=expected or result is None:return
        fit=result.fit if isinstance(result,FastFitResult) else result
        now=time.monotonic()
        if isinstance(result,FastFitResult):
            self.axis_task_ms.append(result.elapsed_ms)
            if len(self.axis_task_ms)>120:self.axis_task_ms.pop(0)
            # Never render a stale frame when Windows/PrintWindow stalls.
            if now-result.frame_time>0.55:
                return
        if not fit.accepted:
            self.axis_rejected+=1
            if now-self.axis_last_status>.8:
                self.axis_last_status=now
                self.phase_axis_note.setText(
                    "Phase Y fast: khong xac nhan ("+fit.reason[:55]+")")
            return
        self.axis_accepted+=1
        previous=float(self.graph_phase.y_max)
        if abs(float(fit.top_deg)-previous)<.7:
            return
        lo,hi=fit.bottom_deg,fit.top_deg
        # Fast paint only; changing 2 spinbox widgets every frame is costly.
        self.graph_phase.y_min=lo
        self.graph_phase.y_max=hi
        self.graph_phase.update()
        if now-self.axis_last_spin>.12:
            self.axis_last_spin=now
            self.phase_min.blockSignals(True)
            self.phase_max.blockSignals(True)
            try:
                self.phase_min.setValue(lo)
                self.phase_max.setValue(hi)
            finally:
                self.phase_min.blockSignals(False)
                self.phase_max.blockSignals(False)
        if now-self.axis_last_status>.22:
            self.axis_last_status=now
            mode=result.mode if isinstance(result,FastFitResult) else "native"
            ms=result.elapsed_ms if isinstance(result,FastFitResult) else 0
            self.phase_axis_note.setText(
                f"Phase Y FAST REF{self._reference_index()+1}: "
                f"{lo:.0f}..{hi:.0f} deg | {fit.hit_fraction:.0%} | "
                f"{mode} {ms:.0f}ms")
        print("V80_FAST_PHASE_Y_CAL",
              key[3],lo,hi,round(fit.hit_fraction,3),
              result.mode if isinstance(result,FastFitResult) else "test",
              round(result.elapsed_ms,1) if isinstance(result,FastFitResult) else 0,
              flush=True)

    def _schedule_absolute_axis_calibration(self,target):
        if not self.current_sum or not self.plot_layout or not self.current_traces:
            return
        now=time.monotonic()
        if now-self.pan_last_move<.65:return
        ref,other=self._ordered_traces()
        key=(target.hwnd,self.plot_layout.phase,
             tuple(self.current_pair or ()),self._reference_index(),
             self._phase_axis_generation)
        from native_poll_budget_v8162 import poll_due,PHASE_AXIS_STEADY_SECONDS
        if not poll_due(now=now,last_started=self.axis_requested,
                        key=key,last_key=self._axis_poll_identity,
                        steady_seconds=PHASE_AXIS_STEADY_SECONDS):
            return
        if self.axis_future is not None and not self.axis_future.done():
            return
        current_top=float(self.graph_phase.y_max)
        self.axis_requested=now
        self._axis_poll_identity=key
        self.axis_future=self.axis_pool.submit(
            capture_fit_fast,target.hwnd,self.plot_layout.phase,
            ref,other,current_top)
        def callback(task,k=key):
            try:
                self.events.axis_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V80_FAST_AXIS_CAPTURE_ERROR",str(exc)[:130],flush=True)
        self.axis_future.add_done_callback(callback)

    def _mag_axis_request_key(self,hwnd):
        return (hwnd,self.plot_layout.mag,
                tuple(self.current_pair or ()),self._reference_index(),
                tuple(t.file_mtime_ns for t in self.current_traces),
                self._mag_axis_generation)

    def on_mag_ref_anchor(self,payload):
        """Use a verified native trace's full Y transform. H and EQ untouched."""
        key,fit=payload
        if not self.current_sum or not self.current_traces or not self.plot_layout:
            return
        if not self.mag_fit.isChecked() or not isinstance(fit,SumMagAxis):
            return
        if key!=self._mag_axis_request_key(self.plot_hwnd):return
        if (getattr(self,"mag_axis_drag",None) is not None or
            time.monotonic()-self.mag_pan_last_move<.65):return
        if not fit.accepted:
            self.mag_anchor_failed+=1
            # One ambiguous frame must not make a previously calibrated
            # SUM Mag disappear while moving the native Smaart Y axis.
            if self.mag_anchor_failed>=3 and time.monotonic()-self.mag_pan_last_move>1.1:
                self._mag_anchor_verified=False
                self.graph_mag.native_axis_ready=False
                if getattr(self,"_active_smaart_major",None)==8:
                    self.graph_phase.native_x_axis_ready=False
                    self.graph_phase.update()
                self.graph_mag.update()
            if self.mag_anchor_failed<=3:
                print("V826_MAG_NATIVE_HOLD",fit.reason,flush=True)
            return
        if not self._mag_anchor_verified:
            t0=getattr(self,"_static_mag_first_paint_at",None)
            if t0 is not None:
                print("V8180_STATIC_MAG_NATIVE_READY_MS",
                      round((time.monotonic()-t0)*1000.,1),
                      "source_score",round(fit.score,3),flush=True)
                self._static_mag_first_paint_at=None
        self.mag_anchor_accepted+=1
        self.mag_anchor_failed=0
        self._mag_anchor_verified=True
        # Native provenance supplies BOTH the Y mapping and the exact
        # logarithmic X span; use the same X on SUM Phase, SUM Mag and ROI.
        xlo=float(getattr(fit,"x_min",20.))
        xhi=float(getattr(fit,"x_max",20000.))
        if not (0<xlo<xhi):return
        for graph in (self.graph_phase,self.graph_mag):
            graph.f_min,graph.f_max=xlo,xhi
            graph.native_x_axis_ready=True
            graph._paint_cache=None
            graph.update()
        self._position_roi_markers()
        self.graph_mag.native_axis_ready=True
        self.graph_mag.display_offset_db=0.0
        self.graph_mag.native_axis_label=(f"0 dB GRID {fit.score:.0%}"
                    if fit.source_index<0 and fit.color=="GRID" else
                    f"{fit.color.upper()} {fit.score:.0%}")
        before=(self.graph_mag.y_min,self.graph_mag.y_max)
        self.graph_mag.y_min=float(fit.y_min)
        self.graph_mag.y_max=float(fit.y_max)
        self.mag_min.blockSignals(True)
        self.mag_max.blockSignals(True)
        try:
            self.mag_min.setValue(fit.y_min)
            self.mag_max.setValue(fit.y_max)
        finally:
            self.mag_min.blockSignals(False)
            self.mag_max.blockSignals(False)
        self.graph_mag.update()
        if (self.mag_anchor_accepted==1 or
            max(abs(before[0]-fit.y_min),abs(before[1]-fit.y_max))>.35):
            provenance=("0 dB + Smaart GRID"
                        if fit.source_index<0 and fit.color=="GRID" else
                        f"Trace {fit.source_index+1} {fit.color}")
            self.axis_note.setText(
                f"SUM MAG Y NATIVE: {provenance} {fit.score:.0%}"
                " | no display gain")
            print("V826_SUM_MAG_NATIVE_AXIS",
                  fit.color,fit.source_index,round(fit.score,3),
                  round(fit.y_min,3),round(fit.y_max,3),
                  "OFFSET_ZERO",flush=True)

    def _schedule_mag_ref_anchor(self,target):
        if not self.current_sum or not self.current_traces or not self.plot_layout:
            return
        if not self.mag_fit.isChecked():return
        now=time.monotonic()
        if now-self.mag_pan_last_move<.65:return
        key=self._mag_axis_request_key(target.hwnd)
        # Changed trace/viewport/smoothing => verify a fresh native frame.
        # In steady state do not redo the ~1s full-color Y-fit each second.
        from native_poll_budget_v8162 import (
            poll_due,MAG_ANCHOR_STEADY_SECONDS,
            MAG_ANCHOR_FIRST_RETRY_SECONDS,
            MAG_ANCHOR_RECOVERY_RETRY_SECONDS,
            MAG_ANCHOR_HOLD_RETRY_SECONDS)
        identity=(key,self._verified_mag_smoothing_for_offset())
        # Static TRF startup/theme-switch: retry NEW native pixel proof
        # promptly. Previous V8.180 jumped to a 5-second poll after two
        # misses, leaving SUM MAG empty despite unchanged measurement data.
        # Every retry still requires fresh PrintWindow+X/Y/source identity.
        if self._mag_anchor_verified:
            interval=MAG_ANCHOR_STEADY_SECONDS
        elif self.mag_anchor_failed<3:
            interval=MAG_ANCHOR_FIRST_RETRY_SECONDS
        elif self.mag_anchor_failed<6:
            interval=MAG_ANCHOR_RECOVERY_RETRY_SECONDS
        else:
            interval=MAG_ANCHOR_HOLD_RETRY_SECONDS
        if not poll_due(now=now,last_started=self.mag_anchor_requested,
                        key=identity,last_key=self._mag_anchor_poll_identity,
                        steady_seconds=interval):
            return
        if self.mag_anchor_future is not None and not self.mag_anchor_future.done():
            return
        if identity!=self._mag_anchor_poll_identity:
            self.mag_anchor_failed=0
        self.mag_anchor_requested=now
        self._mag_anchor_poll_identity=identity
        self.mag_anchor_future=self.mag_anchor_pool.submit(
            capture_sum_mag_axis,target.hwnd,self.plot_layout.mag,
            tuple(self.current_traces))
        def on_finished(task,k=key):
            try:
                self.events.mag_anchor_ready.emit((k,task.result()))
            except Exception as exc:
                print("V826_MAG_NATIVE_READ_ERROR",str(exc)[:140],flush=True)
        self.mag_anchor_future.add_done_callback(on_finished)

    def on_native_dual_pan(self,payload):
        key,result=payload
        if not self.current_sum or not self.plot_layout or not isinstance(result,DualPanResult):
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  self.plot_layout.mag,tuple(self.current_pair or ()),
                  self._reference_index())
        # Worker captured before/during a 160+ px mouse drag MUST NOT
        # apply its stale delta once the pointer is released.
        if len(key)==6 and key[5]!=getattr(self,"_viewport_epoch",0):return
        if key[:5]!=expected:
            return
        phase_key=(key[0],key[1],key[3],key[4])
        mag_key=(key[0],key[2],key[3],key[4])
        self.on_native_fast_pan((phase_key,result.phase))
        self.on_native_mag_pan((mag_key,result.mag))

    def _apply_native_y_delta(self,kind,frame):
        """Viewport-only movement; keep the stored complex TF and SUM unchanged."""
        now=time.monotonic()
        is_mag=kind=="mag"
        stamp_key="_mag_pan_last_frame" if is_mag else "_phase_pan_last_frame"
        previous=float(getattr(self,stamp_key,0.))
        # Mouse position alone cannot prove Smaart moved its Y axis.
        # Accept only native pixel-correlated motion, even during drag.
        threshold=.90 if is_mag else .85
        if not trusted_pan(frame,now,previous,minimum_confidence=threshold):
            if is_mag:self.mag_pan_rejected+=1
            else:self.pan_rejected+=1
            return
        setattr(self,stamp_key,float(frame.frame_time))
        dy=float(frame.delta_px)
        if abs(dy)<.75:return
        plot_rect=self.plot_layout.mag if is_mag else self.plot_layout.phase
        graph=self.graph_mag if is_mag else self.graph_phase
        try:
            lo,hi,offset=translated_y_range(
                graph.y_min,graph.y_max,plot_rect[3],dy)
        except ValueError:
            if is_mag:self.mag_pan_rejected+=1
            else:self.pan_rejected+=1
            return
        graph.y_min=lo
        graph.y_max=hi
        graph.update()
        if is_mag:
            self.mag_pan_last_move=now
            self.mag_pan_accepted+=1
            self._mag_axis_generation+=1
            spin_time="mag_pan_last_spin"
            min_spin,max_spin=self.mag_min,self.mag_max
        else:
            self.pan_last_move=now
            self.pan_accepted+=1
            self._phase_axis_generation+=1
            spin_time="axis_last_spin"
            min_spin,max_spin=self.phase_min,self.phase_max
        if now-getattr(self,spin_time,0.)>.12:
            setattr(self,spin_time,now)
            min_spin.blockSignals(True)
            max_spin.blockSignals(True)
            try:
                min_spin.setValue(lo)
                max_spin.setValue(hi)
            finally:
                min_spin.blockSignals(False)
                max_spin.blockSignals(False)
        # Native positive pixel translation => both overlay Y axes move down.
        if is_mag:
            if now-self.mag_pan_last_status>.22:
                self.mag_pan_last_status=now
                self.mag_axis_note.setText(
                    f"Mag Y theo Smaart: {dy:+.0f}px / {offset:+.2f}dB | "
                    f"{frame.confidence:.0%}")
            if now-self.mag_pan_last_log>.30:
                self.mag_pan_last_log=now
                print("V828_MAG_Y_FOLLOW",dy,round(offset,3),
                      round(frame.confidence,3),round(hi,2),flush=True)
        else:
            if now-self.axis_last_status>.22:
                self.axis_last_status=now
                self.phase_axis_note.setText(
                    f"Phase Y theo Smaart: {dy:+.0f}px / {offset:+.2f}deg | "
                    f"{frame.confidence:.0%}")
            if now-self.pan_last_log>.25:
                self.pan_last_log=now
                print("V828_PHASE_Y_FOLLOW",dy,round(offset,3),
                      round(frame.confidence,3),round(hi,2),flush=True)

    def on_native_mag_pan(self,payload):
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.mag,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        # No arbitrary Y position before a native trace has been registered.
        if not self._mag_anchor_verified:return
        self._apply_native_y_delta("mag",frame)

    def on_native_fast_pan(self,payload):
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        self._apply_native_y_delta("phase",frame)

    def _schedule_fast_pan(self,target):
        if not self.current_sum or not self.plot_layout:
            return
        now=time.monotonic()
        # V8.161: expensive native PrintWindow/pixel pan polling is kept
        # fast ONLY while the operator drags the native Y ruler.
        # Wheel/passive monitoring remains active at 5.5 Hz; the separate
        # absolute Phase and native Mag axis workers still run unchanged.
        active_kind=("phase" if getattr(self,"axis_drag",None) is not None
                     else "mag" if getattr(self,"mag_axis_drag",None) is not None
                     else None)
        if now-self.pan_requested < _native_pan_min_interval(active_kind):
            return
        if self.pan_future is not None and not self.pan_future.done():return
        key=(target.hwnd,self.plot_layout.phase,self.plot_layout.mag,
             tuple(self.current_pair or ()),self._reference_index(),
             getattr(self,"_viewport_epoch",0))
        self.pan_requested=now
        self.pan_future=self.pan_pool.submit(
            self.pan_tracker.poll,key,self.plot_layout.phase,
            self.plot_layout.mag,active_kind)
        def done(task,k=key):
            try:
                self.events.pan_snapshot.emit((k,task.result()))
            except Exception as exc:
                print("V82_DUAL_PAN_WORKER_ERROR",str(exc)[:130],flush=True)
        self.pan_future.add_done_callback(done)

    def _fast_y_drag_tick(self):
        # Only pointer/Qt work on the GUI thread. Capture and native fitting
        # remain on their own workers and cannot block the 16ms fast lane.
        if not getattr(self,"plot_layout",None) or not self.current_sum:return
        hwnd=getattr(self,"plot_hwnd",None)
        if not hwnd or not self._target_is_foreground(hwnd):return
        target=SimpleNamespace(hwnd=hwnd)
        self._check_phase_axis_drag(target)
        self._check_mag_axis_drag(target)
        if (getattr(self,"axis_drag",None) is not None or
            getattr(self,"mag_axis_drag",None) is not None):
            self._schedule_fast_pan(target)

    def _check_mag_axis_drag(self,target):
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            self.mag_axis_drag=None
            return
        x,y,w,h=self.plot_layout.mag
        try:
            px,py=win32api.GetCursorPos()
            held=bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON)&0x8000)
        except Exception:return
        state=getattr(self,"mag_axis_drag",None)
        if state is None:
            if not held:
                self._mag_was_pressed=False
                return
            if getattr(self,"_mag_was_pressed",False):return
            self._mag_was_pressed=True
            if getattr(self,"axis_drag",None) is not None:return
            if not (x-72<=px<=x+6 and y+10<=py<=y+h-10):return
            if not getattr(self,"_mag_anchor_verified",False):return
            self.mag_axis_drag={"start":(px,py),"lo":self.graph_mag.y_min,
                                "hi":self.graph_mag.y_max,
                                "rect":self.plot_layout.mag,"preview_shift":0.}
            self._viewport_epoch=getattr(self,"_viewport_epoch",0)+1
            self._mag_axis_generation+=1
            self._mag_pan_last_frame=time.monotonic()
            print("V834_MAG_GESTURE_BEGIN",px,py,flush=True)
            return
        if held:
            movement=float(py-state["start"][1])
            if abs(movement-state["preview_shift"])<1.:return
            state["preview_shift"]=movement
            # Record pointer activity only. Do not invent viewport motion;
            # on_native_dual_pan applies verified Smaart trace pixels.
            return
        self.mag_axis_drag=None
        self._mag_was_pressed=False
        self._viewport_epoch=getattr(self,"_viewport_epoch",0)+1
        self._mag_axis_generation+=1
        self._mag_pan_last_frame=time.monotonic()
        self.mag_pan_last_move=time.monotonic()
        self.mag_anchor_requested=0.
        print("V834_MAG_GESTURE_RELEASE",
              round(state["preview_shift"],1),flush=True)

    def _check_phase_axis_drag(self,target):
        """Follow real Smaart Phase ruler while mouse held; settle to native REF."""
        if not getattr(self,"plot_layout",None) or not self.current_sum:
            self.axis_drag=None
            return
        x,y,w,h=self.plot_layout.phase
        try:
            px,py=win32api.GetCursorPos()
            held=bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON)&0x8000)
        except Exception:
            return
        if self.axis_drag is None:
            if not held:
                self._axis_was_pressed=False
                return
            if self._axis_was_pressed:return
            self._axis_was_pressed=True
            if not(x-72<=px<=x+6 and y+10<=py<=y+h-10):
                return
            self.axis_drag={
                "hwnd":target.hwnd,
                "start":(px,py),
                "lo":self.graph_phase.y_min,
                "hi":self.graph_phase.y_max,
                "rect":self.plot_layout.phase,
                "preview_shift":0.}
            # Invalidate all already-captured absolute and relative frames.
            self._phase_axis_generation+=1
            self._viewport_epoch=getattr(self,"_viewport_epoch",0)+1
            self._phase_pan_last_frame=time.monotonic()
            print("V829_PHASE_GESTURE_BEGIN",px,py,
                  round(self.graph_phase.y_max,1),flush=True)
            return
        state=self.axis_drag
        if held:
            move=float(py-state["start"][1])
            if abs(move-state["preview_shift"])>=1.:
                state["preview_shift"]=move
                # Native dual-pan drives both overlays. The pointer alone
                # is not a valid Smaart-axis movement signal.
            return
        # Do not force a snap from raw mouse motion on release. A fresh
        # native REF fit can reconcile the viewport after real Smaart paints.
        self.axis_drag=None
        self._axis_was_pressed=False
        self._phase_axis_generation+=1
        self._viewport_epoch=getattr(self,"_viewport_epoch",0)+1
        self._phase_pan_last_frame=time.monotonic()
        self.pan_last_move=time.monotonic()
        self.axis_requested=0.
        print("V829_PHASE_GESTURE_RELEASE",
              round(state["preview_shift"],1),
              round(self.graph_phase.y_max,1),flush=True)

    def on_plot_layout(self,payload):
        # Never apply a stale async result captured for the other Smaart HWND.
        # A failed probe must retain its original HWND, so a V8 failure does
        # not hide a valid Suite overlay (or vice versa).
        if payload is not None:
            hwnd,verified_layout=payload
            active=locate_smaart(prefer_hwnd=getattr(self,"plot_hwnd",None) or getattr(self.observer,"hwnd",None))
            if (active is None or active.hwnd!=hwnd or
                    not self._target_is_foreground(hwnd)):
                return
            if verified_layout is None:
                payload=None
        if payload is None:
            # A single UIA/PrintWindow miss must not erase both valid SUMs.
            # Retain only if the SAME Smaart HWND remains at exactly the
            # same position/size, for at most 2.5s after a verified layout.
            hwnd=getattr(self,"plot_hwnd",None)
            prior=getattr(self,"_plot_native_window_rect",None)
            recent=time.monotonic()-getattr(self,"_plot_last_good",0.)<2.5
            if hwnd and prior and recent:
                try:
                    if (win32gui.IsWindow(hwnd) and
                        not win32gui.IsIconic(hwnd) and
                        win32gui.GetWindowRect(hwnd)==prior):
                        return
                except Exception:
                    pass
            self.plot_layout=None
            self.overlay_positioned=False
            self.refresh_visibility()
            return
        hwnd,layout=payload
        self._plot_last_good=time.monotonic()
        try:self._plot_native_window_rect=win32gui.GetWindowRect(hwnd)
        except Exception:self._plot_native_window_rect=None
        changed=(self.plot_hwnd!=hwnd or self.plot_layout is None or
                 self.plot_layout.phase!=layout.phase or
                 self.plot_layout.mag!=layout.mag or
                 getattr(self.plot_layout,"theme","dark")!=getattr(layout,"theme","dark"))
        if changed:
            self._static_mag_first_paint_at=time.monotonic()
            print("V812_ROLE_GEOMETRY",hwnd,layout.phase,layout.mag,flush=True)
            self.axis_drag=None
            self._axis_was_pressed=False
            self._mag_offset_key=None
            self._mag_anchor_verified=False
            self.graph_mag.native_axis_ready=False
            self._phase_pan_last_frame=0.0
            self._mag_pan_last_frame=0.0
            self._phase_axis_generation+=1
            self._mag_axis_generation+=1
            # Existing spatially bound async samples are rejected through
            # their old rect keys; never reuse axis displacement across
            # a swapped Mag/Phase view.
        self.plot_hwnd=hwnd
        self.plot_layout=layout
        if changed:self._apply_plot_layout()

    def _apply_plot_layout(self):
        if self.plot_layout is None:return
        theme=getattr(self.plot_layout,"theme","dark")
        for widget,rect in ((self.graph_phase,self.plot_layout.phase),
                            (self.graph_mag,self.plot_layout.mag)):
            if widget.theme!=theme:
                widget.theme=theme
                widget._paint_cache=None
                widget.update()
            if widget.geometry().getRect()!=rect:
                widget.setGeometry(*rect)
        self.overlay_positioned=True
        self._position_roi_markers()
        self.refresh_visibility()

    def on_peq_marker_drag(self,number,x,y,phase):
        callback=getattr(self,"eq_peq_drag_callback",None)
        if not callable(callback):return False
        return bool(callback(number,x,y,phase))

    def _position_eq_peq_grips(self):
        grips=getattr(self,"eq_peq_grips",{})
        if not grips:return
        graph=self.graph_mag
        source=graph.mageq_source
        frame=graph.mageq_frame
        active=(source is not None and frame is not None
                and bool(getattr(frame,"identity_verified",False))
                and frame.source_identity==source.source_identity
                and source.revision==frame.revision
                and self.overlay_positioned
                and graph.isVisible()
                and getattr(self,"overlay_tool_mode","")=="eq"
                and getattr(self,"overlay_workspace_visible",False)
                and not getattr(self,"ui_tool_enabled",False)
                and callable(getattr(self,"_eq_tick_safe",None))
                and bool(self._eq_tick_safe()))
        if active:
            from native_eq_mag_v06 import frame_is_fresh_for_window
            active=frame_is_fresh_for_window(frame,frame.hwnd)
        if active:
            try:
                from mageq_visual_v13 import build_geometry
                markers=build_geometry(source,frame).markers
            except (ValueError,AttributeError,TypeError):
                active=False
        targets={m.number:m for m in markers if m.visible} if active else {}
        for number,grip in grips.items():
            marker=targets.get(number)
            if marker is None:
                if grip.dragging:
                    # Reject/stop editing on source/viewport loss; still
                    # allow Qt to deliver release to the captured grip.
                    continue
                if grip.isVisible():grip.hide()
                continue
            if grip.dragging:continue  # capture coords remain fixed while held
            x,y,_,_=frame.plot
            rect=(round(x+marker.x-grip.width()/2),
                  round(y+marker.y-grip.height()/2),
                  grip.width(),grip.height())
            if grip.geometry().getRect()!=rect:grip.setGeometry(*rect)
            if not grip.isVisible():
                grip.show()
                grip.raise_()

    def refresh_visibility(self,*_):
        self._enforce_display_always_on()
        workspace=bool(getattr(self,"overlay_workspace_visible",True))
        mode=getattr(self,"overlay_tool_mode","phase")
        phase_active=(workspace and mode=="phase" and
                      getattr(self,"_selection_verified",True) and
                      (not self.managed_mode or self.ui_tool_enabled))
        has=(self.current_sum is not None and self.overlay_positioned
             and phase_active)
        if os.environ.get("REMIX_QA_TRACE_REARM")=="1":
            now=time.monotonic()
            signature=(bool(self.current_sum),bool(self.overlay_positioned),
                       bool(workspace),mode,bool(self._selection_verified),
                       bool(self.ui_tool_enabled),bool(has),
                       getattr(self,"plot_hwnd",None))
            if signature!=getattr(self,"_qa_vis_signature",None) or (
                    now-getattr(self,"_qa_vis_at",0.)>5.):
                self._qa_vis_signature=signature
                self._qa_vis_at=now
                print("QA_REARM_VIS","sum",signature[0],
                      "positioned",signature[1],"workspace",signature[2],
                      "mode",signature[3],"pair_verified",signature[4],
                      "tool_enabled",signature[5],"SHOW_SUM",signature[6],
                      "plot_hwnd",signature[7],flush=True)
        eq_check=getattr(self,"_eq_tick_safe",None)
        eq_active=(workspace and self.managed_mode and mode=="eq"
                   and callable(eq_check) and bool(eq_check())
                   and not self.ui_tool_enabled and
                   self.overlay_positioned)
        if self.graph_mag.eq_roi_active!=bool(eq_active):
            self.graph_mag.eq_roi_active=bool(eq_active)
            self.graph_mag.update()
        # STRICT single-owner overlay lifecycle:
        # Phase: SUM Phase + SUM Mag + LF/HF
        # EQ: MagEQ only, if computed
        # FIR uses the SAME Mag/Phase QWidgets, gated by fresh native
        # source identity and independently accepted Phase pixel evidence.
        fir_active=(workspace and self.managed_mode and mode=="fir" and
                    not self.ui_tool_enabled and self.overlay_positioned)
        valid_band=(20<=self.fir_roi_lf_hz<self.fir_roi_hf_hz<=20000 and
                    self.fir_roi_hf_hz>=2*self.fir_roi_lf_hz)
        fir_mag=bool(fir_active and valid_band and self.fir_roi_mode=="mag")
        fir_phase=bool(fir_active and valid_band and self.fir_roi_mode=="phase")
        for graph,active in ((self.graph_mag,fir_mag),
                             (self.graph_phase,fir_phase)):
            if graph.fir_roi_active!=active:
                graph.fir_roi_active=active
                graph.update()
        # Editable guides show without a solver result. Native FIR curves
        # remain separately gated by validated source/frame/axis evidence.
        self.graph_mag.setVisible(bool(has or eq_active or fir_mag))
        self.graph_phase.setVisible(bool(has or fir_phase))
        for marker in self.roi_markers.values():
            marker.setVisible(bool(has))
        for grip in (*self.roi_line_grips.values(),
                     *self.mag_roi_line_grips.values()):
            grip.setVisible(bool(has))
        for marker in self.eq_roi_markers.values():
            marker.setVisible(bool(eq_active))
        for grip in self.eq_roi_line_grips.values():
            grip.setVisible(bool(eq_active))
        for marker in self.fir_roi_markers.values():
            marker.setVisible(bool(fir_mag or fir_phase))
        for grip in self.fir_roi_line_grips.values():
            grip.setVisible(bool(fir_mag or fir_phase))
        self._position_eq_peq_grips()

    def closeEvent(self,event):
        for grip in (*self.roi_line_grips.values(),
                     *self.mag_roi_line_grips.values(),
                     *self.eq_roi_line_grips.values(),
                     *self.fir_roi_line_grips.values()):
            grip.close()
        for marker in (*self.roi_markers.values(),
                       *self.eq_roi_markers.values(),
                       *self.fir_roi_markers.values()):
            marker.close()
        for grip in getattr(self,"eq_peq_grips",{}).values():
            grip.cancel()
            grip.close()
        self.graph_mag.close()
        self.graph_phase.close()
        super().closeEvent(event)

    def _target_is_foreground(self,target_hwnd):
        front=win32gui.GetForegroundWindow()
        if not front:return False
        if front==target_hwnd:return True
        # Panel and its child popups may take focus during editing.
        # Any unrelated process => overlay MUST be hidden.
        try:
            _,pid=win32process.GetWindowThreadProcessId(front)
            return pid==os.getpid()
        except Exception:return False

    def _schedule_steady_native_proofs(self,target):
        """V8.168: at most one long native proof worker in flight.

        Phase axis, Mag axis and source offsets use independent pools. Their
        captures previously overlapped on the same 33/66ms GUI tick, causing
        transient >1-core spikes. Never reuse or waive native proof; just
        defer the next independent capture until its predecessor completes.
        Selection tick capture and the 16ms mouse-drag lane are unaffected.
        """
        from native_poll_budget_v8162 import native_proof_busy
        def busy():
            return native_proof_busy(self.axis_future,
                                     self.mag_anchor_future,
                                     self.offset_future)
        if busy():return
        # Unverified Smaart8 X-axis blocks BOTH SUM Phase and SUM MAG.
        # Give the static Mag native source a first-paint lane before the
        # unrelated Phase Y-axis worker (still serialized, no CPU spike).
        # No cached proof is ever used to authorize a new frame/export.
        mag_first=not getattr(self,"_mag_anchor_verified",True)
        if mag_first:
            self._schedule_mag_ref_anchor(target)
            if busy():return
        if self.axis_drag is None:
            self._schedule_absolute_axis_calibration(target)
            if busy():return
        if not mag_first:
            self._schedule_mag_ref_anchor(target)
            if busy():return
        self._schedule_trace_offsets(target)

    def tick(self):
        self._refresh_saved_smoothing()
        if self.demo:
            if self.host:
                attached=self.host.isVisible() and self._target_is_foreground(int(self.host.winId()))
                x,y,w,h=self.host.geometry().getRect()
                shapes=self.host.plot_boxes()
                for widget,key in [(self.graph_mag,"MAGNITUDE"),(self.graph_phase,"PHASE")]:
                    a,b,c,d=shapes[key]
                    rect=(x+a,y+b,c,d)
                    if widget.geometry().getRect()!=rect:widget.setGeometry(*rect)
                self.overlay_positioned=attached
                self.refresh_visibility()
                if attached and not self.isVisible():self.show()
                if not attached and self.isVisible():self.hide()
                if attached:
                    screen=QApplication.primaryScreen().availableGeometry()
                    px=max(screen.left()+8,min(x+w-self.width()-3,
                         screen.right()-self.width()-8))
                    py=max(screen.top()+8,min(y+55,
                         screen.bottom()-self.height()-8))
                    if self.pos().x()!=px or self.pos().y()!=py:
                        self.move(px,py)
            return
        target=locate_smaart(prefer_hwnd=getattr(self,"plot_hwnd",None) or getattr(self.observer,"hwnd",None))
        if target is not None and self.observer is not None:
            from smaart8_api3_readonly_v868 import process_smaart_major
            from smaart_runtime_paths_v868 import trace_directory
            version=process_smaart_major(target.hwnd)
            if getattr(self,"_active_smaart_major",None)!=version:
                self._active_smaart_major=version
                self._mag_anchor_verified=False
                self.graph_mag.native_axis_ready=False
                for graph in (self.graph_phase,self.graph_mag):
                    graph.require_native_x_axis=(version==8)
                    graph.native_x_axis_ready=(version!=8)
                    graph.f_min=20.
                    graph.f_max=20000.
                    graph._paint_cache=None
                    graph.update()
            target_folder=trace_directory(version) if version in (8,9) else None
            if target_folder is not None and self.observer.folder!=target_folder:
                # Switch editions without reusing a Smaart 9 tick or TRF.
                self.observer.clear("Smaart edition changed")
                self.observer.folder=target_folder
                # P0: on_selection(None) only erased the plotted SUM but
                # left SelectionController.last_pair/generation unchanged.
                # Returning to the SAME Suite pair then skipped apply(),
                # leaving current_sum=None despite valid 3/3 native ticks.
                # Invalidate controller first: cancel stale TRF futures,
                # then re-arm through THREE fresh checks on the new host.
                if not self.controller.invalidate("Smaart edition changed"):
                    self.on_selection(None)
                self.tick_gate=StableTickGate(required=3)
                self._selection_verified=False
                self.plot_hwnd=None;self.plot_layout=None
                self.overlay_positioned=False
                # The next foreground host gets a fresh native role scan.
                self.plot_requested=0.
        if target is None or not self._target_is_foreground(target.hwnd):
            self.axis_drag=None
            self._axis_was_pressed=False
            self.mag_axis_drag=None
            self._mag_was_pressed=False
            self._viewport_epoch=getattr(self,"_viewport_epoch",0)+1
            self.overlay_positioned=False;self.refresh_visibility()
            self.plot_hwnd=None;self.plot_layout=None
            self.plot_requested=0.
            if self.isVisible():self.hide()
            return
        if not self.isVisible() and (not self.managed_mode or self.ui_tool_enabled):
            self.show()
        elif self.isVisible() and self.managed_mode and not self.ui_tool_enabled:
            self.hide()
        # Passive native-plot watcher: works for wheel, gestures, and
        # mouse interactions irrespective of how the Y-axis was changed.
        self._check_phase_axis_drag(target)
        self._check_mag_axis_drag(target)
        self._schedule_fast_pan(target)
        self._schedule_steady_native_proofs(target)
        self._schedule_live_smoothing(target)
        l,t,r,b=target.rect
        if self.plot_hwnd==target.hwnd and self.plot_layout is not None:
            self._apply_plot_layout()
        else:
            self.overlay_positioned=False
            self.refresh_visibility()
        if self.isVisible() and not self.managed_mode:
            area=QApplication.primaryScreen().availableGeometry()
            px=max(area.left()+8,min(r-self.width()-3,
                   area.right()-self.width()-8))
            py=max(area.top()+8,min(t+75,
                   area.bottom()-self.height()-8))
            if abs(self.x()-px)>1 or abs(self.y()-py)>1:
                self.move(px,py)
        now=time.monotonic()
        if now-self.plot_requested>0.9 and (
            self.plot_future is None or self.plot_future.done()):
            self.plot_requested=now
            hwnd=target.hwnd
            self.plot_future=self.plot_pool.submit(locate_role_plots,hwnd)
            # Tag even failed native probes with their originating HWND.
            # on_plot_layout rejects obsolete results after a host switch.
            self.plot_future.add_done_callback(
                lambda task,h=hwnd:self.events.layout_ready.emit(
                    (h,task.result()) if not task.exception() else (h,None)))
        now=time.monotonic()
        if (self.should_poll_selection(target) and
            now-self.last_poll>.16 and
            (self.poll_future is None or self.poll_future.done())):
            self.last_poll=now
            self.poll_future=self.pool.submit(self.observer.poll,target.hwnd)
            self.poll_future.add_done_callback(self._handle_scan_future)

    def closeEvent(self,event):
        if self.managed_mode:
            # Closing the Auto Phase popup must not terminate the
            # shared Smaart TRF observer used by Auto EQ and FIR.
            self.ui_tool_enabled=False
            self.hide()
            event.ignore()
            return
        self._align_closed=True
        self._align_completion=None
        self._align_completion_timer.stop()
        self._update_closed=True
        self._update_timer.stop()
        bounded_shutdown(self._update_pool)
        self.timer.stop()
        self._align_ticket+=1
        bounded_shutdown(self._align_pool)
        # Close native full-height line hit strips and legacy labels.
        for grip in (*self.roi_line_grips.values(),
                     *self.mag_roi_line_grips.values(),
                     *self.eq_roi_line_grips.values(),
                     *self.fir_roi_line_grips.values()):
            grip.close()
        for marker in (*self.roi_markers.values(),
                       *self.eq_roi_markers.values(),
                       *self.fir_roi_markers.values()):
            marker.close()
        self.graph_mag.close();self.graph_phase.close()
        bounded_shutdown(self.pool)
        bounded_shutdown(self.plot_pool)
        self.drag_timer.stop()
        bounded_shutdown(self.axis_pool)
        bounded_shutdown(self.pan_pool)
        bounded_shutdown(self.mag_anchor_pool)
        bounded_shutdown(self.offset_pool)
        if self.host:self.host.close()
        event.accept()

def main(argv=None):
    """Production entrypoint shared by source QA and the native launcher."""
    if argv is None:
        argv = sys.argv[1:]
    # Packaging self-check performs no GUI, no Smaart, no audio I/O and must
    # remain runnable while the real overlay owns the singleton mutex.
    if "--package-selfcheck" in argv:
        from remix_duo_license_v874 import load_installed_license
        from remix_duo.licensing.online import configured as online_configured
        qa = bool(getattr(sys, "_remix_duo_qa_signed_build", False))
        status = load_installed_license().code if qa else (
            "ONLINE_CONFIGURED" if online_configured() else "ONLINE_NOT_CONFIGURED")
        print(f"REMIX_DUO_PACKAGE_SELF_CHECK QA={qa} STATUS={status}", flush=True)
        raise SystemExit(0 if (qa and status=="ACTIVE") or
                         (not qa and status=="ONLINE_CONFIGURED") else 22)
    from single_instance_v823 import acquire_instance
    _single_instance=acquire_instance()
    if _single_instance is None:
        print("V823_ALREADY_RUNNING: only one RemiX Duo may read Smaart Data Bar",flush=True)
        raise SystemExit(21)
    from duo_lifecycle_v8142 import mark_started
    mark_started()
    parser=argparse.ArgumentParser()
    parser.add_argument("--demo",action="store_true")
    parser.add_argument("--package-selfcheck",action="store_true",help=argparse.SUPPRESS)
    a=parser.parse_args(argv)
    app=QApplication(sys.argv)
    # V8.118: per-user log + GUI-stall stack dump (pythonw had no log).
    try:
        from gui_watchdog_v8118 import install as _install_watchdog
        _watchdog=_install_watchdog(app)
    except Exception as exc:  # diagnostics must never block startup
        print("V8118_WATCHDOG_DISABLED",exc,flush=True)
    if getattr(sys, "_remix_duo_qa_signed_build", False):
        app.setApplicationName("RemiX Duo QA V8.87")
    else:
        app.setApplicationName("RemiX Duo 8.180")
    # V8.74: product-scoped Ed25519 license gate, BEFORE any Smaart/GUI IO.
    # No demo bypass: all application entrypoints require a signed DUO_PRO key.
    # Cloudflare is mandatory for the commercial frozen EXE. Developer
    # source runs may continue using the existing, local QA license until
    # the real Cloudflare Worker/D1 issuer is deployed and key-pinned.
    if getattr(sys, "frozen", False) and not getattr(sys, "_remix_duo_qa_signed_build", False):
        from remix_duo.licensing.gate import activation_gate, load_installed_license
        license_state_reader=load_installed_license
    else:
        from remix_duo_license_v874 import activation_gate, load_installed_license
        license_state_reader=load_installed_license
    if not activation_gate():
        raise SystemExit(22)
    license_state=license_state_reader()
    if getattr(sys, "frozen", False) and not getattr(sys, "_remix_duo_qa_signed_build", False):
        from remix_duo.licensing.gate import license_display
    else:
        from remix_duo_license_v874 import license_display
    license_badge,license_tooltip=license_display(license_state)
    view=App(a.demo)
    from signal_tools_gui_v813 import ToolHub
    hub=ToolHub(view, license_badge, license_tooltip)
    return app.exec()

if __name__=="__main__":
    raise SystemExit(main())
