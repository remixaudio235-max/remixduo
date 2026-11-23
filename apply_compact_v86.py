from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_6_REMIX_SIGNAL_COMPACT_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
assert 'RemiX Signal V8.5 - Windows QA' in s
s=s.replace('RemiX Signal V8.5 - Windows QA',
            'RemiX Signal V8.6 - Windows QA')
s=s.replace('WINDOWS V8.5','WINDOWS V8.6')
needle='''        self.setFixedSize(402,770)'''
assert s.count(needle)==1
s=s.replace(needle,'''        # V8.6 compact UI: hide presentation rows only. Underlying widgets
        # stay alive so TF, ROI markers and running Auto Align are unchanged.
        self.setFixedSize(402,560)''')
needle='''        hrow.addWidget(readonly)
        layout.addWidget(header)'''
assert s.count(needle)==1
s=s.replace(needle,'''        hrow.addWidget(readonly)
        readonly.hide()  # red circle 1: top-right READ ONLY badge
        layout.addWidget(header)''')
needle='''        trace.addLayout(refrow)
        self.correction_target_label=QLabel('''
assert s.count(needle)==1
s=s.replace(needle,'''        trace.addLayout(refrow)
        # Red circle 2: no REF chooser or annotation in the compact panel.
        # Keep the real QComboBox and its signal alive; default REF is 1.
        self.ref_choice.setCurrentIndex(0)
        for i in range(refrow.count()):
            item=refrow.itemAt(i)
            widget=item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
        self.correction_target_label=QLabel(''')
needle='''        trace.addWidget(self.correction_target_label)

        # PHASE MATCH RESULT'''
assert s.count(needle)==1
s=s.replace(needle,'''        trace.addWidget(self.correction_target_label)
        self.correction_target_label.hide()

        # PHASE MATCH RESULT''')
needle='''        summary.addWidget(self.sum_ref_label)

        # ALIGN CONTROL'''
assert s.count(needle)==1
s=s.replace(needle,'''        summary.addWidget(self.sum_ref_label)
        # Red circle 3: calculations continue even when this card is hidden.
        self.phase_match_card=summary.parentWidget()
        self.phase_match_card.hide()

        # ALIGN CONTROL''')
needle='''        control=make_card("AUTO ALIGN / VÙNG ĐO","03")'''
assert s.count(needle)==1
s=s.replace(needle,'''        control=make_card("AUTO ALIGN / VÙNG ĐO","02")''')
needle='''        control.addLayout(lfrow)
        delayrow=QHBoxLayout()'''
assert s.count(needle)==1
s=s.replace(needle,'''        control.addLayout(lfrow)
        # Red circle 4: LF/HF spinboxes stay connected for ROI marker dragging
        # on Smaart's plot, but the number inputs disappear from this panel.
        self.roi_hint.hide()
        for i in range(lfrow.count()):
            item=lfrow.itemAt(i)
            widget=item.widget() if item is not None else None
            if widget is not None:
                widget.hide()
        delayrow=QHBoxLayout()''')
needle='''        candidates_card=make_card("TOP 3 PHƯƠNG ÁN","04")'''
assert s.count(needle)==1
s=s.replace(needle,'''        candidates_card=make_card("TOP 3 PHƯƠNG ÁN","03")''')
needle='''        layout.addWidget(self.status)
        self.events=Events()'''
assert s.count(needle)==1
s=s.replace(needle,'''        layout.addWidget(self.status)
        self.status.hide()  # red circle 5: bottom status/footer
        self.events=Events()''')
p.write_text(s,encoding='utf-8')
print('V86_COMPACT_UI_PATCH_OK')
