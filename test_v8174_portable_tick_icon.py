"""V8.174: portable colored-document icon tick detection.

Regression for the Smaart Suite window on DESKTOP-UMDV2S3:
22 visible rows, 2 solid icons without white X, 20 icons with white X.
"""
from PIL import Image, ImageDraw
from selection_v7 import scan_icon_white_cross

def make_icon(rgb,checked,*,fold=True):
    im=Image.new("RGB",(35,30),"white")
    draw=ImageDraw.Draw(im)
    draw.rectangle((9,5,26,24), fill=rgb)
    if fold:
        draw.polygon([(21,5),(26,5),(26,10)],fill="white")
        draw.line((21,5,26,10),fill=tuple(max(0,c//2) for c in rgb),width=1)
    if not checked:
        draw.line((13,10,23,20),fill="white",width=3)
        draw.line((23,10,13,20),fill="white",width=3)
    return im

def test_solid_colored_file_icon_is_on_even_with_white_background():
    for rgb in ((210,24,12),(211,91,4),(25,160,174),(42,55,225)):
        im=make_icon(rgb,True)
        assert scan_icon_white_cross(im,(9,6,24,22))=="on"

def test_white_x_is_off_and_corner_not_counted_as_x():
    for rgb in ((137,51,151),(10,156,64),(220,70,15),(38,98,160)):
        im=make_icon(rgb,False)
        assert scan_icon_white_cross(im,(9,6,24,22))=="off"

def test_smaart_22_rows_two_active():
    colors=[(210+i*3%45,42+i*5%120,85+i*13%160) for i in range(22)]
    actual=[0,15]  # CUONG-15, sup1 1 in user-provided screenshot
    rows=[make_icon(color,i in actual) for i,color in enumerate(colors)]
    states=[scan_icon_white_cross(im,(9,6,24,22)) for im in rows]
    assert states.count("on")==2,states
    assert states.count("off")==20,states
    assert [i for i,state in enumerate(states) if state=="on"]==actual

def test_partial_icon_or_blank_never_claims_a_state():
    icon=make_icon((180,34,80),True)
    assert scan_icon_white_cross(icon,(19,7,34,23))=="unknown"
    white=Image.new("RGB",(35,30),"white")
    assert scan_icon_white_cross(white,(9,6,24,22))=="unknown"
