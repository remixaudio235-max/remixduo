"""Smaart8 Light theme: native black glyphs on bright header.
Synthetic Light is a *test image*, never claimed to be user-native capture.
"""
import numpy as np
from PIL import Image
from unittest.mock import patch
from smaart8_plot_profile_v868 import (
    title_template,detect_v8_roles,detect_v8_profile,
    search_role,locate_v8_role_plots,_native_header_theme)

PHASE=(215,114,1474,400)
MAG=(215,538,1474,399)

def theme_scene(theme,background=None):
    assert theme in ("dark","light")
    bg=(10,10,10) if theme=="dark" else (245,245,245)
    fg=(238,238,238) if theme=="dark" else (28,28,28)
    if background is not None:bg=(background,)*3
    arr=np.full((1032,1920,3),bg,dtype=np.uint8)
    for label,rect in (("PHASE",PHASE),("MAG",MAG)):
        t=title_template(label)
        h,w=t.shape;x,y=rect[:2]
        arr[y:y+h,x:x+w]=np.where(t[:,:,None],np.array(fg,dtype=np.uint8),np.array(bg,dtype=np.uint8))
    return Image.fromarray(arr,"RGB")

def test_dark_title_glyphs_unchanged():
    image=theme_scene("dark")
    assert detect_v8_roles(image,PHASE,MAG)=="PHASE_TOP"
    assert detect_v8_profile(image)==(PHASE,MAG)
    assert _native_header_theme(image,PHASE)=="dark"
    assert search_role(image,PHASE,"PHASE")>.90

def test_light_black_title_glyphs_verified():
    image=theme_scene("light")
    assert _native_header_theme(image,PHASE)=="light"
    assert detect_v8_roles(image,PHASE,MAG)=="PHASE_TOP"
    assert detect_v8_profile(image)==(PHASE,MAG)
    assert search_role(image,PHASE,"PHASE")>.90
    assert search_role(image,MAG,"MAG")>.90

def test_light_wrong_titles_and_mid_gray_fail_closed():
    white_blank=Image.new("RGB",(1920,1032),(245,245,245))
    assert detect_v8_profile(white_blank) is None
    gray=Image.new("RGB",(1920,1032),(150,150,150))
    assert detect_v8_profile(gray) is None
    dark=theme_scene("dark")
    bright=theme_scene("light")
    a=np.asarray(dark).copy();b=np.asarray(bright)
    x,y,w,h=MAG
    a[y:y+40,x:x+w]=b[y:y+40,x:x+w]
    assert detect_v8_profile(Image.fromarray(a)) is None

def test_native_role_locator_propagates_light_for_sum_contrast():
    image=theme_scene("light")
    with patch("smaart8_plot_profile_v868.process_smaart_major",return_value=8), \
         patch("smaart8_plot_profile_v868.printwindow_image",return_value=image), \
         patch("smaart8_plot_profile_v868.win32gui.GetWindowRect",return_value=(0,0,1920,1032)), \
         patch("smaart8_plot_profile_v868.locate_plots",return_value=None):
        result=locate_v8_role_plots(12345)
    assert result is not None
    assert result.phase==PHASE and result.mag==MAG
    assert result.theme=="light"
