from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_7_POSITIVE_DELAY_ROUTE_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
needle='''        self.delay_route_label.setMinimumHeight(25)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.delay_route_label.setMinimumHeight(26)
        self.delay_route_label.setMaximumHeight(42)''')
needle='''        if hasattr(self,"delay_route_label"):
            self.delay_route_label.setText(
                f"TRỄ TRACE {delayed}: +{self.delay.value():.2f} ms"
                f"  |  MỐC TRACE {ref_num}")'''
assert s.count(needle)==1
s=s.replace(needle,'''        if hasattr(self,"delay_route_label"):
            source=self.current_pair if self.current_pair else ()
            name_delayed=(Path(source[delayed-1]).stem[:12]
                          if len(source)==2 else "—")
            name_ref=(Path(source[ref_num-1]).stem[:12]
                      if len(source)==2 else "—")
            self.delay_route_label.setText(
                f"TRỄ T{delayed} ({name_delayed}) +{self.delay.value():.2f}ms"
                f"  |  GIỮ T{ref_num} ({name_ref})")
            self.delay_route_label.setToolTip(
                "Theo mô hình TF: cộng Delay DƯƠNG cho TRACE "
                f"{delayed} ({name_delayed}), giữ nguyên TRACE {ref_num} "
                f"({name_ref}). Chỉ là preview; phải kiểm tra IR/Delay "
                "phần cứng trước khi cài vào DSP.")''')
needle='''        self.pair_label.setText("01  "+Path(record.names[0]).stem+"\\n02  "+Path(record.names[1]).stem)
        self.status.setText("Loading selected pair...")'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.pair_label.setText("01  "+Path(record.names[0]).stem+"\\n02  "+Path(record.names[1]).stem)
        self._update_delay_route_label()
        self.status.setText("Loading selected pair...")''')
p.write_text(s,encoding="utf-8")
print("V87_DELAY_TARGET_NAMES_ADDED")
