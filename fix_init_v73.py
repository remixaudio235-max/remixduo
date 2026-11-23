from pathlib import Path
p=Path(__file__).with_name('overlay_v7.py')
s=p.read_text(encoding='utf-8')
old='if not hasattr(self,"roi_markers") or not self.plot_layout:'
assert s.count(old)==1
s=s.replace(old,'if not hasattr(self,"roi_markers") or not getattr(self,"plot_layout",None):')
p.write_text(s,encoding='utf-8')
print('INIT_GEOMETRY_GUARD_FIXED')
