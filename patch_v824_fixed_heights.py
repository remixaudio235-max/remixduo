from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf-8")
a='self.page_heights={"phase":316,"eq":555,"fir":475}'
assert s.count(a)==1
s=s.replace(a,'self.page_heights={"phase":283,"eq":555,"fir":475}',1)
a='''        engine.header.hide()
        for widget in self.pages.values():'''
assert s.count(a)==1
s=s.replace(a,'''        engine.header.hide()
        engine.setFixedHeight(283)  # Remove inherited legacy 400px stretch.
        for widget in self.pages.values():''',1)
a="compact=335 if self.engine._selection_verified else 195"
assert s.count(a)==1
s=s.replace(a,"compact=313 if self.engine._selection_verified else 178",1)
p.write_text(s,encoding="utf-8")
print("V824_PHASE_HEIGHT_COMPACT_PASS")
