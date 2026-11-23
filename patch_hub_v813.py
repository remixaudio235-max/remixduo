from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_13_TOOL_HUB_QA\overlay_v7.py")
s=p.read_text(encoding="utf-8")
assert s.count('self.setWindowTitle("RemiX Signal V8.12")')==1
s=s.replace('self.setWindowTitle("RemiX Signal V8.12")',
            'self.setWindowTitle("RemiX Signal V8.13 · Auto Phase")')
s=s.replace('edition=QLabel("SMAART · V8.12")',
            'edition=QLabel("SMAART · V8.13")')
s=s.replace('edition=QLabel("SMAART � V8.12")',
            'edition=QLabel("SMAART · V8.13")')
needle='''        self.demo=demo
        self.setWindowTitle('''
assert s.count(needle)==1
s=s.replace(needle,'''        self.demo=demo
        # Standalone by default for backward-compatible unit tests;
        # when controlled by ToolHub the panel is shown only if selected.
        self.managed_mode=False
        self.ui_tool_enabled=True
        self.setWindowTitle(''')
needle='''        if not self.isVisible():self.show()
        r,t,rgt,btm=win32gui.GetWindowRect(target.hwnd)'''
if needle in s:
    s=s.replace(needle,'''        if not self.isVisible() and (not self.managed_mode or self.ui_tool_enabled):
            self.show()
        elif self.isVisible() and self.managed_mode and not self.ui_tool_enabled:
            self.hide()
        r,t,rgt,btm=win32gui.GetWindowRect(target.hwnd)''')
else:
    # Inspect precise original before committing patch.
    idx=s.index('        if not self.isVisible():self.show()',s.index('    def tick(self):'))
    print("TICK_NEAR",repr(s[idx:idx+215]))
    raise RuntimeError("Main tick anchor mismatch")
# app docking below 86px hub instead of on top of navigation
needle='''py=max(area.top()+8,min(t+75,
                   area.bottom()-self.height()-8))'''
assert s.count(needle)==1
s=s.replace(needle,'''py=max(area.top()+8,min(t+(164 if self.managed_mode else 75),
                   area.bottom()-self.height()-8))''')
needle='''if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--demo",action="store_true")
    a=parser.parse_args()
    app=QApplication(sys.argv)
    view=App(a.demo)
    app.exec()'''
assert s.count(needle)==1
s=s.replace(needle,'''if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--demo",action="store_true")
    a=parser.parse_args()
    app=QApplication(sys.argv)
    view=App(a.demo)
    from signal_tools_gui_v813 import ToolHub
    hub=ToolHub(view)
    app.exec()''')
p.write_text(s,encoding="utf-8")
print("V813_MULTITOOL_HUB_INTEGRATED",len(s))
