from pathlib import Path
root=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_5_ASCII_IMPORT_QA')
p=root/'live_sync_v7.py'
s=p.read_text(encoding='utf-8')
needle='from selection_v7 import archive_order'
assert s.count(needle)==1
s=s.replace(needle,'from selection_v7 import archive_order,fresh_unindexed_imports')
needle='''        self.order=order
        self.uia_rows=rows'''
assert s.count(needle)==1
s=s.replace(needle,'''        self.order=order
        self.imports_count=len(fresh_unindexed_imports(self.folder))
        self.uia_rows=rows''')
needle='''            f"FULL SCAN {scan.covered}/{scan.total} in {scan.elapsed_s:.2f}s",
'''
assert s.count(needle)==1
s=s.replace(needle,'''            f"FULL SCAN {scan.covered}/{scan.total} in {scan.elapsed_s:.2f}s"
            + (f" | {self.imports_count} ASCII imports (index pending)"
               if self.imports_count else ""),
''')
needle='''            text=(f"Verified {len(self.states)}/{len(self.order)} rows, "
                  f"active {sum(1 for x in self.states.values() if x=='on')}")'''
assert s.count(needle)==1
s=s.replace(needle,'''            text=(f"Verified {len(self.states)}/{len(self.order)} rows, "
                  f"active {sum(1 for x in self.states.values() if x=='on')}")
            if getattr(self,"imports_count",0):
                text+=f" | {self.imports_count} ASCII imports (index pending)"''')
p.write_text(s,encoding='utf-8')

p=root/'overlay_v7.py'
s=p.read_text(encoding='utf-8')
s=s.replace('RemiX Auto Align V7.4 - Windows QA',
            'RemiX Auto Align V7.5 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V7.4',
            'RemiX  AUTO ALIGN  V7.5')
p.write_text(s,encoding='utf-8')
print('V75_SYNC_AND_UI_TITLE_PATCH_PASS')
