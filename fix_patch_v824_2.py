from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\patch_v824_ui.py")
s=p.read_text(encoding="utf8")
a=s.index("needle='''                  padding:3px 6px;")
b=s.index("needle='''        layout.setSpacing(4)",a)
s=s[:a]+'''assert s.count("padding:3px 6px;min-height:40px;}")==1
s=s.replace("padding:3px 6px;min-height:40px;}",
            "padding:1px 5px;min-height:30px;}",1)
assert s.count("min-height:32px;}")==1
s=s.replace("min-height:32px;}","min-height:29px;}",1)
'''+s[b:]
p.write_text(s,encoding="utf8")
print("PATCH_CSS_2_REWRITTEN")
