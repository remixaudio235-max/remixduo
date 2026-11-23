from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
s=p.read_text("utf-8")
old='''        if self.plot_hwnd!=hwnd or self.plot_layout!=layout:
            print("V7_PLOT_RECT",hwnd,layout,flush=True)
        self.plot_hwnd=hwnd
        self.plot_layout=layout
        self._apply_plot_layout()'''
new='''        changed=(self.plot_hwnd!=hwnd or self.plot_layout is None or
                 self.plot_layout.phase!=layout.phase or self.plot_layout.mag!=layout.mag)
        if changed:
            print("V7_PLOT_RECT",hwnd,layout.phase,layout.mag,flush=True)
        self.plot_hwnd=hwnd
        self.plot_layout=layout
        if changed:self._apply_plot_layout()'''
if old not in s:raise RuntimeError("source on_plot_layout mismatch")
s=s.replace(old,new)
s=s.replace('''        self.label=f"SUM {kind.upper()} (model)"''','''        self.label=f"SUM {kind.upper()} (MODEL - Y do RemiX chon)"''')
# Inform user that graphical Y-axis of Smaart is not automatically matched.
s=s.replace('''        self.notes.setWordWrap(True);layout.addWidget(self.notes)''',
'''        self.notes.setWordWrap(True);layout.addWidget(self.notes)
        self.axis_note=QLabel("Y Mag/Phase can khop truc Smaart; chua tu doc Y axis",self)
        self.axis_note.setWordWrap(True);layout.addWidget(self.axis_note)''')
p.write_text(s,encoding="utf-8")
print("V7_PLOT_DIRTY_PATCH_PASS")
