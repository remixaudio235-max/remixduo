"""V8.38: read-only saved Smaart smoothing must follow *visible* plots.

Phase1 can be hidden while Phase2 is the active plot. Never guess when
simultaneous visible panes disagree on the smoothing value.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

from smaart_smooth_sync_v811 import read_saved_smooth


def _config(tmp_path,panes):
    root=ET.Element("Root")
    for name,visible,smoothing_id in panes:
        prop=ET.SubElement(root,"plotProperties")
        ET.SubElement(prop,"name").text=name
        ET.SubElement(prop,"visible").text=str(int(visible))
        ET.SubElement(prop,"smoothingId").text=str(smoothing_id)
    f=tmp_path/"SmaartConfig.xml"
    ET.ElementTree(root).write(f,encoding="utf-8")
    return f


def test_visible_phase2_and_magnitude1(tmp_path):
    cfg=_config(tmp_path,[
        ("Phase1",0,1),("Magnitude1",1,5),
        ("Phase2",1,5),("Magnitude2",0,1)])
    snap=read_saved_smooth(cfg)
    assert snap is not None
    assert (snap.mag_id,snap.phase_id)==(5,5)
    assert (snap.mag_oct,snap.phase_oct)==(1/6,1/6)
    assert snap.mag_verified and snap.phase_verified


def test_independent_phase_and_mag_values(tmp_path):
    cfg=_config(tmp_path,[
        ("Phase1",1,4),("Magnitude1",0,1),
        ("Phase2",0,6),("Magnitude2",1,6)])
    snap=read_saved_smooth(cfg)
    assert snap and snap.mag_oct==1/3 and snap.phase_oct==1/12
    # V8.153: 1/3 Oct is a supported live display mode for every Auto tool.
    assert snap.mag_verified and snap.phase_verified


def test_verified_id4_maps_to_visible_one_twelfth_octave(tmp_path):
    cfg=_config(tmp_path,[
        ("Phase1",1,5),("Magnitude1",1,4)])
    snap=read_saved_smooth(cfg)
    assert snap and snap.mag_id==4 and snap.mag_oct==1/12
    assert snap.mag_verified and snap.phase_verified


@pytest.mark.parametrize("panes",[
    [("Phase1",1,5),("Phase2",1,4),("Magnitude1",1,5)],
    [("Phase1",0,5),("Magnitude1",1,5)],
    [("Phase2",1,12),("Magnitude2",1,5)],
])
def test_reject_conflict_missing_or_unknown(tmp_path,panes):
    assert read_saved_smooth(_config(tmp_path,panes)) is None


def test_same_id_multiple_visible_panes_is_unambiguous(tmp_path):
    cfg=_config(tmp_path,[
       ("Phase1",1,5),("Phase2",1,5),
       ("Magnitude1",1,5),("Magnitude2",1,5)])
    snap=read_saved_smooth(cfg)
    assert snap and snap.phase_id==snap.mag_id==5
