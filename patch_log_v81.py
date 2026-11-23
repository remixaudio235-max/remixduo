from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_1_HYBRID_PHASE_Y_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert s.count('        self.pan_accepted=0')==1
s=s.replace('        self.pan_accepted=0','        self.pan_last_log=0.0\n        self.pan_accepted=0')
old='''        print("V81_PAN_FAST",dy,round(frame.confidence,3),
              round(frame.capture_ms,1),
              round(self.graph_phase.y_max,1),flush=True)'''
new='''        if now-self.pan_last_log>.25:
            self.pan_last_log=now
            print("V81_PAN_FAST",dy,round(frame.confidence,3),
                  round(frame.capture_ms,1),
                  round(self.graph_phase.y_max,1),flush=True)'''
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('V81_LIGHTWEIGHT_LOG_PATCHED')
