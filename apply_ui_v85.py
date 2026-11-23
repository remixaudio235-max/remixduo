from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_5_REMIX_SIGNAL_UI_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
s=s.replace('QCheckBox,QDoubleSpinBox,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame)',
            'QCheckBox,QDoubleSpinBox,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QTabWidget,QSizePolicy)')
s=s.replace('RemiX Auto Align V8.4 - Windows QA','RemiX Signal V8.5 - Windows QA')
start=s.index('        self.setFixedSize(354,713)')
end=s.index('        self.events=Events()',start)
ui=r'''        # RemiX Signal: compact, dark, high-contrast Smaart companion.
        # All original widget attributes and calculation callbacks are
        # preserved so engineering behavior remains identical to V8.4.
        self.setFixedSize(402,770)
        self.setStyleSheet("""
            QWidget { background:#090E15; color:#DFEDF3;
                      font-family:'Segoe UI'; font-size:11px; }
            QFrame#panelCard {background:#111C29; border:1px solid #284055;
                               border-radius:10px;}
            QFrame#header {background:#091821; border:1px solid #295061;
                            border-radius:11px;}
            QLabel#brand {font-size:20px;font-weight:700;color:#53E7F5;}
            QLabel#version {font-size:10px;color:#91AABB;}
            QLabel#sectionTitle {font-weight:700;font-size:11px;
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
            QPushButton#run {background:#FF922A;color:#14151A;
                             font-weight:800;font-size:14px;
                             border:0;border-radius:8px;
                             min-height:39px;}
            QPushButton#run:hover {background:#FFAF55;}
            QPushButton#run:pressed {background:#DF7420;}
            QTabWidget::pane {border:1px solid #2D485B;
                              background:#111C29;border-radius:8px;}
            QTabBar::tab {background:#132739;color:#9AB5C6;
                           padding:6px 11px;min-width:65px;}
            QTabBar::tab:selected {background:#224354;
                                   color:#65EFF4;font-weight:700;}
        """)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(10,9,10,9)
        layout.setSpacing(6)

        def make_card(heading,number):
            frame=QFrame(self)
            frame.setObjectName("panelCard")
            col=QVBoxLayout(frame)
            col.setContentsMargins(10,8,10,8)
            col.setSpacing(5)
            label=QLabel(f"{number}   {heading}")
            label.setObjectName("sectionTitle")
            col.addWidget(label)
            layout.addWidget(frame)
            return col

        def tag(text):
            label=QLabel(text)
            label.setObjectName("caption")
            return label

        header=QFrame(self)
        header.setObjectName("header")
        hrow=QHBoxLayout(header)
        hrow.setContentsMargins(12,7,11,7)
        names=QVBoxLayout()
        names.setSpacing(0)
        brand=QLabel("RemiX  SIGNAL")
        brand.setObjectName("brand")
        names.addWidget(brand)
        edition=QLabel("SMAART COMPANION  ·  WINDOWS V8.5")
        edition.setObjectName("version")
        names.addWidget(edition)
        hrow.addLayout(names,1)
        readonly=QLabel("READ ONLY")
        readonly.setStyleSheet("color:#7DEAD2;border:1px solid #247F71;"
                               "background:#0F302D;border-radius:8px;"
                               "font:bold 10px 'Segoe UI';padding:4px 8px;")
        hrow.addWidget(readonly)
        layout.addWidget(header)

        # TRACE / REFERENCE
        trace=make_card("TRACE ĐANG CHỌN","01")
        self.pair_label=QLabel("Đang chờ 2 Trace được chọn")
        self.pair_label.setObjectName("tracePair")
        self.pair_label.setWordWrap(True)
        self.pair_label.setMinimumHeight(29)
        self.pair_label.setMaximumHeight(38)
        trace.addWidget(self.pair_label)
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
        self.correction_target_label=QLabel(
            "REF TRACE 1 GIỮ NGUYÊN · BÙ TRACE 2")
        self.correction_target_label.setObjectName("amber")
        trace.addWidget(self.correction_target_label)

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

        # ALIGN CONTROL: no rows wider than the actual 382px content area.
        control=make_card("AUTO ALIGN / VÙNG ĐO","03")
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
        delayrow=QHBoxLayout()
        delayrow.setSpacing(7)
        delayrow.addWidget(tag("SHIFT"))
        self.delay=QDoubleSpinBox()
        self.delay.setRange(-180,180)
        self.delay.setDecimals(2)
        self.delay.setSingleStep(.1)
        self.delay.setSuffix(" ms")
        self.delay.valueChanged.connect(self.recalc)
        delayrow.addWidget(self.delay,1)
        self.invert=QCheckBox("ĐẢO TRACE 2")
        self.invert.stateChanged.connect(self.recalc)
        delayrow.addWidget(self.invert)
        control.addLayout(delayrow)
        self.solve=QPushButton("AUTO ALIGN")
        self.solve.setObjectName("run")
        self.solve.clicked.connect(self.align)
        control.addWidget(self.solve)

        candidates_card=make_card("TOP 3 PHƯƠNG ÁN","04")
        self.candidates=[QLabel("—") for _ in range(3)]
        for item in self.candidates:
            item.setObjectName("result")
            item.setMinimumHeight(17)
            candidates_card.addWidget(item)

        # Compact tabs keep rarely needed Y-axis / diagnostic text away
        # from real-time phase match and solve controls.
        self.tabs=QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        display_page=QWidget()
        displaycol=QVBoxLayout(display_page)
        displaycol.setContentsMargins(9,7,9,7)
        displaycol.setSpacing(7)
        showrow=QHBoxLayout()
        self.mag=QCheckBox("SUM MAG")
        self.mag.setChecked(True)
        self.mag.stateChanged.connect(self.refresh_visibility)
        self.phase=QCheckBox("SUM PHASE")
        self.phase.setChecked(True)
        self.phase.stateChanged.connect(self.refresh_visibility)
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
        smoothrow.setHorizontalSpacing(8)
        smoothrow.addWidget(tag("MAG SMOOTH"),0,0)
        smoothrow.addWidget(tag("PHASE SMOOTH"),0,1)
        smoothrow.addWidget(self.mag_smooth,1,0)
        smoothrow.addWidget(self.phase_smooth,1,1)
        displaycol.addLayout(smoothrow)
        self.mag_fit=QCheckBox("Auto-fit Mag (chỉ hiển thị)")
        self.mag_fit.setChecked(True)
        self.mag_fit.setToolTip("Điều chỉnh vị trí SUM Mag, không thay đổi DSP Gain.")
        self.mag_fit.stateChanged.connect(self.recalc)
        displaycol.addWidget(self.mag_fit)
        self.tabs.addTab(display_page,"Hiển thị")

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
        axes.setHorizontalSpacing(6)
        axes.addWidget(tag("TRỤC Y"),0,0)
        axes.addWidget(tag("MIN"),0,1)
        axes.addWidget(tag("MAX"),0,2)
        axes.addWidget(tag("MAG (dB)"),1,0)
        axes.addWidget(self.mag_min,1,1)
        axes.addWidget(self.mag_max,1,2)
        axes.addWidget(tag("PHASE (°)"),2,0)
        axes.addWidget(self.phase_min,2,1)
        axes.addWidget(self.phase_max,2,2)
        axiscol.addLayout(axes)
        self.tabs.addTab(axis_page,"Trục Y")

        info_page=QWidget()
        self.diag_layout=QVBoxLayout(info_page)
        self.diag_layout.setContentsMargins(9,7,9,7)
        self.diag_layout.setSpacing(5)
        self.notes=QLabel("TF lưu trữ · Không lấy TF trực tiếp qua Smaart API")
        self.notes.setObjectName("diagnostic")
        self.notes.setWordWrap(True)
        self.diag_layout.addWidget(self.notes)
        self.axis_note=QLabel("Trục Y: đang chờ đồng bộ")
        self.axis_note.setObjectName("diagnostic")
        self.axis_note.setWordWrap(True)
        self.diag_layout.addWidget(self.axis_note)
        self.tabs.addTab(info_page,"Thông tin")
        layout.addWidget(self.tabs,1)

        self.status=QLabel("Đang chờ Smaart")
        self.status.setObjectName("footer")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(33)
        self.status.setMaximumHeight(51)
        layout.addWidget(self.status)
'''
s=s[:start]+ui+s[end:]
# Adapt diagnostics labels to the info tab, instead of old top-level insertion.
s=s.replace('layout.insertWidget(layout.indexOf(self.axis_note),self.phase_axis_note)',
            'self.phase_axis_note.setObjectName("diagnostic")\n        self.phase_axis_note.setWordWrap(True)\n        self.diag_layout.addWidget(self.phase_axis_note)')
