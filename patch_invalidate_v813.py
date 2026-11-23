from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_13_TOOL_HUB_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf8")
needle='''        self.filter_count.setPrefix("PEQ ")
        self.main.insertWidget(4,self.filter_count)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.filter_count.setPrefix("PEQ ")
        self.target.valueChanged.connect(self.invalidate)
        self.filter_count.valueChanged.connect(self.invalidate)
        self.main.insertWidget(4,self.filter_count)''')
needle='''        self.taps.setCurrentIndex(1)
        self.main.insertWidget(3,self.taps)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.taps.setCurrentIndex(1)
        self.taps.currentIndexChanged.connect(self.invalidate)
        self.main.insertWidget(3,self.taps)''')
p.write_text(s,encoding="utf8")
print("V813_SETTINGS_INVALIDATE_OLD_PREVIEW_PASS")
