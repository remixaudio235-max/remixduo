"""Smaart pure-red original trace must drive Mag; green SUM must not."""
import numpy as np
from PIL import Image,ImageDraw
from native_fast_pan_v81 import colored_profiles,infer_pan


def render(shift):
    im=Image.new('RGB',(440,300),(0,0,0))
    draw=ImageDraw.Draw(im)
    x=np.arange(20,420,dtype=float)
    y=110+shift+18*np.sin(x/41)+7*np.sin(x/13)
    draw.line(list(zip(x.astype(int),y.astype(int))),fill=(255,0,0),width=2)
    # A stationary green RemiX SUM must NOT be mistaken for Smaart.
    green=145+14*np.cos(x/20)
    draw.line(list(zip(x.astype(int),green.astype(int))),
              fill=(57,255,20),width=3)
    return im


def test_pure_red_smaart_mag_30px_movement():
    prev,n1=colored_profiles(render(0))
    nxt,n2=colored_profiles(render(30))
    assert n1>500 and n2>500
    result=infer_pan(prev,nxt)
    assert result.valid,result
    assert abs(result.delta_px-30)<=1,result
    assert result.confidence>.86,result


def test_only_green_sum_is_rejected():
    im=Image.new('RGB',(440,300),(0,0,0))
    d=ImageDraw.Draw(im)
    d.line([(0,80),(440,140)],fill=(57,255,20),width=3)
    _,native_count=colored_profiles(im)
    assert native_count==0
