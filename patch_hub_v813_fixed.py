from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_13_TOOL_HUB_QA\overlay_v7.py")
s=p.read_text(encoding="utf-8")
assert s.count('self.setWindowTitle("RemiX Signal V8.12")')==2
# one demo host, one real App
s=s.replace('self.setWindowTitle("RemiX Signal V8.12")',
            'self.setWindowTitle("RemiX Signal V8.13 · Auto Phase")')
s=s.replace('edition=QLabel("SMAART · V8.12")','edition=QLabel("SMAART · V8.13")')
s=s.replace('edition=QLabel("SMAART � V8.12")','edition=QLabel("SMAART · V8.13")')
s=s.replace('''        self.demo=demo
        self.setWindowTitle(''', '''        self.demo=demo
        self.managed_mode=False
        self.ui_tool_enabled=True
        self.setWindowTitle(''')
start=s.index('    def tick(self):',s.index('class App('))
ix=s.index('        if not self.isVisible():self.show()',start)
s=s[:ix]+'''        if not self.isVisible() and (not self.managed_mode or self.ui_tool_enabled):
            self.show()
        elif self.isVisible() and self.managed_mode and not self.ui_tool_enabled:
            self.hide()'''+s[ix+len('        if not self.isVisible():self.show()'):]
assert 'py=max(area.top()+8,min(t+75,' in s
s=s.replace('py=max(area.top()+8,min(t+75,',
            'py=max(area.top()+8,min(t+(164 if self.managed_mode else 75),')
needle='''    view=App(a.demo)
    app.exec()'''
assert s.count(needle)==1
s=s.replace(needle,'''    view=App(a.demo)
    from signal_tools_gui_v813 import ToolHub
    hub=ToolHub(view)
    app.exec()''')
p.write_text(s,encoding="utf8")
print("V813_HUB_PATCH_OK")
