from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\patch_v824_ui.py")
s=p.read_text(encoding="utf8")
a=s.index("needle='''        candidates_card=make_card")
b=s.index("needle='''            button.setFixedHeight",a)
s=s[:a]+'''assert s.count("        self.candidates=[]")==1
s=s.replace("        self.candidates=[]",
            "        self.candidate_card=candidates_card.parentWidget()\\n"
            "        self.candidates=[]",1)
'''+s[b:]
p.write_text(s,encoding="utf8")
print("PATCH_V824_CANDIDATES_ANCHOR_FIXED")
