from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\patch_v824_ui.py")
s=p.read_text(encoding="utf-8")
a=s.index("needle='''             QFrame#panelCard")
b=s.index("needle='''                  padding",a)
s=s[:a]+'''import re
s,n=re.subn(r"(QFrame#panelCard[^\\n]*\\n\\s*border-radius:)10px;",
            r"\\g<1>7px;",s,count=1)
assert n==1, "QFrame panel card CSS not found"
'''+s[b:]
p.write_text(s,encoding="utf-8")
print("PATCH_HELPER_FIXED")
