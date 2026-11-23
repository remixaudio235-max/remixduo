"""V8.121: Smaart 8 Data Bar ticks from pixels + traceTreeScanner order.

Live 2026-11-12 (Smaart 8.5.2.1): no UIA tree, API V3 cannot report ticks,
poll() always returned "Smaart 8: no verified TRF tick map". Fixture: real
frame with 3 shown traces (left column only kept).
"""
import os,time
from pathlib import Path
from PIL import Image,ImageDraw
import live_sync_v7 as live
from smaart8_databar_v8121 import v8_row_states
from selection_v7 import archive_order

HOST=(0,0,1920,1032)
FIX=Path(__file__).with_name("fixtures")/"smaart8_databar_3on_1920x1032.png"


def test_rows_and_states_from_real_frame():
    rows=v8_row_states(Image.open(FIX),HOST)
    assert [s for *_,s in rows]==["on","on","on"]        # folder icon excluded
    assert all(abs((r[0]-p[0])-22)<=2 for p,r in zip(rows,rows[1:]))


def test_white_cross_icon_reads_off():
    im=Image.open(FIX).convert("RGB")
    d=ImageDraw.Draw(im)
    d.line((27,162,40,179),fill=(255,255,255),width=2)
    d.line((40,162,27,179),fill=(255,255,255),width=2)
    assert [s for *_,s in v8_row_states(im,HOST)]==["on","off","on"]


def test_dark_desaturated_trace_icon_is_not_dropped():
    im=Image.new("RGB",(1920,1040),(20,25,28))
    ImageDraw.Draw(im).rectangle((25,140,42,157),fill=(35,52,35))
    rows=v8_row_states(im,(0,0,1920,1040))
    assert len(rows)==1


def test_short_session_folder_glyph_is_not_a_trace_row():
    im=Image.new("RGB",(1920,1040),(20,25,28))
    draw=ImageDraw.Draw(im)
    draw.rectangle((25,100,42,110),fill=(152,99,5))
    draw.rectangle((25,140,42,157),fill=(35,52,35))
    rows=v8_row_states(im,(0,0,1920,1040))
    assert len(rows)==1
    assert rows[0][0]>=140


def make_session(tmp_path,names_indexed,new=()):
    tf=tmp_path/"Transfer Function";sd=tf/"Session Data";sd.mkdir(parents=True)
    items="".join(f'<item fileName="{n}"/>' for n in names_indexed)
    (tf/"index.xml").write_text(
        f'<traceTreeScanner><map><mapItem path="{sd}"><traceFolderScanner path="{sd}">'
        f'<index><items>{items}</items></index></traceFolderScanner></mapItem></map>'
        f'</traceTreeScanner>',encoding="utf-8")
    base=time.time()-1000
    os.utime(tf/"index.xml",(base,base))
    for k,n in enumerate(names_indexed):
        (sd/n).write_bytes(b"x");os.utime(sd/n,(base-100+k,base-100+k))
    for k,n in enumerate(new):
        (sd/n).write_bytes(b"x");os.utime(sd/n,(base+10+k,base+10+k))
    return sd


def test_tracetreescanner_order_with_new_captures_on_top(tmp_path):
    sd=make_session(tmp_path,["SUB SKY 2.trf","0 delay.trf"],["find 1,2ms.trf","M12aaa.trf"])
    assert [p.name for p in archive_order(sd)]==[
        "M12aaa.trf","find 1,2ms.trf","SUB SKY 2.trf","0 delay.trf"]


def _observer(monkeypatch,tmp_path,frame):
    sd=make_session(tmp_path,["SUB SKY 2.trf","0 delay.trf"],["find 1,2ms.trf"])
    import smaart8_api3_readonly_v868 as api
    monkeypatch.setattr(api,"process_smaart_major",lambda h:8)
    monkeypatch.setattr(live,"printwindow_image",lambda h:frame)
    monkeypatch.setattr(live.win32gui,"GetWindowRect",lambda h:HOST)
    import ctypes
    monkeypatch.setattr(ctypes.windll.user32,"GetDpiForWindow",lambda h:96)
    return live.LiveDataBarV7(sd)


def test_poll_v8_verifies_ticks(monkeypatch,tmp_path):
    obs=_observer(monkeypatch,tmp_path,Image.open(FIX))
    r=obs.poll(77)
    assert r.status.startswith("Verified viewport") and r.verified==r.rows==3
    assert [Path(n).name for n in r.active_names]==["find 1,2ms.trf","SUB SKY 2.trf","0 delay.trf"]


def test_poll_v8_count_mismatch_fails_closed(monkeypatch,tmp_path):
    obs=_observer(monkeypatch,tmp_path,Image.open(FIX))
    (obs.folder/"extra.trf").write_bytes(b"x")          # 4 files, 3 visible rows
    r=obs.poll(77)
    assert r.pair is None and "HOLD" in r.status and not r.status.startswith("Verified")
