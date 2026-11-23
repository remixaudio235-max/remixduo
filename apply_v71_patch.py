from pathlib import Path
import textwrap

base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_1_QA')
p=base/'selection_v7.py'
s=p.read_text(encoding='utf-8')
a=s.index('def archive_order(')
b=s.index('\ndef scan_icon_white_cross(',a)
s=s[:a]+'''def archive_order(folder:Path)->list[Path]:
    """Read canonical Smaart index.xml row IDs, fail closed if inconsistent.

    Unlike mtime order, adhocIndex preserves explicit Smaart Data Library IDs.
    Validate every stored TRF identity and require contiguous 0-based indices.
    """
    from xml.etree import ElementTree as ET
    folder=Path(folder)
    all_files={p.name.casefold():p for p in folder.glob("*.trf")}
    index=folder.parent/"index.xml"
    if not index.is_file():
        raise ValueError("Smaart index.xml missing; row-to-Trace mapping unverified")
    try:
        root=ET.parse(index).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Smaart index.xml parse failed: {exc}") from exc
    ids={}
    for element in root.findall(".//path"):
        name=str(element.text or "").strip()
        if not name.lower().endswith(".trf"):
            continue
        key=Path(name).name.casefold()
        if key not in all_files:
            raise ValueError(f"Smaart index references missing TRF: {name}")
        try:
            ix=int(element.attrib["adhocIndex"])
        except (ValueError,KeyError) as exc:
            raise ValueError("Smaart index has invalid row ID") from exc
        if ix in ids or any(path==all_files[key] for path in ids.values()):
            raise ValueError("Duplicate row/Trace in Smaart index")
        ids[ix]=all_files[key]
    if sorted(ids)!=list(range(len(all_files))) or len(ids)!=len(all_files):
        raise ValueError(f"Smaart row IDs incomplete/stale ({len(ids)}/{len(all_files)})")
    return [ids[i] for i in range(len(all_files))]
''' + s[b:]
p.write_text(s,encoding='utf-8')

p=base/'full_scan_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('    # Normalize 1-based UIA row numbers to 0-based when needed.\n    if m and 0 not in m and 1 in m and len(m)>=2:\n        m={k-1:v for k,v in m.items()}\n    return root,bar,m',
'''    # Never guess a -1 shift. Accept only a complete zero- or one-based sequence.
    labels=sorted(m)
    if labels==list(range(len(m))):
        pass
    elif labels==list(range(1,len(m)+1)):
        m={k-1:v for k,v in m.items()}
    else:
        raise ScanError(f"UIA row indices are not contiguous: {labels[:5]}")
    return root,bar,m''')
a=s.index('def _page(')
b=s.index('\ndef full_scan(',a)
s=s[:a]+'''def _page(img,order,scroll,first_y,top,bottom,icon_left,
          row_height=22,*,uia_rows=None,window_origin=(0,0)):
    """Classify each trace using its *own* native UIA rectangle (not inferred rows)."""
    found={}
    if uia_rows is not None:
        for i,item in uia_rows.items():
            if not 0<=i<len(order): continue
            try:
                rect=item.rectangle()
                rowy=rect.top-window_origin[1]
                x=rect.left-window_origin[0]+7
            except Exception:
                continue
            if rowy < top-0.5 or rowy+18 > bottom+0.5: continue
            icon=scan_icon_white_cross(img,(x,rowy+3,x+15,rowy+18))
            if icon != "unknown": found[i]=icon
        return found
    for i,_ in enumerate(order):
        rowy=first_y+i*row_height-scroll
        if rowy<top-0.5 or rowy+18>bottom+0.5:continue
        icon=scan_icon_white_cross(img,(icon_left,rowy+3,icon_left+15,rowy+18))
        if icon!="unknown":found[i]=icon
    return found
''' + s[b:]
s=s.replace('page=_page(img,order,pos,first_y,top,bottom,icon_left,row_height)',
            'page=_page(img,order,pos,first_y,top,bottom,icon_left,row_height,\\n                       uia_rows=rows,window_origin=(l,t))')
p.write_text(s,encoding='utf-8')

p=base/'live_sync_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('        self.order=[]\n', '        self.order=[]\n        self.uia_rows={}\n')
s=s.replace('        self.order=order\n        self.states=dict(enumerate(scan.states))',
            '        self.order=order\n        self.uia_rows=rows\n        self.states=dict(enumerate(scan.states))')
s=s.replace('            rows=_page(image,self.order,offset1,anchor,top,bottom,left)',
            '            rows=_page(image,self.order,offset1,anchor,top,bottom,left,\\n                       uia_rows=self.uia_rows,window_origin=(rect[0],rect[1]))')
p.write_text(s,encoding='utf-8')

p=base/'smaart_axes_v71.py'
p.write_text('''"""Read *saved* Smaart plot axes without modifying Smaart's configuration."""
from pathlib import Path
from xml.etree import ElementTree as ET
import math

def read_saved_axes(path=None):
    path=Path(path or Path.home()/"Documents/Smaart Suite/Config/SmaartConfig.xml")
    if not path.is_file():
        return None
    root=ET.parse(path).getroot()
    result={}
    for element in root.iter("plotProperties"):
        name=element.findtext("name")
        if name not in ("Phase1","Magnitude1"):
            continue
        if element.findtext("visible")!="1":
            continue
        value=element.findtext("ordinateRange") or ""
        parts=value.split(",")
        if len(parts)!=2: continue
        lo,hi=map(float,parts)
        if not (math.isfinite(lo) and math.isfinite(hi)
                and -500<=lo<hi<=500 and 1<hi-lo<500):
            continue
        key="phase" if name=="Phase1" else "mag"
        result[key]=(lo,hi)
    return result if "mag" in result and "phase" in result else None
''',encoding='utf-8')

