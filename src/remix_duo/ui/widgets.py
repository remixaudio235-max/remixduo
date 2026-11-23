"""Shared plot, notices and style used by legacy Windows and portable UI."""
import math
import numpy as np
from PyQt6.QtCore import Qt,QTimer,QPoint
from PyQt6.QtGui import QPainter,QColor,QPen,QPainterPath
from PyQt6.QtWidgets import QWidget,QLabel,QGraphicsDropShadowEffect

_TOAST_TONES={
    'info':('#0D1D2A','#DDF6FF','#365D72','#65DAFF'),
    'busy':('#0C2029','#E1FBFF','#347484','#59E5F2'),
    'success':('#10251F','#E7FFF3','#34745D','#67F2A7'),
    'warning':('#2A2115','#FFF6E7','#80623A','#FFB85C'),
    'error':('#2B171D','#FFF0F3','#824454','#FF7185'),
}

def _toast_tone(message):
    text=str(message).casefold()
    if any(key in text for key in ('lỗi','thất bại','không đọc được','error')):
        return 'error'
    if any(key in text for key in ('cảnh báo','chưa ','cần đúng','hold','không tạo được')):
        return 'warning'
    if any(key in text for key in ('thành công','đã tạo','hoàn tất',' pass')):
        return 'success'
    if text.startswith('đang ') or 'vui lòng đợi' in text:
        return 'busy'
    return 'info'

