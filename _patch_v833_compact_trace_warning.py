"""V8.33 surgical compact Auto Phase trace/warning UI, preserve state engine."""
from pathlib import Path
root=Path(__file__).resolve().parent
engine=root/'overlay_v7.py'
gui=root/'signal_tools_gui_v813.py'
a=engine.read_text(encoding='utf-8')
b=gui.read_text(encoding='utf-8')
def one(s,old,new):
    hits=s.count(old)
    if hits!=1:raise RuntimeError(f"expected 1 occurrence, got {hits}: {old[:90]!r}")
    return s.replace(old,new,1)

# A real size policy prevents the 3-trace warning/card from consuming
# remaining vertical space when Top3 is hidden.
trace_lines=[line for line in a.splitlines(keepends=True)
             if 'trace=make_card(' in line]
if len(trace_lines)!=1:
    raise RuntimeError('Trace source layout anchor count mismatch')
a=one(a,trace_lines[0],trace_lines[0]+
      '        self.trace_card=trace.parentWidget()\n'
      '        self.trace_card.setObjectName("traceCard")\n'
      '        self.trace_card.setSizePolicy(\n'
      '            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)\n'
      '        self.trace_card.setFixedHeight(138)\n')
a=one(a,
      '        trace.addWidget(self.selection_warning)\n',
      '        self.selection_warning.setAlignment(\n'
      '            Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)\n'
      '        self.selection_warning.setFixedHeight(36)\n'
      '        self.selection_warning.setSizePolicy(\n'
      '            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)\n'
      '        trace.addWidget(self.selection_warning)\n')
a=one(a,
      '            "color:#FFD1A1;background:#352418;border:1px solid #A36A25;"\n'
      '            "font:bold 10px \'Segoe UI\';border-radius:5px;padding:4px;")',
      '            "color:#FFCC97;background:#291F19;border:1px solid #80552F;"\n'
      '            "font:600 10px \'Segoe UI\';border-radius:6px;"\n'
      '            "padding:3px 7px;")')
a=one(a,
      '        # Compact tabs keep rarely needed Y-axis / diagnostic text away\n',
      '        # Keep Top3 at its actual content height, not an expanded card.\n'
      '        self.candidate_card.setSizePolicy(\n'
      '            QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)\n'
      '        self.candidate_card.setFixedHeight(167)\n'
      '        # Compact tabs keep rarely needed Y-axis / diagnostic text away\n')
a=one(a,
      '        self.tabs.hide()\n',
      '        self.tabs.hide()\n'
      '        # Distribute unused space below the content, never inside\n'
      '        # the warning or Trace rows. Normal Top3 remains unchanged.\n'
      '        layout.addStretch(1)\n')
a=one(a,
      '    def _set_tick_presentation(self,valid:bool):\n'
      '        self._selection_verified=bool(valid)\n',
      '    def _set_tick_presentation(self,valid:bool):\n'
      '        # Verified pair = two compact trace name/result rows; invalid\n'
      '        # count = only section title + slim warning message.\n'
      '        self.trace_card.setFixedHeight(138 if valid else 70)\n'
      '        self._selection_verified=bool(valid)\n')
# Only for a confirmed invalid tick count. Transient pending won't flicker
# between tall/short right docks while snapshots stabilize.
b=one(b,
      '    def apply_rect(self,rect):\n'
      '        x,y,w,h=rect\n'
      '        self.setFixedSize(w,h)\n',
      '    def apply_rect(self,rect):\n'
      '        x,y,w,h=rect\n'
      '        invalid_phase=(self.stack.currentWidget() is self.pages["phase"]\n'
      '                       and getattr(self.engine,"_selection_quality","")=="invalid"\n'
      '                       and not getattr(self.engine,"_selection_verified",False))\n'
      '        if invalid_phase:\n'
      '            h=min(h,148)\n'
      '        self.setFixedSize(w,h)\n')
engine.write_text(a,encoding='utf-8')
gui.write_text(b,encoding='utf-8')
print('V833_PATCH_APPLIED',engine,gui,flush=True)
