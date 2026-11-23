"""V8.10 micro sidebar fits Smaart's ~168px right control column.

No DSP/TF/solver changes; only layout and app positioning.
"""
from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_10_NARROW_SIDE_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
assert s.count("self.setFixedSize(402,515)")==1
s=s.replace("RemiX Signal V8.9 - Windows QA","RemiX Signal V8.10 - Windows QA")
s=s.replace("WINDOWS V8.9","WINDOWS V8.10")
s=s.replace("self.setFixedSize(402,515)","self.setFixedSize(164,688)")
s=s.replace("font-size:20px;font-weight:700;color:#53E7F5;",
            "font-size:15px;font-weight:700;color:#53E7F5;")
s=s.replace("QTabBar::tab {background:#132739;color:#9AB5C6;\n                           padding:6px 11px;min-width:65px;}",
            "QTabBar::tab {background:#132739;color:#9AB5C6;\n                           font-size:9px;padding:5px 3px;min-width:38px;}")
s=s.replace("min-height:39px;","min-height:32px;")
s=s.replace("font-weight:800;font-size:14px;","font-weight:800;font-size:12px;")
s=s.replace("layout.setContentsMargins(10,9,10,9)","layout.setContentsMargins(4,6,4,5)")
s=s.replace("layout.setSpacing(6)","layout.setSpacing(4)",1)
s=s.replace("col.setContentsMargins(10,8,10,8)","col.setContentsMargins(6,5,6,5)")
s=s.replace("col.setSpacing(5)","col.setSpacing(3)",1)
s=s.replace("label=QLabel(f\"{number}   {heading}\")",
            "label=QLabel(f\"{number}  {heading}\")")
s=s.replace("font-weight:700;font-size:11px;\n                                  color:#8EC7D5;",
            "font-weight:700;font-size:9px;\n                                  color:#8EC7D5;")
s=s.replace("hrow.setContentsMargins(12,7,11,7)","hrow.setContentsMargins(6,5,5,5)")
s=s.replace('edition=QLabel("SMAART COMPANION  ·  WINDOWS V8.10")',
            'edition=QLabel("SMAART · V8.10")')
s=s.replace('edition=QLabel("SMAART COMPANION  �  WINDOWS V8.10")',
            'edition=QLabel("SMAART · V8.10")')
s=s.replace('edition=QLabel("SMAART COMPANION  -  WINDOWS V8.10")',
            'edition=QLabel("SMAART · V8.10")')
s=s.replace('control=make_card("AUTO ALIGN / VUNG DO","02")',
            'control=make_card("AUTO ALIGN","02")')
s=s.replace('candidates_card=make_card("TOP 3 PHUONG AN","03")',
            'candidates_card=make_card("TOP 3","03")')
s=s.replace('trace=make_card("TRACE DANG CH?N","01")',
            'trace=make_card("TRACE","01")')
start=s.index("        self.trace_grid=QGridLayout()")
end=s.index("        trace.addLayout(self.trace_grid)",start)
new='''        # Two read-only lines per source:
        # name (full name in tooltip), then "Delay 0.00ms · Không đảo".
        # This fits a 164px app anchored entirely in Smaart's side column.
        self.trace_grid=QGridLayout()
        self.trace_grid.setContentsMargins(0,0,0,0)
        self.trace_grid.setHorizontalSpacing(0)
        self.trace_grid.setVerticalSpacing(2)
        self.trace_name_labels=[]
        self.trace_delay_static=[]
        self.trace_polarity_static=[]
        self.trace_delay_tags=[]
        self.trace_compact_result=[]
        for idx in range(2):
            name=QLabel(f"{idx+1:02d}  —")
            name.setStyleSheet("color:#F0FAFF;font:bold 10px 'Segoe UI';")
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
            result.setStyleSheet("color:#9EC5D3;font:10px 'Segoe UI';")
            result.setMinimumHeight(16)
            result.setToolTip("Đề xuất Auto Align, chỉ đọc")
            self.trace_compact_result.append(result)
            self.trace_grid.addWidget(result,idx*2+1,0)
'''
s=s[:start]+new+s[end:]
# keep hidden attrs created so no write to external
start=s.index("    def _update_delay_route_label(self,*_):")
end=s.index("    def on_ref_changed(self,*_):",start)
new='''    def _update_delay_route_label(self,*_):
        """Render model results with no editable delay or invert controls."""
        ref=self._reference_index()
        target=1-ref
        names=tuple(self.current_pair or ())
        for i,label in enumerate(self.trace_name_labels):
            full=Path(names[i]).stem if len(names)==2 else "—"
            shortened=full if len(full)<=17 else full[:16]+"…"
            label.setText(f"{i+1:02d}  {shortened}")
            label.setToolTip(f"Trace {i+1}: {full}")
            val=self.delay.value() if i==target else 0.0
            inv=i==target and self.invert.isChecked()
            self.trace_delay_static[i].setText(f"{val:.2f} ms")
            self.trace_polarity_static[i].setText(
                "Đảo pha" if inv else "Không đảo")
            self.trace_compact_result[i].setText(
                f"Delay {val:.2f}ms · "
                f"{'Đảo pha' if inv else 'Không đảo'}")
            self.trace_compact_result[i].setStyleSheet(
                "color:#FFB47D;font:10px 'Segoe UI';"
                if inv else "color:#9EC5D3;font:10px 'Segoe UI';")
        if hasattr(self,"delay_route_label"):
            self.delay_route_label.setText(
                f"Delay Trace {target+1}: +{self.delay.value():.2f} ms | "
                f"{'Đảo pha' if self.invert.isChecked() else 'Không đảo'} "
                f"| giữ Trace {ref+1}")
        if hasattr(self,"correction_target_label"):
            self.correction_target_label.setText(
                f"TRACE {ref+1} GIỮ NGUYÊN | TRỄ TRACE {target+1}")

'''
s=s[:start]+new+s[end:]
s=s.replace("showrow=QHBoxLayout()","showrow=QVBoxLayout()",1)
s=s.replace('showrow.addWidget(self.mag)\n        showrow.addWidget(self.phase)',
            'showrow.setSpacing(2)\n        showrow.addWidget(self.mag)\n        showrow.addWidget(self.phase)')
