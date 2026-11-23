from pathlib import Path
base=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_1_QA')
for name in ('full_scan_v7.py','live_sync_v7.py'):
    p=base/name
    s=p.read_text(encoding='utf-8')
    before=s.count('\\n                       uia_rows')
    assert before==1,(name,before)
    s=s.replace('\\n                       uia_rows','\n                       uia_rows')
    p.write_text(s,encoding='utf-8')
p=base/'apply_v71_patch.py'
s=p.read_text(encoding='utf-8')
s=s[s.index("p=base/'overlay_v7.py'"):]
s=s.replace("b=s.index('\\nclass QAHost(',a)",
            "b=s.index('class QAHost(',a)")
exec(s)
