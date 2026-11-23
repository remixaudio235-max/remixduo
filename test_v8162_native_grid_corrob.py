"""V8.162: corroborated native zero dB grid, never an unverified saved axis."""
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
import mag_sum_native_v826 as native
from smaart_native_y_grid_v839 import saved_mag_grid_interval
from test_v839_native_mag_grid import build_grid, RECT,WINDOW


def xml_file(tmp_path,rows):
    root=ET.Element("config")
    for name,visible,step in rows:
        node=ET.SubElement(root,"plotProperties")
        ET.SubElement(node,"name").text=name
        ET.SubElement(node,"visible").text=str(visible)
        ET.SubElement(node,"ordinateGridInterval").text=str(step)
    f=tmp_path/"SmaartConfig.xml"
    ET.ElementTree(root).write(f,encoding="utf-8")
    return f


def test_inactive_consensus_only_opt_in_and_multiple_agree(tmp_path):
    f=xml_file(tmp_path,[("Magnitude1",0,3),("Magnitude2",0,3)])
    assert saved_mag_grid_interval(f) is None
    assert saved_mag_grid_interval(f,allow_inactive_consensus=True)==3.


@pytest.mark.parametrize("rows",[
    [("Magnitude1",0,3)],
    [("Magnitude1",0,3),("Magnitude2",0,6)],
    [("Magnitude1",1,3),("Magnitude2",1,6)]])
def test_inconsistent_or_insufficient_grid_consensus_is_rejected(tmp_path,rows):
    f=xml_file(tmp_path,rows)
    assert saved_mag_grid_interval(f,allow_inactive_consensus=True) is None


def fake_source(*args,scale=12.,score=.99,accepted=True):
    height=RECT[3]
    return native.SumMagAxis(accepted,-8.0,(-8.0+height/scale),score,1,
                             "magenta","native source fit",228)


def test_native_grid_with_independent_curve_scale_is_accepted(monkeypatch):
    img=build_grid()
    monkeypatch.setattr(native,"capture_native_window",lambda hwnd:(img,WINDOW))
    monkeypatch.setattr(native,"saved_mag_grid_interval",
                        lambda **kw:3. if kw.get("allow_inactive_consensus") else None)
    monkeypatch.setattr(native,"axis_from_native_image",
                        lambda *args:fake_source(scale=34.5/3.))
    result=native.capture_sum_mag_axis(123,RECT,("a","b"))
    assert result.accepted and result.color=="GRID" and result.source_index==-1
    assert abs(result.y_max-14.87)<.45 and abs(result.y_min+20.96)<.45
    assert "corroborated" in result.reason


def test_grid_contradiction_must_fail_closed_even_if_source_fit_accepts(monkeypatch):
    img=build_grid()
    monkeypatch.setattr(native,"capture_native_window",lambda hwnd:(img,WINDOW))
    monkeypatch.setattr(native,"saved_mag_grid_interval",
                        lambda **kw:3. if kw.get("allow_inactive_consensus") else None)
    monkeypatch.setattr(native,"axis_from_native_image",
                        lambda *args:fake_source(scale=7.))
    result=native.capture_sum_mag_axis(123,RECT,("a","b"))
    assert not result.accepted
    assert "not corroborated" in result.reason


@pytest.mark.parametrize("source",[
    native.SumMagAxis(False,reason="no visible source"),
    native.SumMagAxis(True,-20.,16.,.99,-1,"GRID","spoofed",228)])
def test_no_independent_source_evidence_never_passes(monkeypatch,source):
    img=build_grid()
    monkeypatch.setattr(native,"capture_native_window",lambda hwnd:(img,WINDOW))
    monkeypatch.setattr(native,"saved_mag_grid_interval",
                        lambda **kw:3. if kw.get("allow_inactive_consensus") else None)
    monkeypatch.setattr(native,"axis_from_native_image",lambda *args:source)
    assert not native.capture_sum_mag_axis(123,RECT,("a","b")).accepted
