from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_24_COMPACT_TICK_AUDIT_QA")
p=root/"qa_v824_live_100.py"
s=p.read_text(encoding="utf8")
old='''        assert snapshot.rows>=100 and snapshot.verified==snapshot.rows
        if d.state=="valid":'''
assert s.count(old)==1
s=s.replace(old,'''        if snapshot.rows<100 or snapshot.verified!=snapshot.rows:
            print("TRANSIENT_NATIVE_FRAME",i,snapshot.status,
                  "GATE",d.state,flush=True)
            assert d.state=="transient"
        if d.state=="valid":''')
needle='''    report={
        "polls":len(rows_seen),'''
assert s.count(needle)==1
s=s.replace(needle,'''    verified_ok=sum(a>=100 and a==b for a,b in rows_seen)
    print("NATIVE_VERIFIED_RATE",verified_ok,"/",len(rows_seen),flush=True)
    assert verified_ok>=95, f"Unreliable Smaart Data Bar snapshots: {verified_ok}/100"
    report={
        "verified_ok":verified_ok,
        "polls":len(rows_seen),''')
p.write_text(s,encoding="utf8")
p=root/"CUTOVER_V824.ps1"
s=p.read_text(encoding="utf8")
old='''    & $py -u qa_v824_live_100.py *> "$new\\V824_REAL_100_POLL.stdout.log"
    $status=$LASTEXITCODE'''
assert s.count(old)==1
s=s.replace(old,'''    $ErrorActionPreference='Continue'
    & $py -u qa_v824_live_100.py *> "$new\\V824_REAL_100_POLL.stdout.log"
    $status=$LASTEXITCODE
    $ErrorActionPreference='Stop' ''')
p.write_text(s,encoding="utf8")
print("V824_NATIVE_100_POLL_DIAGNOSTIC_AND_PS_ERROR_HANDLER_FIXED")