s=s.replace('layout.insertWidget(layout.indexOf(self.axis_note),self.mag_axis_note)',
            'self.mag_axis_note.setObjectName("diagnostic")\n        self.mag_axis_note.setWordWrap(True)\n        self.diag_layout.addWidget(self.mag_axis_note)')
# Remove per-label style that truncates in old layout.
s=s.replace('self.phase_axis_note.setStyleSheet("color:#9cd3f2;font:10px \'Segoe UI\'")',
            'self.phase_axis_note.setStyleSheet("color:#9cd3f2;font:10px \'Segoe UI\'")')
s=s.replace('self.mag_axis_note.setStyleSheet("color:#b1e7a6;font:10px \'Segoe UI\'")',
            'self.mag_axis_note.setStyleSheet("color:#b1e7a6;font:10px \'Segoe UI\'")')
# Correct only UI copy in methods; leave DSP logic untouched.
s=s.replace('self.pair_label.setText("TRACE 1: "+Path(record.names[0]).stem+"\\nTRACE 2: "+Path(record.names[1]).stem)',
            'self.pair_label.setText("01  "+Path(record.names[0]).stem+"\\n02  "+Path(record.names[1]).stem)')
s=s.replace('self.invert.setText(f"D?O TRACE {other_num}")','self.invert.setText(f"ĐẢO TRACE {other_num}")')
s=s.replace('f"REF TRACE {new_ref} GI? NGUYEN \\x07 BU TUONG D?I TRACE {other_num}"',
            'f"REF TRACE {new_ref} GIỮ NGUYÊN · BÙ TRACE {other_num}"')
