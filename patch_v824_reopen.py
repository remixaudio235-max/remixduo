from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf8")
old='''        if self._last_host_rect is not None and self._anchors is not None:
            self._update_placements(self._last_host_rect)'''
assert s.count(old)==1
s=s.replace(old,'''        if self._last_host_rect is not None:
            # Fall back to Smaart host rect when native UIA anchors are
            # temporarily unavailable; re-opening after HIDE must work.
            self._update_placements(self._last_host_rect)''',1)
p.write_text(s,encoding="utf8")
print("V824_REOPEN_WITHOUT_UIA_ANCHORS_PATCHED")
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\qa_v824_layout_native.py")
s=p.read_text(encoding="utf8")
old='''hub.select("phase");hub.dock.apply_rect((1490,437,205,313))
app.processEvents()
assert hub.dock.isVisible()'''
assert s.count(old)==1
s=s.replace(old,'''hub._last_host_rect=(0,0,1920,1000)
hub._anchors=None
hub.select("phase")
app.processEvents()
assert hub.dock.isVisible()''')
p.write_text(s,encoding="utf8")
print("V824_REAL_QT_REOPEN_TEST_ADAPTED")
