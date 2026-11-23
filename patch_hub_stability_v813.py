from pathlib import Path
base=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_13_TOOL_HUB_QA")
p=base/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
needle='''        self.fir=FIRDialog(engine)
        self.active=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.fir=FIRDialog(engine)
        self._last_pair_key=None
        self.active=None''')
needle='''    def tick(self):
        target=locate_smaart()'''
assert s.count(needle)==1
s=s.replace(needle,'''    def tick(self):
        # The existing selection worker completes asynchronously.
        # Refresh tool source lists once when pair changes or finishes
        # loading, not once per 175ms poll (would discard user previews).
        pair_key=(tuple(self.engine.current_pair or ()),
                  bool(self.engine.current_traces))
        if pair_key!=self._last_pair_key:
            self._last_pair_key=pair_key
            self.eq.refresh_sources()
            self.fir.refresh_sources()
        target=locate_smaart()''')
p.write_text(s,encoding="utf8")
q=base/"overlay_v7.py"
s=q.read_text(encoding="utf8")
needle='''    def closeEvent(self,event):
        self.graph_mag.close();self.graph_phase.close()'''
assert s.count(needle)==1
s=s.replace(needle,'''    def closeEvent(self,event):
        if self.managed_mode:
            # Closing the Auto Phase popup must not terminate the
            # shared Smaart TRF observer used by Auto EQ and FIR.
            self.ui_tool_enabled=False
            self.hide()
            event.ignore()
            return
        self.graph_mag.close();self.graph_phase.close()''')
q.write_text(s,encoding="utf8")
print("V813_TOOL_PERSISTENCE_AND_PAIR_REFRESH_PATCH_PASS")
