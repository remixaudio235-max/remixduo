from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"live_sync_v7.py"
s=p.read_text(encoding="utf-8")
needle="    captured_at:float"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n    active_names:tuple[str,...]|None=None\n    ambiguous:int=0")
needle='''        return SyncResult(self.last_pair,
            f"FULL SCAN {scan.covered}/{scan.total} in {scan.elapsed_s:.2f}s"
            + (f" | {self.imports_count} ASCII imports (index pending)"
               if self.imports_count else ""),
            scan.covered,scan.total,True,time.perf_counter())'''
assert s.count(needle)==1
s=s.replace(needle,'''        active=tuple(str(self.order[i]) for i in range(len(self.order))
                     if self.states.get(i)=="on")
        ambiguous=sum(v not in ("on","off") for v in self.states.values())
        return SyncResult(self.last_pair,
            f"FULL SCAN {scan.covered}/{scan.total} in {scan.elapsed_s:.2f}s"
            + (f" | {self.imports_count} ASCII imports (index pending)"
               if self.imports_count else ""),
            scan.covered,scan.total,True,time.perf_counter(),
            active,ambiguous)''')
needle='''            if pair!=self.last_pair:changed=True
            self.last_pair=pair
            self.last_pos=offset1'''
assert s.count(needle)==1
s=s.replace(needle,'''            if pair!=self.last_pair:changed=True
            self.last_pair=pair
            self.last_pos=offset1''')
needle='''            return SyncResult(pair,text,len(self.states),len(self.order),changed,now)'''
assert s.count(needle)==1
s=s.replace(needle,'''            active=tuple(str(self.order[i]) for i in range(len(self.order))
                         if self.states.get(i)=="on")
            ambiguous=sum(v not in ("on","off") for v in self.states.values())
            return SyncResult(pair,text,len(self.states),len(self.order),
                              changed,now,active,ambiguous)''')
p.write_text(s,encoding="utf8")
print("V824_IMMUTABLE_TICK_SNAPSHOT_PATCHED")
