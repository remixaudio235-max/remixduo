"""Regression from real native Suite 1366x720 PrintWindow sample.
Reproject whole capture to physical DPIs and classify against stored 21-row
ground truth from an independent 100% DPI read-only QA run.
This is a scale stress replay, NOT a live high-DPI Windows test.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import json
import pytest
from PIL import Image
from types import SimpleNamespace
from full_scan_v7 import _page
from databar_icon_geometry_v8181 import classify_uia_row_gutter
ORIGIN=Path(r"D:\REMIX_DUO_CHECKPOINTS\QA_V8180_R5_RESOLUTION_DPI_QA_20261122\RUN_20261122_CURRENT_AND_MATRIX")
STATES={int(k):v for k,v in json.loads((ORIGIN/"native_suite_readonly_probe.json").read_text(encoding="utf8"))["visible_states"].items()}
REAL=Image.open(ORIGIN/"suite_readonly.png").convert("RGB")
assert REAL.size==(1366,720)
class FakeRow:
    def __init__(self,t,left):
        self.top=t; self.left=left
    def rectangle(self):
        return SimpleNamespace(top=self.top,left=self.left)

@pytest.mark.parametrize("dpi",[96,120,144,168,192])
@pytest.mark.parametrize("resample",[Image.Resampling.NEAREST, Image.Resampling.BICUBIC])
def test_real_native_suite_capture_scaled_all_icon_states(dpi,resample):
    scale=dpi/96.
    im=REAL.resize((round(REAL.width*scale),round(REAL.height*scale)),resample)
    pitch=round(22*scale)
    uia={i:FakeRow(round((163+i*22)*scale),round(9*scale)) for i in range(21)}
    page=_page(im,["trace"]*21,0,round(163*scale),round(163*scale),round(735*scale),
               round(16*scale),row_height=pitch,uia_rows=uia,window_origin=(0,0))
    mismatches={i:(STATES[i],page.get(i)) for i in STATES if page.get(i)!=STATES[i]}
    assert not mismatches,(dpi,resample,mismatches)