def show_notice(owner, message):
    """Readable in-window toast; keep the detailed status visible separately."""
    label=getattr(owner, '_remix_notice', None)
    if label is None:
        label=QLabel(owner)
        label.setObjectName('remixToast')
        label.setWordWrap(True)
        label.setAccessibleName('Thông báo RemiX Duo')
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        shadow=QGraphicsDropShadowEffect(label)
        shadow.setBlurRadius(24)
        shadow.setOffset(0,4)
        shadow.setColor(QColor(0,0,0,145))
        label.setGraphicsEffect(shadow)
        owner._remix_notice=label
        timer=QTimer(owner)
        timer.setSingleShot(True)
        timer.timeout.connect(label.hide)
        owner._remix_notice_timer=timer
    full_message=str(message)
    tone=_toast_tone(full_message)
    surface,text,border,accent=_TOAST_TONES[tone]
    label.setProperty('toastTone',tone)
    label.setAccessibleDescription('Toast '+tone)
    label.setStyleSheet(
        'QLabel#remixToast {'
        f'background-color:{surface};color:{text};'
        f'border:1px solid {border};border-left:4px solid {accent};'
        'border-radius:10px;padding:9px 12px;'
        'font:600 12px "Segoe UI";}'
    )
    label.setToolTip(full_message)
    compact=owner.width()<300
    limit=90 if compact else 180
    label.setText(full_message if len(full_message)<=limit else full_message[:limit-1]+'…')
    # V8.138: a plot can be 1400+ px wide. A full-width toast obscures the
    # measurement and, when duplicated in the dock, also covers tool controls.
    # Keep plot notices compact; narrow dialog notices retain their width.
    available=max(100,owner.width()-24)
    cap=min(520 if owner.width()>=600 else 420,available)
    if tone=='busy':
        cap=min(cap,280)
    natural=label.fontMetrics().horizontalAdvance(label.text())+40
    minimum=min(cap,220 if owner.width()>=300 else 100)
    notice_width=min(cap,max(minimum,natural))
    label.setFixedWidth(notice_width)
    label.adjustSize()
    # V8.124: a page inside a scrolling dock is taller than what is shown;
    # anchor the toast to the VISIBLE part, never below the dock bottom.
    visible=owner.visibleRegion().boundingRect()
    if visible.isEmpty():
        visible=owner.rect()
    label.setMaximumHeight(min(84 if owner.width()>=600 else 104,
                               max(60,visible.height()//3)))
    x=max(12,visible.right()-label.width()-12)
    label.move(x,max(visible.top()+8,
                     min(visible.bottom()-label.height()-12,
                         owner.height()-label.height()-16)))
    label.show()
    label.raise_()
    owner._remix_notice_timer.start(5000)

def show_plot_notice(anchor,message):
    """Show a non-activating top-level Toast anchored over a plot.

    Native preview widgets can be hidden while Smaart still shows its plot.
    A child Toast would then fall back into and cover the compact tool panel;
    the independent Tool surface keeps controls clear in both states.
    """
    show_notice(anchor,message)
    label=anchor._remix_notice
    if not label.isWindow():
        label.setParent(None,Qt.WindowType.Tool |
                       Qt.WindowType.FramelessWindowHint |
                       Qt.WindowType.WindowStaysOnTopHint |
                       Qt.WindowType.WindowDoesNotAcceptFocus)
        label.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        anchor.destroyed.connect(label.deleteLater)
    origin=anchor.mapToGlobal(QPoint(0,0))
    x=origin.x()+max(12,anchor.width()-label.width()-16)
    y=origin.y()+max(12,anchor.height()-label.height()-16)
    label.move(x,y)
    label.show()
    label.raise_()


STYLE="""
QWidget {background:#08121B;color:#E6F4F8;font:11px 'Segoe UI';}
QFrame#card {background:#112231;border:1px solid #28495E;border-radius:8px;}
QLabel#title {color:#5BE6F3;font:bold 15px 'Segoe UI';}
QLabel#hint {color:#94B6C5;font:10px 'Segoe UI';}
QLabel#score {color:#A4FFCB;font:bold 12px 'Segoe UI';}
QPushButton {background:#1E3C51;color:#EDF8FF;border:1px solid #34647B;
 border-radius:6px;min-height:29px;font:bold 11px 'Segoe UI';}
QPushButton:hover {background:#295D74;}
QPushButton#run {background:#FF952A;border:0;color:#111721;}
QComboBox,QDoubleSpinBox,QSpinBox {background:#152E40;color:#F4FBFF;
 border:1px solid #315B72;border-radius:5px;min-height:27px;}
QTextEdit {background:#07131B;color:#C9ECF0;border:1px solid #284559;
 border-radius:6px;font:10px 'Consolas';}
"""


class MiniPlot(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(130)
        self.freq=None
        self.before=None
        self.after=None
        self.working_range=None
        self.setToolTip("Cyan: trước xử lý | Green: sau xử lý (mô phỏng TF)")
    def set_working_range(self,lf,hf):
        self.working_range=(lf,hf)
        self.update()
    def set_curves(self,freq,before,after):
        self.freq=np.asarray(freq,float).copy()
        self.before=np.asarray(before,float).copy()
        self.after=np.asarray(after,float).copy()
        self.update()
    def clear(self):
        self.freq=self.before=self.after=None
        self.working_range=None
        self.update()
    def paintEvent(self,event):
        p=QPainter(self)
        p.fillRect(self.rect(),QColor("#050C14"))
        w,h=self.width(),self.height()
        p.setPen(QPen(QColor("#253C4C"),1))
        for yy in (.25,.5,.75):
            p.drawLine(0,int(h*yy),w,int(h*yy))
        if self.working_range is not None:
            lo,hi=self.working_range
            xmin=lambda v: int((math.log10(v)-math.log10(20))/3*(w-2))
            x1,x2=xmin(lo),xmin(hi)
            p.fillRect(max(0,x1),0,max(0,min(w,x2)-max(0,x1)),h,QColor(9,165,199,36))
            p.setPen(QPen(QColor("#28DCEB"),1,Qt.PenStyle.DashLine))
            p.drawLine(x1,0,x1,h-1)
            p.drawLine(x2,0,x2,h-1)
        if self.freq is None or len(self.freq)<2:return
        mask=(np.isfinite(self.freq)&(self.freq>0)&
              np.isfinite(self.before)&np.isfinite(self.after))
        if mask.sum()<3:return
        f=self.freq[mask]; b=self.before[mask]; a=self.after[mask]
        valid=(f>=20)&(f<=20000)
        if valid.sum()<3:return
        f=f[valid];b=b[valid];a=a[valid]
        ylo=float(min(np.percentile(b,5),np.percentile(a,5)))-3
        yhi=float(max(np.percentile(b,95),np.percentile(a,95)))+3
        if yhi-ylo<6:yhi=ylo+6
        x=((np.log10(f)-np.log10(20))/(np.log10(20000)-np.log10(20)))*(w-2)
        for data,color in ((b,"#49C8EB"),(a,"#64FEA0")):
            ys=np.clip((yhi-data)/(yhi-ylo)*h,-1e5,1e5)
            path=QPainterPath()
            path.moveTo(float(x[0]),float(ys[0]))
            for xx,yy in zip(x[1:],ys[1:]):
                path.lineTo(float(xx),float(yy))
            p.setPen(QPen(QColor(color),1.6))
            p.setClipRect(self.rect())
            p.drawPath(path)
        p.setClipping(False)
        p.setPen(QColor("#88A7B2"))
        p.drawText(6,h-5,"20Hz")
        p.drawText(max(4,w-43),h-5,"20k")

