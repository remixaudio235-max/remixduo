from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_19_FULL_HEIGHT_ROI_DRAG_QA\overlay_v7.py")
s=p.read_text(encoding="utf8")
needle="""        self.graph_mag.close();self.graph_phase.close()
        self.pool.shutdown(wait=False,cancel_futures=True)"""
assert s.count(needle)==1
s=s.replace(needle,"""        # Close native full-height line hit strips and legacy labels.
        for grip in self.roi_line_grips.values():
            grip.close()
        for marker in self.roi_markers.values():
            marker.close()
        self.graph_mag.close();self.graph_phase.close()
        self.pool.shutdown(wait=False,cancel_futures=True)""")
p.write_text(s,encoding="utf8")
print("V819_NATIVE_LINE_WINDOWS_CLEAN_CLOSE_PATCH_PASS")
