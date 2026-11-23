"""Non-invasive LF/HF ROI guides and draggable header handles for Smaart.

Two small, independently interactive Qt tool windows sit on the TOP EDGE of
the existing phase plot. All other regions remain click-through; original
Smaart drawing, audio, input devices, DSP, and generator are untouched.
"""
from __future__ import annotations

import math
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

F_MIN = 20.0
F_MAX = 20000.0
MIN_SEPARATION_OCT = 0.025  # Keep handles strictly ordered; about 1.75%.

def hz_to_x(hz, left, width, fmin=F_MIN, fmax=F_MAX):
    if width <= 0 or not (0 < fmin < fmax):
        raise ValueError("Invalid plot geometry")
    hz = max(fmin, min(fmax, float(hz)))
    return float(left) + math.log(hz / fmin) / math.log(fmax / fmin) * width

def x_to_hz(x, left, width, fmin=F_MIN, fmax=F_MAX):
    if width <= 0 or not (0 < fmin < fmax):
        raise ValueError("Invalid plot geometry")
    t = max(0.0, min(1.0, (float(x) - float(left)) / float(width)))
    return fmin * (fmax / fmin) ** t

def bound_drag(kind, value, lf, hf):
    value = max(F_MIN, min(F_MAX, float(value)))
    separation = 2 ** MIN_SEPARATION_OCT
    if kind == "LF":
        return max(F_MIN, min(value, hf / separation))
    if kind == "HF":
        return min(F_MAX, max(value, lf * separation))
    raise ValueError("Unknown ROI marker")


class ROIMarker(QWidget):
    """Small draggable tab, NOT a full-size mouse-intercepting overlay."""
    WIDTH = 84
    HEIGHT = 29

    def __init__(self, kind: str, drag_callback):
        super().__init__(None)
        if kind not in ("LF", "HF"):
            raise ValueError(kind)
        self.kind = kind
        self.drag_callback = drag_callback
        self.frequency = 60.0 if kind == "LF" else 200.0
        self.dragging = False
        self.color = QColor("#42eab6" if kind == "LF" else "#ffaf54")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setToolTip(f"Keo {kind} de chon vung Auto Align")
        self.hide()

    def set_frequency(self, hz):
        hz = float(hz)
        if self.frequency != hz:
            self.frequency = hz
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(self.color, 1.3))
        painter.setBrush(QColor(8, 18, 27, 225))
        painter.drawRoundedRect(QRectF(1, 1, self.WIDTH - 2, self.HEIGHT - 6), 5, 5)
        painter.setPen(self.color)
        painter.setFont(self.font())
        text = f"{self.kind} {self.frequency:.0f} Hz" if self.frequency < 1000 \
            else f"{self.kind} {self.frequency/1000:.2f}k"
        painter.drawText(QRectF(2, 1, self.WIDTH - 4, self.HEIGHT - 7),
                         Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(QPen(self.color, 2))
        mid = self.WIDTH / 2
        painter.drawLine(int(mid), self.HEIGHT - 7, int(mid), self.HEIGHT - 1)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.grabMouse()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # Global position, not local: moving the handle cannot shift origin.
            self.drag_callback(self.kind, float(event.globalPosition().x()))
            event.accept()
        else:
            if self.dragging:
                self.dragging = False
                self.releaseMouse()
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.drag_callback(self.kind, float(event.globalPosition().x()))
            self.dragging = False
            self.releaseMouse()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class ROILineGrip(QWidget):
    """Drag anywhere along the LF/HF dashed line, not only its top label.

    17px touch/hit strip follows the Phase plot and is absent over the
    header. A tiny nonzero alpha fill ensures hit-testing works on Win32
    layered windows without covering Smaart's native plot pixels.
    """
    WIDTH=17
    LABEL_MARGIN=ROIMarker.HEIGHT

    def __init__(self,kind:str,drag_callback):
        super().__init__(None)
        if kind not in ("LF","HF"):
            raise ValueError(kind)
        self.kind=kind
        self.drag_callback=drag_callback
        self.dragging=False
        self.hovered=False
        self.color=QColor("#42eab6" if kind=="LF" else "#ffaf54")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip(f"Keo duong {kind} o bat ky vi tri nao")
        self.resize(self.WIDTH,100)
        self.hide()

    def set_line_geometry(self,plot_rect,hz,label_margin=None,
                              fmin=F_MIN,fmax=F_MAX):
        left,top,width,height=plot_rect
        # Phase has a top LF/HF text handle; Mag uses the full plot height.
        margin=(self.LABEL_MARGIN if label_margin is None else int(label_margin))
        if width<=0 or height<=margin or margin<0:
            self.hide()
            return
        mid=round(hz_to_x(float(hz),left,width,fmin,fmax))
        y=top+margin
        h=height-margin
        rect=(int(mid-self.WIDTH//2),int(y),self.WIDTH,int(h))
        if self.geometry().getRect()!=rect:
            self.setGeometry(*rect)

    def paintEvent(self,event):
        painter=QPainter(self)
        # Small but NONZERO alpha makes the full narrow strip draggable
        # on Windows layered windows. Native plot remains visually intact.
        painter.fillRect(self.rect(),QColor(8,18,27,3))
        if self.hovered or self.dragging:
            painter.setPen(QPen(self.color,2,Qt.PenStyle.DashLine))
            painter.drawLine(self.WIDTH//2,0,self.WIDTH//2,self.height())
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
            self.dragging=True
            self.grabMouse()
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # Absolute global X is stable even as the line tool moves.
            self.drag_callback(self.kind,float(event.globalPosition().x()))
            event.accept()
            return
        if self.dragging:
            self.dragging=False
            self.releaseMouse()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.dragging:
            self.drag_callback(self.kind,float(event.globalPosition().x()))
            self.dragging=False
            self.releaseMouse()
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)
