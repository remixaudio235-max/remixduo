"""Surgical V8.28 Phase/Mag Y-follow integration into current V8.27 only."""
from pathlib import Path

src = Path(__file__).with_name("overlay_v7.py")
text = src.read_text(encoding="utf-8-sig")
original = text


def replace_once(old, new):
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Unsafe patch: expected 1 occurrence, found {count}: {old[:85]!r}")
    text = text.replace(old, new)


replace_once(
    "from native_dual_y_v82 import NativeDualFastPan,DualPanResult\n",
    "from native_dual_y_v82 import NativeDualFastPan,DualPanResult\n"
    "from axis_y_sync_v828 import trusted_pan,translated_y_range\n",
)
replace_once(
    "        self.mag_pan_last_log=0.0\n",
    "        self.mag_pan_last_log=0.0\n"
    "        self._phase_pan_last_frame=0.0\n"
    "        self._mag_pan_last_frame=0.0\n"
    "        self._phase_axis_generation=0\n"
    "        self._mag_axis_generation=0\n",
)
replace_once(
    "        expected=(self.plot_hwnd,self.plot_layout.phase,\n"
    "                  tuple(self.current_pair or ()),self._reference_index())\n"
    "        if key!=expected or result is None:return\n",
    "        expected=(self.plot_hwnd,self.plot_layout.phase,\n"
    "                  tuple(self.current_pair or ()),self._reference_index(),\n"
    "                  self._phase_axis_generation)\n"
    "        if key!=expected or result is None:return\n",
)
replace_once(
    "        key=(target.hwnd,self.plot_layout.phase,\n"
    "             tuple(self.current_pair or ()),self._reference_index())\n"
    "        current_top=float(self.graph_phase.y_max)\n",
    "        key=(target.hwnd,self.plot_layout.phase,\n"
    "             tuple(self.current_pair or ()),self._reference_index(),\n"
    "             self._phase_axis_generation)\n"
    "        current_top=float(self.graph_phase.y_max)\n",
)
replace_once(
    "                tuple(t.file_mtime_ns for t in self.current_traces))\n",
    "                tuple(t.file_mtime_ns for t in self.current_traces),\n"
    "                self._mag_axis_generation)\n",
)
replace_once(
    "        if not fit.accepted:\n"
    "            self.mag_anchor_failed+=1\n"
    "            self._mag_anchor_verified=False\n"
    "            self.graph_mag.native_axis_ready=False\n"
    "            self.graph_mag.update()\n"
    "            if self.mag_anchor_failed<=3:\n",
    "        if not fit.accepted:\n"
    "            self.mag_anchor_failed+=1\n"
    "            # One ambiguous frame must not make a previously calibrated\n"
    "            # SUM Mag disappear while moving the native Smaart Y axis.\n"
    "            if self.mag_anchor_failed>=3 and time.monotonic()-self.mag_pan_last_move>1.1:\n"
    "                self._mag_anchor_verified=False\n"
    "                self.graph_mag.native_axis_ready=False\n"
    "                self.graph_mag.update()\n"
    "            if self.mag_anchor_failed<=3:\n",
)
replace_once(
    "        self.mag_anchor_accepted+=1\n"
    "        self._mag_anchor_verified=True\n",
    "        self.mag_anchor_accepted+=1\n"
    "        self.mag_anchor_failed=0\n"
    "        self._mag_anchor_verified=True\n",
)
start = text.find("    def on_native_mag_pan(self,payload):")
end = text.find("    def _schedule_fast_pan(self,target):", start)
if start < 0 or end < 0 or end < start:
    raise RuntimeError("Cannot locate original Y-follow callbacks")

