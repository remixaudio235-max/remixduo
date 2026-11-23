"""V8.19: full-height interactive LF/HF dashed-line hit targets.

The old header ROIMarkers remain untouched. Their dotted guides live on
a click-through SumGraph, so add two narrow 17px-wide Qt Tool windows over
each plotted line (excluding the top label). Only the lines intercept mouse
input; every other graph pixel remains click-through to Smaart.
"""
from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_19_FULL_HEIGHT_ROI_DRAG_QA")
p=root/"roi_markers_v73.py"
s=p.read_text(encoding="utf-8")
assert "class ROILineGrip" not in s
s+='''
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

    def set_line_geometry(self,plot_rect,hz):
        left,top,width,height=plot_rect
        if width<=0 or height<=self.LABEL_MARGIN:
            self.hide()
            return
        mid=round(hz_to_x(float(hz),left,width))
        y=top+self.LABEL_MARGIN
        h=height-self.LABEL_MARGIN
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
        if self.dragging:
            # Absolute global X is stable even as the line tool moves.
            self.drag_callback(self.kind,float(event.globalPosition().x()))
            event.accept()
            return
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
'''
p.write_text(s,encoding="utf-8")

p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
needle="from roi_markers_v73 import ROIMarker, hz_to_x, x_to_hz, bound_drag"
assert s.count(needle)==1
s=s.replace(needle,
    "from roi_markers_v73 import ROIMarker, ROILineGrip, hz_to_x, x_to_hz, bound_drag")
needle='''        self.roi_markers={name:ROIMarker(name,self.on_roi_drag)
                          for name in ("LF","HF")}'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        self.roi_line_grips={name:ROILineGrip(name,self.on_roi_drag)
                             for name in ("LF","HF")}''')
needle='''            if marker.pos().x()!=px or marker.pos().y()!=py:
                marker.move(px,py)'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        # Each narrow interactive strip covers the dashed line from
        # below the label to the bottom of the Phase plot. Reanchor on
        # ROI frequency, Smaart move/resize and Mag/Phase plot swap.
        for name,grip in self.roi_line_grips.items():
            hz=self.lf.value() if name=="LF" else self.hf.value()
            grip.set_line_geometry(self.plot_layout.phase,hz)''')
needle='''        for marker in self.roi_markers.values():
            marker.setVisible(bool(has))

    def closeEvent(self,event):'''
assert s.count(needle)==1
s=s.replace(needle,'''        for marker in self.roi_markers.values():
            marker.setVisible(bool(has))
        for grip in self.roi_line_grips.values():
            grip.setVisible(bool(has))

    def closeEvent(self,event):''')
needle='''    def closeEvent(self,event):
        for marker in self.roi_markers.values():
            marker.close()'''
assert s.count(needle)==1
s=s.replace(needle,'''    def closeEvent(self,event):
        for grip in self.roi_line_grips.values():
            grip.close()
        for marker in self.roi_markers.values():
            marker.close()''')
s=s.replace("V8.18","V8.19")
p.write_text(s,encoding="utf-8")
print("V819_FULL_LINE_MOUSE_HIT_STRIPS_PATCHED")
