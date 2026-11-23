"""V8.57 native Smaart green original MAG trace color — safety gates."""
import numpy as np
import pytest
from PIL import Image
from smaart_native_mag_fit import trace_color_mask
import smaart_eq_color_select as palette


@pytest.mark.parametrize("rgb", [(81,134,59),(95,137,58),(62,125,39)])
def test_native_green_pixels_recognized(rgb):
    pixels=np.zeros((85,660,3),dtype=np.uint8)
    pixels[20:40,90:160,:]=rgb
    img=Image.fromarray(pixels,"RGB")
    assert trace_color_mask(img,"green")[25,100]
    for other in ("cyan","blue","red","magenta","gold"):
        assert not trace_color_mask(img,other)[25,100],other


@pytest.mark.parametrize("color,rgb", [
    ("cyan",(38,156,189)),("blue",(28,62,174)),
    ("red",(242,39,25)),("magenta",(174,25,166)),
    ("gold",(206,142,41)),
])
def test_old_colors_remain_separate(color,rgb):
    pixels=np.zeros((85,660,3),dtype=np.uint8)
    pixels[20:40,90:160,:]=rgb
    img=Image.fromarray(pixels,"RGB")
    assert trace_color_mask(img,color)[25,100],color
    assert not trace_color_mask(img,"green")[25,100]


def test_green_color_is_considered_only_if_pixel_fit_is_verified(monkeypatch):
    seen=[]
    class F:
        score=.89
        accepted=False
    def reject(*args,trace_color,**kwargs):
        seen.append(trace_color)
        return F()
    monkeypatch.setattr(palette,"fit_native_mag",reject)
    assert palette.choose_color_fit(None,None,None,None,None,None) is None
    assert seen.count("green")==1
    assert seen.count("teal")==1
    assert set(seen)=={"cyan","teal","blue","red","green","magenta","gold"}
    assert len(seen)==len(set(seen))


def test_ambiguous_green_does_not_override_identity(monkeypatch):
    from types import SimpleNamespace
    def fit(*args,trace_color,**kwargs):
        return SimpleNamespace(score=.89 if trace_color in ("green","red") else .10,
                               accepted=trace_color in ("green","red"))
    monkeypatch.setattr(palette,"fit_native_mag",fit)
    result=palette.choose_color_fit(None,None,None,None,None,None)
    assert result is not None and not result.accepted
