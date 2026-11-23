from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_2_DUAL_AXIS_FOLLOW_QA')
p=base/'native_fast_pan_v81.py'
s=p.read_text(encoding="utf-8")
needle='''        width=min(int(w*.65),w-off-290)'''
assert s.count(needle)==1
s=s.replace(needle,'''        width=min(int(w*.65),w-off-290,
                  int(getattr(self,"sample_width",1000000)))''')
p.write_text(s,encoding="utf-8")
p=base/'native_dual_y_v82.py'
s=p.read_text(encoding="utf-8")
needle='''        self.phase=NativeFastPan()
        self.mag=NativeFastPan()'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.phase=NativeFastPan()
        self.mag=NativeFastPan()
        # Compact native ROIs retain independent Smaart polylines while
        # reducing GDI readback and 2D fine-match computation.
        self.phase.sample_width=560
        self.mag.sample_width=560''')
p.write_text(s,encoding="utf-8")
p=base/'qa_dual_native_pixels_v82.py'
s=p.read_text(encoding="utf-8")
needle=''' width=min(int(w*.65),w-offset-290)'''
assert s.count(needle)==1
s=s.replace(needle,''' width=min(int(w*.65),w-offset-290,560)''')
p.write_text(s,encoding="utf-8")
print("V82_DUAL_COMPACT_ROI_560_PATCHED")
