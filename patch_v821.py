from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_21_AUTO_PHASE_TOP_GREEN_QA\overlay_v7.py")
s=p.read_text(encoding="utf-8")
needle='''            QPushButton#run {background:#FF922A;color:#14151A;
                             font-weight:800;font-size:12px;
                             border:0;border-radius:8px;
                             min-height:32px;}'''
assert s.count(needle)==1, "Old Auto Phase button palette missing"
s=s.replace(needle,'''             QPushButton#run {background:#39FF14;color:#041006;
                             font-weight:800;font-size:12px;
                             border:1px solid #78FF66;border-radius:8px;
                             min-height:32px;}''')
needle='''            QPushButton#run:hover {background:#FFAF55;}
            QPushButton#run:pressed {background:#DF7420;}'''
assert s.count(needle)==1
s=s.replace(needle,'''            QPushButton#run:hover {background:#65FF48;}
            QPushButton#run:pressed {background:#29D70B;}''')
needle="        layout.setContentsMargins(4,6,4,5)"
assert s.count(needle)==1
s=s.replace(needle,"        layout.setContentsMargins(4,2,4,5)")
needle='''        self.solve=QPushButton("AUTO PHASE")
        self.solve.setObjectName("run")
        self.solve.clicked.connect(self.align)
        control.addWidget(self.solve)

        candidates_card=make_card'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.solve=QPushButton("AUTO PHASE")
        self.solve.setObjectName("run")
        self.solve.clicked.connect(self.align)
        control.addWidget(self.solve)
        # Place the large AUTO PHASE action first, directly below the
        # dock heading, before TRACE DANG CHON. Keep the actual control
        # card, handlers and trace/candidate states untouched.
        phase_action_card=control.parentWidget()
        assert phase_action_card is not None
        layout.removeWidget(phase_action_card)
        layout.insertWidget(1,phase_action_card)

        candidates_card=make_card''')
# explicit version, no algorithm changes
s=s.replace("V8.20","V8.21")
p.write_text(s,encoding="utf-8")

p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_21_AUTO_PHASE_TOP_GREEN_QA\signal_tools_gui_v813.py")
s=p.read_text(encoding="utf-8")
needle='''          QLabel#dockHeading {background:#192C3C;color:#F2B15D;
              font:bold 10px 'Segoe UI';padding:3px 8px;}'''
assert s.count(needle)==1
s=s.replace(needle,'''          QLabel#dockHeading {background:#132B20;color:#71FF55;
              font:bold 10px 'Segoe UI';padding:3px 8px;}''')
needle='''        self.heading.setText({"phase":"AUTO PHASE","eq":"AUTO EQ",
                              "fir":"FIR"}[mode])'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.heading.setText({"phase":"AUTO PHASE","eq":"AUTO EQ",
                              "fir":"FIR"}[mode])
        self.heading.setStyleSheet(
            "background:#132B20;color:#71FF55;" if mode=="phase" else
            "background:#192C3C;color:#67DFF3;")''')
needle='''            self.menu_button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:21px;"
                "background:#FF9D35;color:#101923;border:0;border-radius:4px;")'''
assert s.count(needle)==1
s=s.replace(needle,'''            self.menu_button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:21px;"
                +("background:#39FF14;color:#041006;" if self.active=="phase"
                  else "background:#FF9D35;color:#101923;")
                +"border:0;border-radius:4px;")''')
needle='''                +("background:#FF9D35;color:#121820;border:0;"
                  "border-radius:4px;" if name==self.active else
                  "background:#18364A;color:#B6D8E4;"
                  "border:1px solid #315169;border-radius:4px;"))'''
assert s.count(needle)==1
s=s.replace(needle,'''                +( ("background:#39FF14;color:#041006;border:1px solid #76FF61;"
                    "border-radius:4px;" if name=="phase" else
                    "background:#FF9D35;color:#121820;border:0;"
                    "border-radius:4px;") if name==self.active else
                  "background:#18364A;color:#B6D8E4;"
                  "border:1px solid #315169;border-radius:4px;"))''')
# restore menu style on mode switch in narrow window
needle='''        self.active=mode
        if mode!="eq":'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.active=mode
        if self._toolbar_mode=="menu":
            self.menu_button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:21px;"
                +("background:#39FF14;color:#041006;" if mode=="phase"
                  else "background:#FF9D35;color:#101923;")
                +"border:0;border-radius:4px;")
        if mode!="eq":''')
s=s.replace("V8.20","V8.21")
p.write_text(s,encoding="utf-8")
print("V821_TOP_ACTION_AND_LIME_GREEN_PATCH_OK")
