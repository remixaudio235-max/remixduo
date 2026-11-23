from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_3_MAG_REF_ANCHOR_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
needle='''        if not frame.valid:
            self.mag_pan_rejected+=1'''
assert s.count(needle)==1
s=s.replace(needle,'''        # Magnitude has several similar-shaped traces. Scores around 0.75
        # were falsely interpreted as ~34px pans in V8.2 (causing Y drift).
        # A real native Mag translation scores >=0.96 in QA. Reject weak
        # matches rather than moving the SUM away from its REF anchor.
        if not frame.valid or frame.confidence < .90:
            self.mag_pan_rejected+=1''')
p.write_text(s,encoding="utf-8")
print("V83_MAG_PAN_WEAK_CORRELATION_FILTER_0.90")
