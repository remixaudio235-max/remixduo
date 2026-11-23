# -*- coding: utf-8 -*-
"""RemiX Duo Auto EQ - read-only preview table, TXT and PNG exports.

Source of truth is the exact PREVIEW_READY RemiX AEQ-U1.2 result.
Never writes .trf, Smaart, audio generator, DSP or any hardware state.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
from PyQt6.QtCore import Qt,QRectF,QEvent
from PyQt6.QtGui import QFont,QColor,QImage,QPainter,QPen,QPixmap
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QFrame,
                             QTableWidget,QTableWidgetItem,QHeaderView,
                             QPushButton,QFileDialog,QMessageBox)

@dataclass(frozen=True)
class EQRow:
    number:int
    hz:float
    db:float
    q:float

@dataclass(frozen=True)
class EQExportSnapshot:
    source:str
    target:str
    fs:int
    before_wrms:float
    after_wrms:float
    rows:tuple[EQRow,...]
    status:str="PREVIEW_READY"

    @classmethod
    def from_result(cls,result,target):
        if result is None or getattr(result,"status",None)!="PREVIEW_READY":
            raise ValueError("Không có kết quả Auto EQ đã nghiệm thu để xuất")
        bands=tuple(getattr(result,"peqs",()))
        if not (1<=len(bands)<=12):
            raise ValueError("Bảng EQ cần từ 1 đến 12 bộ lọc PEQ")
        if not isinstance(target,str) or not target:
            raise ValueError("Target không hợp lệ")
        source=str(getattr(result,"source","")).strip()
        fs=getattr(result,"fs",None)
        before=float(getattr(result,"rms_before",float("nan")))
        after=float(getattr(result,"rms_after",float("nan")))
        if not source or type(fs) is not int or fs<=0 or not all(
            math.isfinite(x) for x in (before,after)):
            raise ValueError("Nguồn, Fs hoặc WRMS không hợp lệ")
        rows=[]
        for i,b in enumerate(bands,1):
            f=float(b.freq_hz);g=float(b.gain_db);q=float(b.q)
            if not all(map(math.isfinite,(f,g,q))) or not (
                   20<=f<fs/2 and -12<=g<=6 and .3<=q<=16):
                raise ValueError("PEQ không hợp lệ hoặc vượt giới hạn an toàn")
            rows.append(EQRow(i,f,g,q))
        return cls(source,target,fs,before,after,tuple(rows))

    def as_text(self):
        lines=[
            "# RemiX Duo - BANG EQ (PREVIEW ONLY)",
            f"# Trace: {self.source}",
            f"# Target: {self.target}",
            f"# Fs: {self.fs} Hz",
            f"# RemiX AEQ-U1.2 | WRMS: {self.before_wrms:.3f} -> {self.after_wrms:.3f} dB",
            "# KHONG GHI DSP / KHONG THAY DOI TRACE SMAART",
            "EQ#,Hz,dB,Q",
        ]
        lines.extend(f"{r.number},{r.hz:.1f},{r.db:+.2f},{r.q:.2f}" for r in self.rows)
        return "\n".join(lines)+"\n"

    def save_txt(self,path):
        p=Path(path)
        if p.suffix.lower()!=".txt":
            raise ValueError("File xuất cần phần mở rộng .txt")
        # Only explicitly chosen output file. Never modify source trace.
        p.write_text(self.as_text(),encoding="utf-8",newline="\n")
        return p

    def to_image(self):
        """Generate a legible PNG with installed system glyphs.

        Qt's offscreen Windows backend can substitute missing fonts with
        tofu glyphs. Pillow rasterizes system Arial directly, independently
        of Qt platform plugin and the desktop session.
        """
        from io import BytesIO
        from PIL import Image,ImageDraw,ImageFont
        width,height=775,750
        img=Image.new("RGB",(width,height),(8,15,25))
        draw=ImageDraw.Draw(img)
        path=Path("C:/Windows/Fonts")
        regular=path/"arial.ttf"
        bold=path/"arialbd.ttf"
        if not regular.is_file() or not bold.is_file():
            raise OSError("Không thấy font Windows Arial để xuất bảng EQ")
        headline=ImageFont.truetype(str(bold),30)
        meta=ImageFont.truetype(str(regular),19)
        column=ImageFont.truetype(str(bold),18)
        value=ImageFont.truetype(str(regular),18)
        footer=ImageFont.truetype(str(regular),16)
        draw.text((30,22),"RemiX Duo  |  AUTO EQ",fill=(126,243,251),font=headline)
        draw.text((30,77),f"Trace gốc: {self.source[:55]}",fill=(219,231,241),font=meta)
        draw.text((30,107),
                  f"Target: {self.target}    Fs: {self.fs:,} Hz    PEQ: {len(self.rows)}",
                  fill=(219,231,241),font=meta)
        draw.text((30,138),
                  f"WRMS: {self.before_wrms:.2f}  ->  {self.after_wrms:.2f} dB",
                  fill=(163,255,197),font=meta)
        left=30;top=176;rowh=39;cols=(115,225,195,180)
        x_offsets=[left]
        for w in cols[:-1]:x_offsets.append(x_offsets[-1]+w)
        for row in range(13):
            y=top+row*rowh
            color=(27,71,94) if row==0 else ((12,37,53) if row%2 else (15,43,57))
            draw.rectangle((left,y,left+sum(cols),y+rowh),fill=color)
            draw.line((left,y+rowh,left+sum(cols),y+rowh),fill=(41,85,107),width=1)
            if row==0:
                texts=("EQ#","Hz","dB","Q")
                fg=(167,243,255);font=column
            elif row<=len(self.rows):
                band=self.rows[row-1]
                texts=(f"EQ{band.number}",f"{band.hz:.1f}",
                       f"{band.db:+.2f}",f"{band.q:.2f}")
                fg=(244,250,255);font=value
            else:
                texts=("-","-","-","-")
                fg=(104,137,157);font=value
            for i,string in enumerate(texts):
                draw.text((x_offsets[i]+12,y+9),string,fill=fg,font=font)
        draw.text((30,699),
              "MagEq: mô phỏng sau EQ | Trace gốc Smaart không đổi",
              fill=(171,212,225),font=footer)
        draw.text((30,726),
              "CHƯA ÁP DỤNG EQ VÀO SMAART / DSP",
              fill=(255,205,143),font=footer)
        data=BytesIO()
        img.save(data,format="PNG")
        return QImage.fromData(data.getvalue(),"PNG")

    def save_png(self,path):
        p=Path(path)
        if p.suffix.lower()!=".png":
            raise ValueError("File xuất cần phần mở rộng .png")
        if not self.to_image().save(str(p),"PNG"):
            raise OSError("Không xuất được PNG")
        return p

class EQExportDialog(QDialog):
    """Review the exact 12x4 preview, with separate explicit save actions."""
    def __init__(self,snapshot:EQExportSnapshot,parent=None):
        super().__init__(parent)
        self.snapshot=snapshot
        self.setWindowTitle("RemiX Duo | Auto EQ")
        # Native white Windows title bar removed; entire title is a real Qt
        # drag surface with a visible, clickable close button.
        self.setWindowFlags(Qt.WindowType.Dialog |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(570,710)
        self.resize(610,775)
        self._drag_pos=None
        self.setStyleSheet("""
            QFrame#dialogShell {background:#091721;border:1px solid #315368;
                border-radius:14px;}
            QFrame#titleBar {background:#132C3A;border:0;
                border-top-left-radius:13px;border-top-right-radius:13px;}
            QLabel#brandLabel {font:800 13px 'Segoe UI';color:#F4FBFF;}
            QLabel#eyebrow {font:700 10px 'Segoe UI';color:#67DCEF;}
            QLabel#heading {font:800 21px 'Segoe UI';color:#F4FDFF;}
            QFrame#summaryCard {background:#102838;border:1px solid #305569;
                border-radius:9px;}
            QLabel#meta {color:#BED9E5;font:11px 'Segoe UI';}
            QLabel#metrics {color:#85E8DA;font:700 11px 'Segoe UI';}
            QLabel#disclaimer {color:#9BBCCB;font:10px 'Segoe UI';}
            QTableWidget {background:#0D2130;alternate-background-color:#122E40;
                border:1px solid #305365;border-radius:8px;
                color:#F2FAFF;gridline-color:#254357;
                selection-background-color:#19546D;font:600 12px 'Consolas';}
            QHeaderView::section {background:#1E465A;color:#D5F6FF;
                padding:8px;border:0;border-bottom:1px solid #4B8295;
                font:800 11px 'Segoe UI';}
            QPushButton {background:#17384B;color:#E6F8FF;padding:7px 10px;
                border:1px solid #456C7E;border-radius:8px;
                font:700 11px 'Segoe UI';min-height:28px;}
            QPushButton:hover {background:#28566C;border-color:#77CBDB;}
            QPushButton#save {background:#62DFF2;color:#071C26;
                border:1px solid #A4F8FF;font:800 11px 'Segoe UI';}
            QPushButton#save:hover {background:#B1F5FE;}
            QPushButton#closeTitle {border:0;background:transparent;
                color:#BDD6E0;min-height:18px;max-height:25px;
                min-width:30px;max-width:30px;font:700 17px 'Segoe UI';}
            QPushButton#closeTitle:hover {background:#7A3043;color:white;}
        """)
        outer=QVBoxLayout(self)
        outer.setContentsMargins(7,7,7,7)
        shell=QFrame(self);shell.setObjectName("dialogShell")
        outer.addWidget(shell)
        shell_layout=QVBoxLayout(shell)
        shell_layout.setContentsMargins(0,0,0,0)
        shell_layout.setSpacing(0)
        self.titlebar=QFrame(shell);self.titlebar.setObjectName("titleBar")
        self.titlebar.setFixedHeight(45)
        self.titlebar.installEventFilter(self)
        title_row=QHBoxLayout(self.titlebar)
        title_row.setContentsMargins(15,5,10,5)
        title_row.setSpacing(8)
        icon=QLabel(self.titlebar)
        logo=QPixmap(str(Path(__file__).resolve().parent/"remix_dou_swirl_toolbar32.png"))
        icon.setFixedSize(24,24)
        if not logo.isNull():
            icon.setPixmap(logo.scaled(24,24,Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
        self.brand_label=QLabel("RemiX Duo",self.titlebar)
        self.brand_label.setObjectName("brandLabel")
        title_row.addWidget(icon)
        title_row.addWidget(self.brand_label)
        title_row.addStretch(1)
        context=QLabel("AUTO EQ  /  KẾT QUẢ",self.titlebar)
        context.setObjectName("eyebrow")
        title_row.addWidget(context)
        self.title_close=QPushButton("×",self.titlebar)
        self.title_close.setObjectName("closeTitle")
        self.title_close.setToolTip("Đóng bảng EQ")
        self.title_close.clicked.connect(self.close)
        title_row.addWidget(self.title_close)
        shell_layout.addWidget(self.titlebar)
        body=QVBoxLayout()
        body.setContentsMargins(17,15,17,15)
        body.setSpacing(10)
        shell_layout.addLayout(body)
        eyebrow=QLabel("KẾT QUẢ PHÂN TÍCH / AUTO EQ")
        eyebrow.setObjectName("eyebrow")
        body.addWidget(eyebrow)
        self.heading=QLabel("BẢNG EQ VỪA TẠO")
        self.heading.setObjectName("heading")
        body.addWidget(self.heading)
        summary=QFrame(shell);summary.setObjectName("summaryCard")
        sums=QVBoxLayout(summary);sums.setContentsMargins(12,10,12,10)
        sums.setSpacing(5)
        meta=QLabel(f"TRACE  {snapshot.source}    •    TARGET  {snapshot.target}")
        meta.setObjectName("meta");meta.setWordWrap(True)
        sums.addWidget(meta)
        self.metrics=QLabel(
            f"Fs {snapshot.fs:,} Hz   |   {len(snapshot.rows)} PEQ"
            f"   |   WRMS {snapshot.before_wrms:.2f} → {snapshot.after_wrms:.2f} dB")
        self.metrics.setObjectName("metrics")
        self.metrics.setWordWrap(True)
        sums.addWidget(self.metrics)
        body.addWidget(summary)
        self.table=QTableWidget(12,4,self)
        self.table.setHorizontalHeaderLabels(("EQ#","Hz","dB","Q"))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        for i in range(12):
            values=(f"EQ{i+1}","—","—","—")
            if i<len(snapshot.rows):
                b=snapshot.rows[i]
                values=(f"EQ{b.number}",f"{b.hz:.1f}",f"{b.db:+.2f}",f"{b.q:.2f}")
            for j,val in enumerate(values):
                item=QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i,j,item)
            self.table.setRowHeight(i,35)
        body.addWidget(self.table,1)
        note=QLabel("PREVIEW ONLY  •  Không ghi DSP, không thay đổi Trace Smaart.")
        note.setObjectName("disclaimer");note.setWordWrap(True)
        body.addWidget(note)
        bar=QHBoxLayout();bar.setSpacing(9)
        self.txt_button=QPushButton("Lưu TXT")
        self.png_button=QPushButton("Lưu PNG")
        self.png_button.setObjectName("save")
        close=QPushButton("Đóng")
        self.txt_button.clicked.connect(self.choose_txt)
        self.png_button.clicked.connect(self.choose_png)
        close.clicked.connect(self.close)
        for button in (self.txt_button,self.png_button,close):
            bar.addWidget(button,1)
        body.addLayout(bar)

    def eventFilter(self,obj,event):
        if obj is getattr(self,"titlebar",None):
            if event.type()==QEvent.Type.MouseButtonPress and (
                    event.button()==Qt.MouseButton.LeftButton):
                self._drag_pos=event.globalPosition().toPoint()-self.frameGeometry().topLeft()
                return True
            if event.type()==QEvent.Type.MouseMove and self._drag_pos is not None:
                self.move(event.globalPosition().toPoint()-self._drag_pos)
                return True
            if event.type()==QEvent.Type.MouseButtonRelease:
                self._drag_pos=None
                return True
        return super().eventFilter(obj,event)

    def choose_txt(self):
        path,_=QFileDialog.getSaveFileName(self,"Xuất bảng EQ",
            "RemiX_Duo_MagEq.txt","TXT (*.txt)",
            options=QFileDialog.Option.DontUseNativeDialog)
        if path:
            try:self.snapshot.save_txt(Path(path).with_suffix(".txt"))
            except Exception as exc:QMessageBox.warning(self,"Xuất EQ",str(exc))

    def choose_png(self):
        path,_=QFileDialog.getSaveFileName(self,"Xuất ảnh bảng EQ",
            "RemiX_Duo_MagEq.png","PNG (*.png)",
            options=QFileDialog.Option.DontUseNativeDialog)
        if path:
            try:self.snapshot.save_png(Path(path).with_suffix(".png"))
            except Exception as exc:QMessageBox.warning(self,"Xuất EQ",str(exc))