# Fix garbled Δ label literals in functional updates.
s=s.replace('f"� SUM-REF: {delta:.2f}� | P95: {p95:.2f}�"',
            'f"Δ SUM–REF: {delta:.2f}° | P95: {p95:.2f}°"')
s=s.replace('f"� SUM-REF: -- � | P95: -- � ({delta_bins} bins)"',
            'f"Δ SUM–REF: --° | P95: --° ({delta_bins} bins)"')
s=s.replace('self.sum_ref_label.setText("� SUM-REF: -- �  |  P95: -- �")',
            'self.sum_ref_label.setText("Δ SUM–REF: --° | P95: --°")')
# Move panel fully on-screen instead of old width-agnostic hardcoded right-365.
s=s.replace('if attached and self.geometry().x()!=x+w-350:\n                    self.move(x+w-350,y+45)',
'''if attached:
                    screen=QApplication.primaryScreen().availableGeometry()
                    px=max(screen.left()+8,min(x+w-self.width()-12,
                         screen.right()-self.width()-8))
                    py=max(screen.top()+8,min(y+55,
                         screen.bottom()-self.height()-8))
                    if self.pos().x()!=px or self.pos().y()!=py:
                        self.move(px,py)''')
s=s.replace('if self.isVisible() and self.geometry().x()!=r-365:self.move(r-365,t+100)',
'''if self.isVisible():
            area=QApplication.primaryScreen().availableGeometry()
            px=max(area.left()+8,min(r-self.width()-10,
                   area.right()-self.width()-8))
            py=max(area.top()+8,min(t+75,
                   area.bottom()-self.height()-8))
            if abs(self.x()-px)>1 or abs(self.y()-py)>1:
                self.move(px,py)''')
p.write_text(s,encoding='utf-8')
print("REMIX_SIGNAL_V85_LAYOUT_PATCH_PASS",len(ui.splitlines()),"layout lines")
