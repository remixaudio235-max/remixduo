"""V8.111: fresh Smaart 9 session writes an index.xml with NO trace entries.

Observed 2026-11-11 (new Windows, Smaart Suite 9): Transfer Function\\index.xml
is a <traceTreeScanner> stub listing only the "Session Data" folder, while the
Data Bar already shows 7 new .trf newest-first. archive_order raised
"indexed row IDs incomplete/noncontiguous" and the tick gate never verified.
An empty index must use the existing strict fresh-import fallback.
"""
import os,time
from pathlib import Path
import pytest
from selection_v7 import archive_order

STUB='''<?xml version="1.0" encoding="UTF-8"?>
<traceTreeScanner><map><mapItem path="X"><traceFolderScanner path="X"><index>
<items><item fileName="Session Data"/></items></index></traceFolderScanner>
</mapItem></map></traceTreeScanner>'''


def make(tmp_path,names,offsets):
    tf=tmp_path/"Transfer Function";sd=tf/"Session Data";sd.mkdir(parents=True)
    index=tf/"index.xml";index.write_text(STUB,encoding="utf-8")
    base=time.time()-1000
    os.utime(index,(base,base))
    for name,off in zip(names,offsets):
        p=sd/name;p.write_bytes(b"trf")
        os.utime(p,(base+off,base+off))
    return sd


def test_empty_index_maps_fresh_traces_newest_first(tmp_path):
    sd=make(tmp_path,["TUNNINNGGG-13-1.trf","0 delay-1.trf","SUb P1 rin rin-1.trf"],
            [61,87,178])
    assert [p.name for p in archive_order(sd)]==[
        "SUb P1 rin rin-1.trf","0 delay-1.trf","TUNNINNGGG-13-1.trf"]


def test_empty_index_still_fails_closed_on_old_or_tied_traces(tmp_path):
    sd=make(tmp_path,["a.trf","b.trf"],[0,50])        # a not newer than index
    with pytest.raises(ValueError):archive_order(sd)
    sd2=make(tmp_path/"t",["a.trf","b.trf"],[40,40])  # tied timestamps
    with pytest.raises(ValueError):archive_order(sd2)


def test_empty_index_with_no_traces_is_empty(tmp_path):
    sd=make(tmp_path,[],[])
    assert archive_order(sd)==[]
