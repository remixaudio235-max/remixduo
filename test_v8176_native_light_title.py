"""Real Suite light native screenshot + synthetic dark/unknown role proof."""
import sys,numpy as np,pytest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from smaart_mag_plot_detector import detect_magnitude_rect,TITLE
from smaart_native_mag_fit import fit_native_mag
from native_eq_mag_v06 import MagSource,native_fit_worker
from smaart_runtime_paths_v868 import trace_directory
from trf_core import read_trf
from types import SimpleNamespace
CAPTURE=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\QA_RELEASE_GATE_20261120\SUITE_EQ_NATIVE_SINGLE_TRACE.png")
PH=(252,112,1442,417);MAG=(252,572,1442,416);RECT=(0,0,1920,1032)
def test_smaart_suite_light_real_native_role_and_mag_fit():
    im=Image.open(CAPTURE).convert("RGB")
    detected=detect_magnitude_rect(im,RECT,(PH,MAG))
    assert detected is not None
    assert detected[0]==MAG and detected[1]>.95,detected
    t=read_trf(trace_directory(9)/"TUNNINNGGG-13-1.trf")
    db=20*np.log10(np.maximum(abs(t.h),1e-16))
    match=fit_native_mag(im,MAG,RECT,t.hz,db,t.coherence,trace_color="magenta")
    assert match.accepted and match.score>.85 and match.bins>100,match
def _glyph_image(bg,ink):
    ar=np.full((1032,1920,3),bg,dtype=np.uint8)
    with np.load(TITLE) as f:
        phase=f["phase"].astype(bool); mag=f["mag"].astype(bool)
    for x,y,m in ((PH[0],PH[1],phase),(MAG[0],MAG[1],mag)):
        ar[y:y+24,x:x+110][m]=ink
    return Image.fromarray(ar)
def test_legacy_dark_not_regressed():
    im=_glyph_image(20,245)
    d=detect_magnitude_rect(im,RECT,(PH,MAG))
    assert d and d[0]==MAG and d[1]>.97,d
def test_unknown_midtone_fails_closed():
    im=_glyph_image(151,20)
    assert detect_magnitude_rect(im,RECT,(PH,MAG)) is None
def test_full_native_mag_eq_worker_real_light_pixel_image(monkeypatch):
    import native_eq_mag_v06 as module
    import smaart8_api3_readonly_v868 as edition
    im=Image.open(CAPTURE).convert("RGB")
    t=read_trf(trace_directory(9)/"TUNNINNGGG-13-1.trf")
    db=20*np.log10(np.maximum(abs(t.h),1e-16))
    source=MagSource(revision=42,source_index=0,freqs=t.hz,original_db=db,
        after_db=db,coh=t.coherence,peqs=tuple(),source_name="TUNNINNGGG-13-1",
        name="TUNNINNGGG-13-1",source_identity="qa-immutable-real-trf",
        fs=48000,display_smooth_oct=0.)
    monkeypatch.setattr(module,"capture_native_window",lambda h:(im,RECT))
    monkeypatch.setattr(module,"locate_role_plots",
        lambda h:SimpleNamespace(phase=PH,mag=MAG))
    monkeypatch.setattr(edition,"process_smaart_major",lambda h:9)
    monkeypatch.setattr(module.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(module.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(module.win32gui,"GetWindowRect",lambda h:RECT)
    frame=native_fit_worker(98765,source,role_hint=(PH,MAG))
    assert frame is not None and frame.identity_verified,frame
    assert frame.color=="magenta" and frame.fit.score>.85,frame
    assert frame.source_identity==source.source_identity and frame.plot==MAG
