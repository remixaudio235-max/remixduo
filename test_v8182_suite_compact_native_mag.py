"""V8.180 R5.1 regression: 1366x768 Suite Magnitude 888x238 is supported.
Pixel/source/color/grid/identity gates remain separate and must still reject
unsupported or ambiguous data; never certify a cropped plot by size alone.
"""
import numpy as np
from PIL import Image
from smaart_native_mag_fit import NativeMagFrame, fit_native_mag

def _source():
    f=np.geomspace(20, 20000, 230)
    db=4*np.sin(np.log(f)*1.7)+3*np.sin(np.log(f)*4.1)
    return f,db,np.ones_like(f)

def test_compact_suite_native_geometry_is_admitted_but_blank_curve_rejected():
    img=Image.new("RGB",(1366,720),(22,24,27))
    rect=(252,393,888,238);win=(0,0,1366,720)
    assert NativeMagFrame(img,rect,win).valid
    f,db,coh=_source()
    fit=fit_native_mag(img,rect,win,f,db,coh,trace_color="magenta")
    assert not fit.accepted
    assert fit.reason=="magenta REF curve missing"

def test_subminimum_and_out_of_window_plots_remain_rejected():
    img=Image.new("RGB",(1366,720),(22,24,27))
    f,db,coh=_source()
    for rect in ((252,393,819,238),(252,393,888,209),
                 (800,393,888,238),(252,600,888,238)):
        assert not NativeMagFrame(img,rect,(0,0,1366,720)).valid
        fit=fit_native_mag(img,rect,(0,0,1366,720),f,db,coh,trace_color="magenta")
        assert not fit.accepted
        assert fit.reason=="Invalid native Mag plot bounds"
