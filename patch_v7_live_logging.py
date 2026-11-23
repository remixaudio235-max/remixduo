from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
s=p.read_text(encoding="utf-8")
s=s.replace('''    def on_selection(self,record):
        # Invalidate''','''    def on_selection(self,record):
        print("V7_PAIR_EVENT",record.names if record else None,flush=True)
        # Invalidate''')
s=s.replace('''        self.recalc()
        self.status.setText(''','''        self.recalc()
        print("V7_SUM_RENDER_READY",self.current_sum.sources if self.current_sum else None,
              len(self.current_sum.hz) if self.current_sum else 0,flush=True)
        self.status.setText(''')
s=s.replace('''        self.plot_hwnd=hwnd
        self.plot_layout=layout''','''        if self.plot_hwnd!=hwnd or self.plot_layout!=layout:
            print("V7_PLOT_RECT",hwnd,layout,flush=True)
        self.plot_hwnd=hwnd
        self.plot_layout=layout''')
p.write_text(s,encoding="utf-8")
print("GUI_QA_LOG_HOOKS_PASS")
