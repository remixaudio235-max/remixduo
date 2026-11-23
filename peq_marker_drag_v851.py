"""V8.51 — edit PEQ by dragging a small independent native-plot grip.

The rest of the existing Mag overlay remains entirely click-through.
Frequency: absolute pointer X on logarithmic Smaart axis.
Gain: vertical pointer displacement / verified native px-per-dB.
Q is preserved. One-quarter-octave and ROI limits ALWAYS apply.
No Smaart/ASIO/DSP/measurement writes.
"""
from __future__ import annotations
from dataclasses import replace
from math import log2, isfinite
import numpy as np
from PyQt6.QtCore import Qt,QRectF
from PyQt6.QtGui import QColor,QPainter,QPen
from PyQt6.QtWidgets import QWidget
from engines.remix_autoeq_unified import AutoEQBand,cascade_biquads
from remix_autoeq_v05_adapter import PEQ
from autoeq_spacing_v850 import close_pairs,MIN_SPACING_OCT

WIDTH,HEIGHT=30,22


def bounded_marker_change(peqs,index,global_x,global_y,plot,
                          press_y,press_gain,px_per_db,lf,hf,cut,boost):
    """Pure, deterministic absolute-X/delta-Y transform.

    Reject infeasible frequency intervals rather than silently overlapping
    adjacent filters or leaving the EQ ROI. Return updated PEQ tuple.
    """
    if not peqs or index<0 or index>=len(peqs):
        raise ValueError("Invalid marker")
    left,top,width,height=map(float,plot)
    if width<100 or height<80 or px_per_db<=1 or not isfinite(px_per_db):
        raise ValueError("Native Mag scale unknown")
    from roi_markers_v73 import x_to_hz
    original=peqs[index]
    others=tuple((i,b) for i,b in enumerate(peqs) if i!=index)
    ratio=2**MIN_SPACING_OCT
    low=max(float(lf),20.)
    high=min(float(hf),20000.)
    for _,b in others:
        f=float(b.freq_hz)
        if f<original.freq_hz:low=max(low,f*ratio)
        else:high=min(high,f/ratio)
    if low>high+1e-6:
        raise ValueError("No nonoverlapping location within current ROI")
    f=x_to_hz(global_x,left,width,20.,20000.)
    f=max(low,min(high,f))
    # Quantize only to display resolution; do NOT round so coarsely that
    # it breaks the safety bound at 1/4 octave.
    g=float(press_gain)+(float(press_y)-float(global_y))/float(px_per_db)
    g=max(float(cut),min(float(boost),g))
    g=round(g,2)
    new=tuple(replace(b,freq_hz=f,gain_db=g) if i==index
              else b for i,b in enumerate(peqs))
    if close_pairs(new,MIN_SPACING_OCT):
        raise ValueError("PEQ spacing violation")
    if not all(float(lf)-1e-7<=float(b.freq_hz)<=float(hf)+1e-7 and
               cut-1e-7<=float(b.gain_db)<=boost+1e-7 and
               .3<=float(b.q)<=16 for b in new):
        # Other existing bands may be outside ROI due to an independent
        # later ROI edit: not legal to start a manual edit in that case.
        raise ValueError("PEQ outside current tuning limits")
    return new


def preview_after_drag(base_result,peqs,weights):
    """Exact 48k/selected-Fs biquad cascade, not a graphics-only transform."""
    if base_result.status!="PREVIEW_READY" or not peqs:
        raise ValueError("Cannot edit an unapproved EQ preview")
    bands=tuple(AutoEQBand("P",float(b.freq_hz),float(b.gain_db),float(b.q))
                for b in peqs)
    response=cascade_biquads(base_result.hz,bands,int(base_result.fs))
    gain=20*np.log10(np.maximum(np.abs(response),1e-15))
    after=base_result.before_db+gain
    w=np.asarray(weights,float)
    if w.shape!=after.shape or not np.isfinite(w).all() or float(w.sum())<=0:
        raise ValueError("Invalid EQ scoring weights")
    rms=float(np.sqrt(np.average((after-base_result.target_db)**2,weights=w)))
    if not np.isfinite(after).all():
        raise ValueError("Nonfinite edited EQ")
    return replace(base_result,peqs=tuple(peqs),after_db=after,rms_after=rms,
                   warnings=tuple(base_result.warnings)+
                   ("MANUAL_PEQ_DRAG: preview only, no DSP write",))


class PEQMarkerGrip(QWidget):
    """Only a tiny 30x22 marker accepts mouse; entire graph is click-through."""
    def __init__(self,number,callback):
        super().__init__(None)
        self.number=int(number)  # 1-based marker label
        self.callback=callback
        self.dragging=False
        self.hovered=False
        self.setFixedSize(WIDTH,HEIGHT)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("PEQ: trai/phai = Hz; len/xuong = Gain; Q giu nguyen")
        self.hide()

    def paintEvent(self,event):
        painter=QPainter(self)
        # Non-zero alpha ensures Win32 layered window remains mouse-hit-able.
        painter.fillRect(self.rect(),QColor(255,195,100,3))
        if self.hovered or self.dragging:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#FFE69A"),1.2))
            painter.drawRoundedRect(QRectF(.5,.5,WIDTH-1,HEIGHT-1),4,4)
        painter.end()

    def enterEvent(self,event):
        self.hovered=True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self,event):
        self.hovered=False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            pos=event.globalPosition()
            try:allowed=bool(self.callback(self.number,
                float(pos.x()),float(pos.y()),"start"))
            except (ValueError,RuntimeError,AttributeError):allowed=False
            if allowed:
                self.dragging=True
                self.grabMouse()
                self.update()
                event.accept()
                return
        event.ignore()

    def mouseMoveEvent(self,event):
        if self.dragging:
            pos=event.globalPosition()
            self.callback(self.number,float(pos.x()),float(pos.y()),"move")
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self,event):
        if self.dragging and event.button()==Qt.MouseButton.LeftButton:
            pos=event.globalPosition()
            try:self.callback(self.number,float(pos.x()),float(pos.y()),"end")
            finally:
                self.dragging=False
                self.releaseMouse()
                self.update()
            event.accept()
        else:event.ignore()

    def cancel(self):
        if self.dragging:
            self.dragging=False
            self.releaseMouse()
        self.hide()
