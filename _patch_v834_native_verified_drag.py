"""V8.34 anti-ghost: only confirmed native pixels may translate SUM."""
from pathlib import Path
p=Path(__file__).with_name('overlay_v7.py')
s=p.read_text(encoding='utf-8')
def one(old,new):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"Unsafe native gate: {n} matches {old[:90]!r}")
 s=s.replace(old,new,1)
one('        if (getattr(self,"axis_drag",None) is not None or\n'
    '            getattr(self,"mag_axis_drag",None) is not None):return\n'
    '        threshold=.90 if is_mag else .85\n',
    '        # Mouse position alone cannot prove Smaart moved its Y axis.\n'
    '        # Accept only native pixel-correlated motion, even during drag.\n'
    '        threshold=.90 if is_mag else .85\n')
one('    def on_native_fast_pan(self,payload):\n'
    '        key,frame=payload\n'
    '        if getattr(self,"axis_drag",None) is not None:return\n',
    '    def on_native_fast_pan(self,payload):\n'
    '        key,frame=payload\n')
one('        if not self.current_sum or not self.plot_layout:\n'
    '            return\n'
    '        if (getattr(self,"axis_drag",None) is not None or\n'
    '            getattr(self,"mag_axis_drag",None) is not None):return\n'
    '        now=time.monotonic()\n'
    '        # One worker, both charts;',
    '        if not self.current_sum or not self.plot_layout:\n'
    '            return\n'
    '        now=time.monotonic()\n'
    '        # Continue native poll while a Y-ruler gesture is active;\n'
    '        # a blank-ruler drag does not move SUM without real Smaart pixels.\n'
    '        # One worker, both charts;')
one('            lo,hi=shifted_y_range(state["lo"],state["hi"],\n'
    '                                  state["rect"][3],movement)\n'
    '            self.graph_mag.y_min=lo\n'
    '            self.graph_mag.y_max=hi\n'
    '            self.graph_mag.update()\n'
    '            self.mag_pan_last_move=time.monotonic()\n'
    '            if self.mag_pan_last_move-getattr(self,"_drag_spin_tick",0.)>.15:\n'
    '                self._drag_spin_tick=self.mag_pan_last_move\n'
    '                self.mag_min.blockSignals(True);self.mag_max.blockSignals(True)\n'
    '                try:\n'
    '                    self.mag_min.setValue(lo);self.mag_max.setValue(hi)\n'
    '                finally:\n'
    '                    self.mag_min.blockSignals(False);self.mag_max.blockSignals(False)\n'
    '            return\n',
    '            # Do not draw speculative mouse-only displacement.\n'
    '            # on_native_dual_pan applies correlated Smaart pixels instead.\n'
    '            return\n')
one('            if abs(move-state["preview_shift"])>=1.:\n'
    '                state["preview_shift"]=move\n'
    '                self._apply_phase_pan(move,state)\n',
    '            if abs(move-state["preview_shift"])>=1.:\n'
    '                state["preview_shift"]=move\n'
    '                # Native dual-pan drives both overlays. The pointer alone\n'
    '                # is not a valid Smaart-axis movement signal.\n')
p.write_text(s,encoding='utf-8')
print('V834_NATIVE_VERIFIED_ONLY_APPLIED',p)
