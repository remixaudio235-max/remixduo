from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_7_POSITIVE_DELAY_ROUTE_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
needle='''        route=route_candidate(results[0])
        # Apply as a nonnegative real delay on the earlier modeled Trace.'''
assert s.count(needle)==1
s=s.replace(needle,'''        route=route_candidate(results[0])
        prior_ref=self._reference_index()
        # Apply as a nonnegative real delay on the earlier modeled Trace.''')
needle='''        self._update_delay_route_label()
        self._mag_offset_key=None
        self._mag_anchor_verified=False
        self.status.setText('''
assert s.count(needle)==1
s=s.replace(needle,'''        self._update_delay_route_label()
        # Re-anchor preview only when a new TF reference is selected.
        # Repeated AUTO ALIGN with the SAME ref must retain the measured
        # visual Mag offset and must not make SUM jump on screen.
        if prior_ref!=route.reference_index:
            self._mag_offset_key=None
            self._mag_anchor_verified=False
        self.status.setText(''')
p.write_text(s,encoding='utf-8')
print('V87_MAG_ANCHOR_STICKY_ON_SAME_REF_FIXED')