replacement = '''    def _apply_native_y_delta(self,kind,frame):
        """Viewport-only movement; keep the stored complex TF and SUM unchanged."""
        now=time.monotonic()
        is_mag=kind=="mag"
        stamp_key="_mag_pan_last_frame" if is_mag else "_phase_pan_last_frame"
        previous=float(getattr(self,stamp_key,0.))
        threshold=.90 if is_mag else .85
        if not trusted_pan(frame,now,previous,minimum_confidence=threshold):
            if is_mag:self.mag_pan_rejected+=1
            else:self.pan_rejected+=1
            return
        setattr(self,stamp_key,float(frame.frame_time))
        dy=float(frame.delta_px)
        if abs(dy)<.75:return
        plot_rect=self.plot_layout.mag if is_mag else self.plot_layout.phase
        graph=self.graph_mag if is_mag else self.graph_phase
        try:
            lo,hi,offset=translated_y_range(
                graph.y_min,graph.y_max,plot_rect[3],dy)
        except ValueError:
            if is_mag:self.mag_pan_rejected+=1
            else:self.pan_rejected+=1
            return
        graph.y_min=lo
        graph.y_max=hi
        graph.update()
        if is_mag:
            self.mag_pan_last_move=now
            self.mag_pan_accepted+=1
            self._mag_axis_generation+=1
            spin_time="mag_pan_last_spin"
            min_spin,max_spin=self.mag_min,self.mag_max
        else:
            self.pan_last_move=now
            self.pan_accepted+=1
            self._phase_axis_generation+=1
            spin_time="axis_last_spin"
            min_spin,max_spin=self.phase_min,self.phase_max
        if now-getattr(self,spin_time,0.)>.12:
            setattr(self,spin_time,now)
            min_spin.blockSignals(True)
            max_spin.blockSignals(True)
            try:
                min_spin.setValue(lo)
                max_spin.setValue(hi)
            finally:
                min_spin.blockSignals(False)
                max_spin.blockSignals(False)
        # Native positive pixel translation => both overlay Y axes move down.
        if is_mag:
            if now-self.mag_pan_last_status>.22:
                self.mag_pan_last_status=now
                self.mag_axis_note.setText(
                    f"Mag Y theo Smaart: {dy:+.0f}px / {offset:+.2f}dB | "
                    f"{frame.confidence:.0%}")
            if now-self.mag_pan_last_log>.30:
                self.mag_pan_last_log=now
                print("V828_MAG_Y_FOLLOW",dy,round(offset,3),
                      round(frame.confidence,3),round(hi,2),flush=True)
        else:
            if now-self.axis_last_status>.22:
                self.axis_last_status=now
                self.phase_axis_note.setText(
                    f"Phase Y theo Smaart: {dy:+.0f}px / {offset:+.2f}deg | "
                    f"{frame.confidence:.0%}")
            if now-self.pan_last_log>.25:
                self.pan_last_log=now
                print("V828_PHASE_Y_FOLLOW",dy,round(offset,3),
                      round(frame.confidence,3),round(hi,2),flush=True)

    def on_native_mag_pan(self,payload):
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.mag,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        # No arbitrary Y position before a native trace has been registered.
        if not self._mag_anchor_verified:return
        self._apply_native_y_delta("mag",frame)

    def on_native_fast_pan(self,payload):
        key,frame=payload
        if frame is None or not self.current_sum or not self.plot_layout:
            return
        expected=(self.plot_hwnd,self.plot_layout.phase,
                  tuple(self.current_pair or ()),self._reference_index())
        if key!=expected:return
        self._apply_native_y_delta("phase",frame)

'''
text = text[:start] + replacement + text[end:]
replace_once(
    "            self._mag_offset_key=None\n"
    "            self._mag_anchor_verified=False\n"
    "            self.graph_mag.native_axis_ready=False\n"
    "            # Existing spatially bound async samples are rejected through\n",
    "            self._mag_offset_key=None\n"
    "            self._mag_anchor_verified=False\n"
    "            self.graph_mag.native_axis_ready=False\n"
    "            self._phase_pan_last_frame=0.0\n"
    "            self._mag_pan_last_frame=0.0\n"
    "            self._phase_axis_generation+=1\n"
    "            self._mag_axis_generation+=1\n"
    "            # Existing spatially bound async samples are rejected through\n",
)
if text == original:
    raise RuntimeError("No changes produced")
src.write_text(text, encoding="utf-8")
print("V828_PATCH_OK",src)
