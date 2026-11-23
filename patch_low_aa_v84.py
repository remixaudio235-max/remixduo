from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_4_SUM_CONTINUITY_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
needle='''        for quality in ("low","high"):
            color=QColor(base)'''
assert s.count(needle)==1
s=s.replace(needle,'''        for quality in ("low","high"):
            # Weak-coherence trace is a translucent orientation guide, not
            # authoritative phase. Disable costly AA for this fallback path;
            # preserve AA on reliable foreground SUM lines.
            painter.setRenderHint(QPainter.RenderHint.Antialiasing,
                                  quality=="high")
            color=QColor(base)''')
p.write_text(s,encoding='utf-8')
print("V84_DISABLE_AA_ONLY_FOR_WEAK_FALLBACK")
