from pathlib import Path
import re
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_20_MAG_EQ_INTEGRATED_CLEAN_UI_QA")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
old='''            label=QLabel(f"{number}  {heading}")
            label.setObjectName("sectionTitle")
            col.addWidget(label)
            layout.addWidget(frame)'''
new='''            # Hide the entire heading row for button-only cards.
            # Preserve unnumbered headings for Trace and Top 3.
            if heading:
                title=(f"{number}  {heading}" if number else heading)
                label=QLabel(title)
                label.setObjectName("sectionTitle")
                col.addWidget(label)
            else:
                col.setContentsMargins(6,3,6,3)
            layout.addWidget(frame)'''
assert s.count(old)==1,s.count(old)
s=s.replace(old,new)
patterns=[
    (r'trace=make_card\("([^"]+)","01"\)',r'trace=make_card("\1",None)'),
    (r'control=make_card\("AUTO ALIGN / [^"]+","02"\)',r'control=make_card(None,None)'),
    (r'self\.solve=QPushButton\("AUTO ALIGN"\)',r'self.solve=QPushButton("AUTO PHASE")'),
    (r'candidates_card=make_card\("([^"]+)","03"\)',r'candidates_card=make_card("\1",None)'),
]
for pattern,replacement in patterns:
    s,count=re.subn(pattern,replacement,s)
    assert count==1,(pattern,count)
s=s.replace("V8.19","V8.20")
p.write_text(s,encoding="utf-8")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8").replace("V8.19","V8.20")
p.write_text(s,encoding="utf-8")
print("V820_UI_PATCH_PASS")