s=s.replace('''        smoothrow.addWidget(tag("MAG SMOOTH"),0,0)
        smoothrow.addWidget(tag("PHASE SMOOTH"),0,1)
        smoothrow.addWidget(self.mag_smooth,1,0)
        smoothrow.addWidget(self.phase_smooth,1,1)''',
'''        smoothrow.addWidget(tag("MAG"),0,0)
        smoothrow.addWidget(self.mag_smooth,0,1)
        smoothrow.addWidget(tag("PHASE"),1,0)
        smoothrow.addWidget(self.phase_smooth,1,1)''')
s=s.replace("smoothrow.setHorizontalSpacing(8)","smoothrow.setHorizontalSpacing(4)")
s=s.replace('self.mag_fit=QCheckBox("Auto-fit Mag (ch? hi?n th?)")',
            'self.mag_fit=QCheckBox("Auto-fit Mag")')
s=s.replace('self.mag_fit=QCheckBox("Auto-fit Mag (chỉ hiển thị)")',
            'self.mag_fit=QCheckBox("Auto-fit Mag")')
s=s.replace('self.tabs.addTab(display_page,"Hi?n th?")',
            'self.tabs.addTab(display_page,"Hiện")')
s=s.replace('self.tabs.addTab(display_page,"Hiển thị")',
            'self.tabs.addTab(display_page,"Hiện")')
s=s.replace('self.tabs.addTab(axis_page,"Tr?c Y")',
            'self.tabs.addTab(axis_page,"Trục")')
s=s.replace('self.tabs.addTab(axis_page,"Trục Y")',
            'self.tabs.addTab(axis_page,"Trục")')
s=s.replace('self.tabs.addTab(info_page,"Th�ng tin")',
            'self.tabs.addTab(info_page,"Info")')
s=s.replace('self.tabs.addTab(info_page,"Thông tin")',
            'self.tabs.addTab(info_page,"Info")')
# Make axis ranges readable: pairs of range controls, two per row.
start=s.index("        axes=QGridLayout()")
end=s.index("        axiscol.addLayout(axes)",start)
s=s[:start]+'''        axes=QGridLayout()
        axes.setHorizontalSpacing(3)
        axes.setVerticalSpacing(4)
        axes.addWidget(tag("MAG Y (dB)"),0,0,1,2)
        axes.addWidget(self.mag_min,1,0)
        axes.addWidget(self.mag_max,1,1)
        axes.addWidget(tag("PHASE Y (°)"),2,0,1,2)
        axes.addWidget(self.phase_min,3,0)
        axes.addWidget(self.phase_max,3,1)
'''+s[end:]
# candidate text may wrap instead of overflow.
needle='''            item.setMinimumHeight(17)
            candidates_card.addWidget(item)'''
assert s.count(needle)==1
s=s.replace(needle,'''            item.setMinimumHeight(24)
            item.setWordWrap(True)
            item.setStyleSheet("font:9px 'Segoe UI';color:#D7ECF2;")
            candidates_card.addWidget(item)''')
# ensure titlebar compact, per-window anchor uses far right Smaart Ctrl Bar
s=s.replace('self.setWindowTitle("RemiX Signal V8.10 - Windows QA")',
            'self.setWindowTitle("RemiX Signal V8.10")')
s=s.replace('x+w-self.width()-12','x+w-self.width()-3')
s=s.replace('r-self.width()-10','r-self.width()-3')
p.write_text(s,encoding="utf-8")
print("V810_MICRO_RIGHT_SIDEBAR_UI_PATCHED",len(s))
