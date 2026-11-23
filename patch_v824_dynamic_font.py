from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
old="font:bold 12px 'Segoe UI';color:"
assert s.count(old)==1
s=s.replace(old,"font:bold 10px 'Segoe UI';color:")
p.write_text(s,encoding="utf-8")
p=root/"qa_v824_top3_compact.py"
s=p.read_text(encoding="utf-8").replace(
    'assert "font:10px" in engine.trace_compact_result',
    'assert "font:bold 10px" in engine.trace_compact_result')
p.write_text(s,encoding="utf-8")
print("V824_TRACE_DELAY_COMPACT_DYNAMIC_FONT_PASS")
