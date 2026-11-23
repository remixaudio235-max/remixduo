from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_5_REMIX_SIGNAL_UI_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
needle='''        self.setFixedSize(402,770)
        self.setStyleSheet("""'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.setFixedSize(402,770)
        self.setObjectName("rootPanel")
        self.setStyleSheet("""''')
needle='''            QWidget { background:#090E15; color:#DFEDF3;
                      font-family:'Segoe UI'; font-size:11px; }'''
assert s.count(needle)==1
s=s.replace(needle,'''            QWidget { color:#DFEDF3; font-family:'Segoe UI'; font-size:11px; }
            QWidget#rootPanel {background:#090E15;}
            QLabel {background:transparent;}''')
needle='''        displaycol.addWidget(self.mag_fit)
        self.tabs.addTab(display_page,"Hiển thị")'''
assert s.count(needle)==1
s=s.replace(needle,'''        displaycol.addWidget(self.mag_fit)
        displaycol.addStretch(1)
        self.tabs.addTab(display_page,"Hiển thị")''')
needle='''        axiscol.addLayout(axes)
        self.tabs.addTab(axis_page,"Trục Y")'''
assert s.count(needle)==1
s=s.replace(needle,'''        axiscol.addLayout(axes)
        axiscol.addStretch(1)
        self.tabs.addTab(axis_page,"Trục Y")''')
needle='''        self.diag_layout.addWidget(self.mag_axis_note)
        # Initial UIA map not verified'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.diag_layout.addWidget(self.mag_axis_note)
        self.diag_layout.addStretch(1)
        # Initial UIA map not verified''')
# QA demo also titled RemiX Signal, and no more old UI window title
assert 'RemiX Auto Align V8.4 - Windows QA' not in s
p.write_text(s,encoding="utf-8")
print("V85_STYLE_BACKGROUND_AND_TAB_SPACING_PASS")
