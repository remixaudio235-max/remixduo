"""R62 reproducer: Smaart 8 1680x1050 known native plot X profile.
No audio, Smaart settings, or on-screen actions. PNG from R61 installed EXE QA.
"""
import numpy as np
from pathlib import Path
from PIL import Image
import pytest
from smaart8_plot_profile_v868 import detect_v8_profile,detect_v8_roles
from mag_sum_native_v826 import _smaart8_native_source_axis
from smaart_runtime_paths_v868 import trace_directory
from trf_core import read_trf

ROOT=Path(r"D:\R60_SMAART8_SUM_RESTORE_QA")
FRAME=ROOT/"R61_SCREEN_MATRIX"/"1680x1050_Auto_Phase.png"
def _sources():
 d=trace_directory(8)
 if d is None:pytest.skip("No Smaart8 saved TF data available")
 paths=[d/"full 30 bien.trf",d/"SUB SKY 2.trf"]
 if not all(x.exists() for x in paths):pytest.skip("Original exact TRF pair unavailable")
 return [read_trf(x) for x in paths]

def test_r62_native1680_exact_measured_plot_roles():
 if not FRAME.exists():pytest.skip("R61 live source screenshot missing")
 im=Image.open(FRAME)
 assert im.size==(1680,1050)
 phase,mag=detect_v8_profile(im)
 assert phase==(215,81,1234,405)
 assert mag==(215,508,1234,405)
 assert detect_v8_roles(im,phase,mag)=="PHASE_TOP"

def test_r62_real1680_y_axis_recovers_from_native_trace_only():
 if not FRAME.exists():pytest.skip("R61 live screenshot missing")
 im=Image.open(FRAME)
 traces=_sources()
 mag=detect_v8_profile(im)[1]
 proof=_smaart8_native_source_axis(im,mag,(0,0,1680,1050),traces)
 assert proof.accepted,proof.reason
 assert proof.source_index==0
 assert proof.color=="green"
 assert proof.score>=0.9
 assert proof.x_min==20 and proof.x_max==20000
 assert -22.0<proof.y_min<-16.0
 assert 16.0<proof.y_max<23.0
 # A source-identity mismatch must fail closed even when the pixels exist.
 wrong=_smaart8_native_source_axis(im,mag,(0,0,1680,1050),[traces[1],traces[1]])
 assert not wrong.accepted

def test_r62_old1680_scaled_x_must_not_prove_axis():
 if not FRAME.exists():pytest.skip("R61 live screenshot missing")
 im=Image.open(FRAME); traces=_sources()
 wrong=(188,508,1290,405)
 old=_smaart8_native_source_axis(im,wrong,(0,0,1680,1050),traces)
 assert not old.accepted

def test_r62_unchanged_1366_profile():
 frame=Path(r"D:\R59_SMAART8_TOP_RIGHT_DOCK_QA\R60_NATIVE_SMAART8_READONLY.png")
 if not frame.exists():pytest.skip("R61 1366 image missing")
 im=Image.open(frame)
 # Verify original profile selection still identifies both correct graphs.
 p=detect_v8_profile(im)
 assert p is not None
 assert p[0][0]==215 and p[1][0]==215
 assert p[0][2]==920 and p[1][2]==920
