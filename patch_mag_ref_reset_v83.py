from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_3_MAG_REF_ANCHOR_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
needle='''        self.last_solve=None
        if hasattr(self,"candidates"):'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.last_solve=None
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        if hasattr(self,"candidates"):''')
p.write_text(s,encoding="utf-8")
print("V83_REF_SWITCH_RESETS_MAG_ANCHOR")
