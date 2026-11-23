"""QA V8.89: Smaart teal TF color is not cyan/green and must not bypass identity."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PIL import Image,ImageDraw
from smaart_native_mag_fit import trace_color_mask
from fir_native_v846 import phase_native_fit
from test_v846_fir_native import source,PHASE,WIN


def test_smaart_teal_pixels_recognized_without_false_cyan_or_olive():
    im=Image.new("RGB",(1500,410),(0,0,0))
    p=ImageDraw.Draw(im)
    p.line([(70,30),(280,90),(530,200),(720,55),(920,260)],fill=(27,224,166),width=3)
    p.line([(70,170),(280,230)],fill=(18,230,15),width=3)
    p.line([(70,310),(280,345)],fill=(0,205,250),width=3)
    teal=trace_color_mask(im,"teal")
    assert np.count_nonzero(teal)>1500
    # Cyan and green masks must not include any point of Smaart teal pixels.
    assert not (teal & trace_color_mask(im,"cyan")).any()
    assert not (teal & trace_color_mask(im,"green")).any()
    assert not (teal & trace_color_mask(im,"red")).any()


def test_native_teal_phase_registration_rejects_wrong_trace_color():
    src,_=source()
    img=Image.new("RGB",(1920,1080),(7,11,15))
    painter=ImageDraw.Draw(img)
    x0,y0,w,h=PHASE
    for f,deg,valid in zip(src.freqs,src.original_phase,src.phase_valid):
        if not valid:continue
        x=w*np.log(f/20.)/np.log(1000.)
        y=((180.-deg)%360.)*h/360.
        if 50<x<w-360 and 1<y<h-2:
            px=int(x0+x);py=int(y0+y)
            painter.ellipse((px-2,py-2,px+2,py+2),fill=(27,224,166))
    phase=phase_native_fit(img,PHASE,WIN,src,"teal")
    assert phase is not None and phase[1]>=.78
    assert phase_native_fit(img,PHASE,WIN,src,"green") is None
    assert phase_native_fit(img,PHASE,WIN,src,"cyan") is None


def test_fir_color_selection_includes_teal():
    import inspect
    from smaart_eq_color_select import choose_color_fit
    src=inspect.getsource(choose_color_fit)
    assert '"teal"' in src
