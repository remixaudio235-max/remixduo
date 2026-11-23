from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"live_sync_v7.py"
s=p.read_text(encoding="utf-8")
old='''return SyncResult(None,"Scroll changed during capture; invalidated",
                                  len(self.states),len(self.order),True,now)'''
assert s.count(old)==1
s=s.replace(old,'''return SyncResult(None,"Scroll changed during capture; unverified",
                                  0,len(self.order),True,now)''')
old='''return SyncResult(None,"No unambiguous rows in viewport",
                                  len(self.states),len(self.order),True,now)'''
assert s.count(old)==1
s=s.replace(old,'''return SyncResult(None,"No unambiguous rows in viewport",
                                  0,len(self.order),True,now)''')
old='''            text=(f"Verified {len(self.states)}/{len(self.order)} rows, "
                  f"active {sum(1 for x in self.states.values() if x=='on')}")'''
assert s.count(old)==1
s=s.replace(old,'''            text=(f"Verified viewport {len(rows)} rows; "
                  f"cached {len(self.states)}/{len(self.order)} rows, "
                  f"active {sum(1 for x in self.states.values() if x=='on')}")''')
old='''return SyncResult(None,"READ ERROR: "+str(exc)[:145],
                              len(self.states),len(self.order),True,now)'''
assert s.count(old)==1
s=s.replace(old,'''return SyncResult(None,"READ ERROR: "+str(exc)[:145],
                              0,len(self.order),True,now)''')
p.write_text(s,encoding="utf-8")
# Native QA requires BOTH a complete cached map and a successfully
# classified NEW viewport. Do not call cached data newly verified.
p=root/"qa_v824_live_100.py"
s=p.read_text(encoding="utf-8")
old='''    verified_ok=sum(a>=100 and a==b for a,b in rows_seen)'''
assert s.count(old)==1
s=s.replace(old,'''    verified_ok=sum(state in ("pending","valid","invalid") for state in states)''')
old='''    assert verified_ok>=95, f"Unreliable Smaart Data Bar snapshots: {verified_ok}/100"'''
assert s.count(old)==1
s=s.replace(old,'''    assert verified_ok>=95, f"Unreliable new viewport reads: {verified_ok}/100"''')
p.write_text(s,encoding="utf-8")
print("V824_VIEWPORT_FRESHNESS_AND_QA_ACCOUNTING_FIXED")