p=base/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('from plot_geometry_v7 import locate_plots',
            'from plot_geometry_v7 import locate_plots\\nfrom smaart_axes_v71 import read_saved_axes')
s=s.replace('        self.draw_count=0','        self.draw_count=0\\n        self.display_offset_db=0.0')
a=s.index('    def paintEvent(self,event):')
b=s.index('\\nclass QAHost(',a)
s=s[:a]+'''    def paintEvent(self,event):
        self.draw_count+=1
        if self.data is None:return
        d=self.data
        w,h=self.width(),self.height()
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        base=QColor("#42f6ff") if self.kind=="mag" else QColor("#f48dff")
        vals=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        # Mag must remain available at low coherence. Show low-COH portions
        # faintly, rather than deleting half the frequency spectrum.
        # Phase retains its coherence gate to avoid noisy phase artifacts.
        paths={"high":QPainterPath(),"low":QPainterPath()}
        prev_type=None
        prev_phase=None
        count={"high":0,"low":0}
        segments=0
        denom=np.log(self.f_max/self.f_min)
        for f,y,coh,good in zip(d.hz,vals,d.coherence,d.valid):
            if not(self.f_min<=f<=self.f_max) or not np.isfinite(y):
                prev_type=None;prev_phase=None;continue
            quality="high" if good else "low"
            if self.kind=="phase" and quality=="low":
                prev_type=None;prev_phase=None;continue
            xx=float((np.log(f/self.f_min)/denom)*w)
            yy=float((self.y_max-y)/(self.y_max-self.y_min)*h)
            if not np.isfinite(xx+yy) or not 0<=yy<=h:
                prev_type=None;prev_phase=None;continue
            path=paths[quality]
            if (quality!=prev_type or prev_phase is None or
                (self.kind=="phase" and abs(y-prev_phase)>170)):
                path.moveTo(xx,yy)
                segments+=1
            else:
                path.lineTo(xx,yy)
            prev_type=quality;prev_phase=y
            count[quality]+=1
        self._last_points=count["high"]+count["low"]
        self._last_segments=segments
        for quality in ("low","high"):
            color=QColor(base)
            if quality=="low":color.setAlpha(85)
            painter.setPen(QPen(color,1.6 if quality=="low" else 2.15))
            painter.drawPath(paths[quality])
        painter.setPen(QColor("#f1b977") if self.display_offset_db else QColor(base))
        painter.setOpacity(.95)
        painter.setFont(self.font())
        offset=(f" | DISPLAY OFFSET {self.display_offset_db:+.1f} dB"
                if self.kind=="mag" and self.display_offset_db else "")
        painter.drawText(95,19,f"SUM {self.kind.upper()} MODEL"+offset)
        painter.end()
''' + s[b:]
s=s.replace('self.setFixedSize(354,465)', 'self.setFixedSize(354,500)')
s=s.replace('        layout.addLayout(yrow)\n        self.solve=QPushButton',
'''        layout.addLayout(yrow)
        self.mag_fit=QCheckBox("Tự đưa Mag vào khung (chỉ dịch hiển thị)")
        self.mag_fit.setChecked(True)
        self.mag_fit.stateChanged.connect(self.recalc)
        layout.addWidget(self.mag_fit)
        self.solve=QPushButton''')
needle='''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        self.update_y_ranges()'''
assert needle in s
s=s.replace(needle,'''        self.graph_mag=SumGraph("mag")
        self.graph_phase=SumGraph("phase")
        saved_axes=read_saved_axes()
        if saved_axes:
            for box,value in ((self.mag_min,saved_axes["mag"][0]),
                              (self.mag_max,saved_axes["mag"][1]),
                              (self.phase_min,saved_axes["phase"][0]),
                              (self.phase_max,saved_axes["phase"][1])):
                box.setValue(value)
            self.axis_note.setText("Đọc Y từ SmaartConfig.xml (lưu lần gần nhất)")
        else:
            self.axis_note.setText("Không đọc được Y của Smaart; cần kiểm tra thang Y")
        self.update_y_ranges()''')
needle='''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),coh_gate=.60)
        self.graph_mag.set_data(self.current_sum)'''
assert needle in s
s=s.replace(needle,'''        self.current_sum=compute_sum(*self.current_traces,
             delay_ms=self.delay.value(),invert_trace2=self.invert.isChecked(),coh_gate=.60)
        self.graph_mag.display_offset_db=0.0
        if self.mag_fit.isChecked():
            d=self.current_sum
            visible=(d.hz>=20)&(d.hz<=20000)&np.isfinite(d.mag_db)
            mag=d.mag_db[visible]
            if len(mag)>0:
                lo=self.mag_min.value()
                hi=self.mag_max.value()
                inside=np.mean((mag>=lo)&(mag<=hi))
                if inside<.30:
                    # Display-only shift; original solver/source dB unchanged.
                    # This preview is deliberately NOT numeric Smaart parity.
                    self.graph_mag.display_offset_db=round(
                        (lo+hi)*0.5-float(np.median(mag)),1)
        if self.graph_mag.display_offset_db:
            self.axis_note.setText(
                f"MODEL Mag: dịch hiển thị {self.graph_mag.display_offset_db:+.1f} dB; "
                "KHÔNG phải gain vật lý")
        self.graph_mag.set_data(self.current_sum)''')
s=s.replace('''        self.graph_mag.update();self.graph_phase.update()

    def on_plot_layout''',
'''        if self.current_traces:self.recalc()
        else:self.graph_mag.update();self.graph_phase.update()

    def on_plot_layout''')
# Show real source pair in GUI, and handle unknown/mismatched file data honestly
p.write_text(s,encoding='utf-8')
print("PATCHED",base)
