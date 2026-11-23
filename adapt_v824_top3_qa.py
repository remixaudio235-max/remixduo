from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA\qa_trace_top3_v817.py")
s=p.read_text(encoding="utf8")
# Keep the old algorithmic invariants; only adapt UI font sizes and explicit
# verified offline test fixture for the newer fail-closed sync gate.
s=s.replace('assert "font:bold 12px" in engine.trace_name_labels[0].styleSheet()',
            'assert "font:bold 10px" in engine.trace_name_labels[0].styleSheet()')
s=s.replace('assert "font:bold 12px" in engine.trace_compact_result[0].styleSheet()',
            'assert "font:10px" in engine.trace_compact_result[0].styleSheet()')
s=s.replace('assert "font:bold 12px" in engine.trace_compact_result[1].styleSheet()',
            'assert "font:10px" in engine.trace_compact_result[1].styleSheet()')
needle='''engine.current_pair=tuple(str(t.path) for t in engine.current_traces)
engine.recalc()'''
assert s.count(needle)==1
s=s.replace(needle,'''engine.current_pair=tuple(str(t.path) for t in engine.current_traces)
engine._selection_verified=True   # explicit offline verified TRF fixture
engine.recalc()''')
(root:=p.parent).joinpath("qa_v824_top3_compact.py").write_text(s,encoding="utf8")
print("V824_TOP3_ALGORITHM_QA_ADAPTED")
