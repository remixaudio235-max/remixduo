from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_15_TOPBAR_RIGHT_DOCK_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf8")
needle='''        if self._anchor_future is not None and self._anchor_future.done():
            try:self._anchors=self._anchor_future.result()
            except Exception:self._anchors=None
            self._anchor_future=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        anchor_changed=False
        if self._anchor_future is not None and self._anchor_future.done():
            try:
                latest=self._anchor_future.result()
                anchor_changed=(latest!=self._anchors)
                self._anchors=latest
            except Exception:
                anchor_changed=self._anchors is not None
                self._anchors=None
            self._anchor_future=None''')
needle='''            if not self._was_target or rect!=self._last_host_rect:'''
assert s.count(needle)==1
s=s.replace(needle,'''            if anchor_changed or not self._was_target or rect!=self._last_host_rect:''')
p.write_text(s,encoding="utf8")
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_15_TOPBAR_RIGHT_DOCK_QA\dock_geometry_v815.py")
s=p.read_text(encoding="utf8")
s=s.replace('if text not in ("+ TF Engine","View"):continue','if text not in ("+ TF Engine","- TF Engine","View"):continue')
s=s.replace('if "+ TF Engine" not in found or "View" not in found:','if not any(x in found for x in ("+ TF Engine","- TF Engine")) or "View" not in found:')
s=s.replace('tf=found["+ TF Engine"]','tf=found.get("+ TF Engine",found.get("- TF Engine"))')
p.write_text(s,encoding="utf8")
print("V815_REANCHOR_ON_NATIVE_LAYOUT_CHANGE_PATCHED")
