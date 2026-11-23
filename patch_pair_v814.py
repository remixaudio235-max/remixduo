from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_14_UNIFIED_TITLE_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf8")
needle='''    def select(self,name):
        if name not in self.pages:
            raise ValueError("Unsupported tool")
        self.active=name'''
assert s.count(needle)==1
s=s.replace(needle,'''    def select(self,name):
        if name not in self.pages:
            raise ValueError("Unsupported tool")
        pair_key=(tuple(self.engine.current_pair or ()),
                  tuple(id(x) for x in (self.engine.current_traces or ())))
        if pair_key!=self._last_pair_key:
            self._last_pair_key=pair_key
            self.eq.refresh_sources()
            self.fir.refresh_sources()
        self.active=name''')
p.write_text(s,encoding="utf8")
print("V814_SELECTION_INVALIDATES_STALE_EQ_FIR_PASS")
