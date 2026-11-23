"""V8.129: a pink Smaart trace must not also match the "red" colour mask.

Live 2026-11-12 (TUNNINNGGG-13-1, pink ~160,48,112): "red" and "magenta"
both fitted with score 1.0, choose_color_fit rejected the tie and the FIR
preview stayed HOLD forever ("không chạy, không tạo FIR").
"""
import numpy as np
from PIL import Image
from smaart_native_mag_fit import trace_color_mask


def _strip(rgb):
    a=np.zeros((60,400,3),dtype=np.uint8)
    a[25:30,50:350]=rgb
    return Image.fromarray(a)


def test_pink_is_magenta_only():
    for rgb in ((160,48,112),(152,48,104),(165,61,118)):
        im=_strip(rgb)
        assert trace_color_mask(im,"red").sum()==0,rgb
        assert trace_color_mask(im,"magenta").sum()>0,rgb
    # dim anti-aliased pink edge: below the magenta floor, but never "red"
    assert trace_color_mask(_strip((128,32,80)),"red").sum()==0


def test_own_icon_colour_mask_v8130():
    """Live: slate blue find 1,2ms-1 (#6677A8) matched none of 7 masks."""
    a=np.zeros((60,400,3),dtype=np.uint8)
    a[20:25,50:350]=(102,119,168)      # trace on the plot
    a[35:40,50:350]=(224,0,0)          # Smaart red coherence
    a[45:48,50:350]=(60,60,70)         # grid
    im=Image.fromarray(a)
    named=sum(int(trace_color_mask(im,c)[20:25].sum()) for c in
              ("cyan","teal","blue","red","green","magenta","gold"))
    assert named==0                     # the old palette misses it
    own=trace_color_mask(im,"#6677A8")
    assert own[20:25].sum()>0 and own[35:48].sum()==0


def test_hint_colour_is_trusted_first(monkeypatch):
    import smaart_eq_color_select as sel
    calls=[]
    class Fit:
        def __init__(self,ok):self.accepted=ok;self.score=1.
    def fake(image,rect,win,f,db,coh,trace_color,**_geometry):
        calls.append(trace_color)
        return Fit(trace_color in ("#6677A8","red","magenta"))
    monkeypatch.setattr(sel,"fit_native_mag",fake)
    choice=sel.choose_color_fit(None,None,None,None,None,None,hint="#6677A8")
    assert choice.accepted and choice.color=="#6677A8" and calls==["#6677A8"]
    # Without a hint, the red/magenta tie is still rejected (fail closed).
    assert not sel.choose_color_fit(None,None,None,None,None,None).accepted


def test_reds_still_red():
    for rgb in ((224,0,0),(255,40,40),(158,50,13),(200,68,17),(120,21,8)):
        assert trace_color_mask(_strip(rgb),"red").sum()>0,rgb
