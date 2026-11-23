from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf8")
needle="from live_sync_v7 import LiveDataBarV7, SyncResult"
assert s.count(needle)==1
s=s.replace(needle,needle+"\nfrom stable_ticks_v824 import StableTickGate")
needle='''        self._selection_last_status="Awaiting verified Data Bar ticks"'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        self.tick_gate=StableTickGate(required=3)
        self._selection_quality="transient"''')
import re
s,n=re.subn(r"(QFrame#panelCard[^\n]*\n\s*border-radius:)10px;",
            r"\g<1>7px;",s,count=1)
assert n==1, "QFrame panel card CSS not found"
assert s.count("padding:3px 6px;min-height:40px;}")==1
s=s.replace("padding:3px 6px;min-height:40px;}",
            "padding:1px 5px;min-height:30px;}",1)
assert s.count("min-height:32px;}")==1
s=s.replace("min-height:32px;}","min-height:29px;}",1)
needle='''        layout.setSpacing(4)'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.setSpacing(2)''')
needle='''            col.setContentsMargins(6,5,6,5)
            col.setSpacing(3)'''
assert s.count(needle)==1
s=s.replace(needle,'''            col.setContentsMargins(5,3,5,3)
            col.setSpacing(2)''')
needle='''                col.setContentsMargins(6,3,6,3)'''
assert s.count(needle)==1
s=s.replace(needle,'''                col.setContentsMargins(5,2,5,2)''')
needle='''        self.trace_grid.setVerticalSpacing(2)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.trace_grid.setVerticalSpacing(0)''')
needle='''                "color:#F5FDFF;font:bold 12px 'Segoe UI';"
                "padding-top:2px;")'''
assert s.count(needle)==1
s=s.replace(needle,'''                "color:#F5FDFF;font:bold 10px 'Segoe UI';"
                "padding-top:0px;")''')
needle='''            name.setMinimumHeight(22)'''
assert s.count(needle)==1
s=s.replace(needle,'''            name.setMinimumHeight(16)
            name.setMaximumHeight(18)''')
needle='''            result.setMinimumHeight(25)'''
assert s.count(needle)==1
s=s.replace(needle,'''            result.setMinimumHeight(15)
            result.setMaximumHeight(17)''')
needle='''        self.solve.clicked.connect(self.align)
        control.addWidget(self.solve)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.solve.clicked.connect(self.align)
        self.solve.setFixedHeight(30)
        control.addWidget(self.solve)''')
assert s.count("        self.candidates=[]")==1
s=s.replace("        self.candidates=[]",
            "        self.candidate_card=candidates_card.parentWidget()\n"
            "        self.candidates=[]",1)
needle='''            button.setFixedHeight(44)'''
assert s.count(needle)==1
s=s.replace(needle,'''            button.setFixedHeight(34)''')
needle='''    def align(self):
        if not self.current_traces:'''
assert s.count(needle)==1
s=s.replace(needle,'''    def align(self):
        if not self._selection_verified:
            self.status.setText("Chưa xác minh ổn định 2 Trace được tick")
            return
        if not self.current_traces:''')
start=s.index("    def found(self,result):")
end=s.index("    def should_poll_selection(self,target):",start)
new='''    def _set_tick_presentation(self,valid:bool):
        self._selection_verified=bool(valid)
        self.solve.setEnabled(bool(valid and self.current_traces))
        self.candidate_card.setVisible(bool(valid))
        for widget in (*self.trace_name_labels,*self.trace_compact_result):
            widget.setVisible(bool(valid))
        if not valid:
            self.last_solve=None
            self._clear_candidate_buttons()
        self.refresh_visibility()

    def found(self,result):
        # Worker-owned tick classification is captured as an immutable
        # snapshot; UI must not inspect mutable observer.states after worker
        # already started a newer screenshot. Legacy tests may omit the
        # snapshot, in which case a safe fallback reads the cached map.
        if isinstance(result,SyncResult):
            names=result.active_names
            ambiguous=result.ambiguous
            if names is None:
                names=tuple(
                    str(self.observer.order[i])
                    for i,state in sorted(self.observer.states.items())
                    if state=="on" and 0<=i<len(self.observer.order))
                ambiguous+=sum(state not in ("on","off")
                               for state in self.observer.states.values())
        else:
            names=()
            ambiguous=1
        decision=self.tick_gate.evaluate(result,names,ambiguous)
        self._selection_quality=decision.state
        self._selection_last_status=decision.reason
        if decision.state in ("transient","pending"):
            self._set_tick_presentation(False)
            self.selection_warning.setText(
                ("Đang kiểm tra Trace..." if decision.state=="transient" else
                 f"Xác minh tick {decision.stable}/3"))
            self.selection_warning.setToolTip(decision.reason)
            self.selection_warning.show()
            return
        if decision.state=="invalid":
            if self.controller.last_pair:
                self.controller.invalidate("Verified active count != 2")
            self._set_tick_presentation(False)
            count=decision.count or 0
            self.selection_warning.setText(
                f"Đang bật {count} Trace — cần đúng 2")
            self.selection_warning.setToolTip(
                "Trace bật: "+", ".join(Path(n).stem for n in names))
            self.selection_warning.show()
            return
        # Pair can be committed ONLY after three matching complete scans.
        self.selection_warning.hide()
        if decision.changed or self.controller.last_pair!=decision.pair:
            self.controller.apply(decision.pair,"Win UIA tick stable 3/3")
        self._set_tick_presentation(True)
        if self.current_traces:self.solve.setEnabled(True)
        self.status.setText("Trace verified, stable 3/3")

'''
s=s[:start]+new+s[end:]
# When async .trf pair loaded, update enabled solve.
needle='''        self.recalc()
        print("V7_SUM_RENDER_READY"'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.recalc()
        self.solve.setEnabled(bool(self._selection_verified))
        print("V7_SUM_RENDER_READY"''')
s=s.replace("V8.23","V8.24")
p.write_text(s,encoding="utf8")

p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf8")
needle='''        self.page_heights={"phase":400,"eq":555,"fir":475}'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.page_heights={"phase":316,"eq":555,"fir":475}''')
needle='''        self._panel_mode=rects.panel_mode
        self.dock.apply_rect(rects.panel)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._panel_mode=rects.panel_mode
        px,py,pw,ph=rects.panel
        if self.active=="phase":
            # Compact phase UI takes only as much Smaart side-column space
            # as needed. Invalid tick selection collapses the Top 3 card.
            compact=335 if self.engine._selection_verified else 195
            ph=min(ph,compact)
        self.dock.apply_rect((px,py,pw,ph))''')
s=s.replace("V8.23","V8.24")
p.write_text(s,encoding="utf8")
print("V824_COMPACT_UI_STATE_GATE_PATCH_PASS")
