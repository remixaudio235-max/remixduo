from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_12_MINI_DYNAMIC_PLOTS_QA\overlay_v7.py")
s=p.read_text(encoding="utf8")
assert "RemiX Signal V8.11" in s
s=s.replace("RemiX Signal V8.11","RemiX Signal V8.12")
s=s.replace("SMAART · V8.11","SMAART · V8.12")
s=s.replace("from plot_geometry_v7 import locate_plots",
            "from plot_geometry_v7 import locate_plots\nfrom plot_role_v812 import locate_role_plots")
assert s.count("self.setFixedSize(205,463)")==1
s=s.replace("self.setFixedSize(205,463)","self.setFixedSize(205,330)")
assert s.count("        layout.addWidget(self.tabs,1)")==1
s=s.replace("        layout.addWidget(self.tabs,1)",
            """        # V8.12 minimal UI: old Trục/Info panels remain in Qt memory
        # for existing axis-calibration and smoothing callbacks, but are
        # not shown or clickable. No tab control is added to the layout.
        self.tabs.hide()""")
# Correct panel placement preserves Smaart right sidebar positioning.
needle="self.plot_future=self.pool.submit(locate_plots,hwnd)"
assert s.count(needle)==1
s=s.replace(needle,"self.plot_future=self.pool.submit(locate_role_plots,hwnd)")
# A failed/unknown detection must hide SUM rather than retain old assumed mapping.
# Previous code already emits None on worker failure.
# For a role swap reset spatial state so Phase Y doesn't consume Mag Y pan fit.
needle='''        if changed:
            print("V7_PLOT_RECT",hwnd,layout.phase,layout.mag,flush=True)'''
assert s.count(needle)==1
s=s.replace(needle,'''        if changed:
            print("V812_ROLE_GEOMETRY",hwnd,layout.phase,layout.mag,flush=True)
            self.axis_drag=None
            self._axis_was_pressed=False
            self._mag_offset_key=None
            self._mag_anchor_verified=False
            # Existing spatially bound async samples are rejected through
            # their old rect keys; never reuse axis displacement across
            # a swapped Mag/Phase view.''')
# Current unknown role results returned None; older logic hides, correct.
s=s.replace("if now-self.plot_requested>2.0 and (","if now-self.plot_requested>0.9 and (")
p.write_text(s,encoding="utf8")
print("V812_MINI_TABS_REMOVED_DYNAMIC_ROLE_MAPPED")
