"""V8.175 real screenshot glyphs + native light/dark Y-grid, fail closed."""
import base64,numpy as np
from PIL import Image,ImageDraw
from plot_role_v812 import detect_plot_roles,PHASE_TEMPLATE,MAG_TEMPLATE
from smaart_native_y_grid_v839 import fit_native_mag_grid
from plot_geometry_v7 import Plots
P="AAAAAAAAAA+EAAAAHwD+YAAAAfAMZgAAAA8Axn48fHjwDGZmbMzHAP5mDuDMcA8GZ+ffwwDAZmYOgDAMBmbszMEAwGZ+fHgQAAAAAAAAAAAAAAAAAAAAAAAAAA=="
M="AAAAAAAAAAAAAAAOGAAAAYAACAP/AOOAAAAZgADAH/AOOAAAABgADAH/APOPH58b2I/Pj/APeZu5mZmJ3dj/ANeBsZmZmJjYx+ANWfsZGZmJjfx+AN2ZsZGZmJjYA8AN2bn5GZnZ3dg8AN2fj5GZz4/PgYAAAAAYAAAAAAAYAAAAO4AAAAAAAAAAAAHgAAAAAAAA"
def mask(s,w):return np.unpackbits(np.frombuffer(base64.b64decode(s),dtype=np.uint8))[:14*w].reshape(14,w).astype(bool)
def img_titles(theme="light",reverse=False,real=False):
    bg=245 if theme=="light" else 24
    fg=15 if theme=="light" else 245
    arr=np.full((110,310,3),bg,dtype=np.uint8)
    if real: a,b=mask(P,52),mask(M,84)
    else:
        a=np.asarray(Image.open(PHASE_TEMPLATE).convert("L"))>128
        b=np.asarray(Image.open(MAG_TEMPLATE).convert("L"))>128
    if reverse:a,b=b,a
    for y,pattern in ((0,a),(50,b)):
        h,w=pattern.shape
        arr[y+5:y+5+h,13:13+w][pattern]=fg
    return Image.fromarray(arr),(0,0,300,42),(0,50,300,42)
def test_real_light_native_titles():
    im,top,bottom=img_titles(real=True)
    r=detect_plot_roles(im,top,bottom)
    assert r.role=="PHASE_TOP" and r.upper_phase>.90 and r.lower_mag>.90,r
def test_light_reverse():
    im,top,bottom=img_titles(reverse=True)
    assert detect_plot_roles(im,top,bottom).role=="MAG_TOP"
def test_dark_kept():
    im,top,bottom=img_titles(theme="dark")
    assert detect_plot_roles(im,top,bottom).role=="PHASE_TOP"
def test_blank_fails_closed():
    im=Image.new("RGB",(310,110),"white")
    assert detect_plot_roles(im,(0,0,300,42),(0,50,300,42)).role=="UNKNOWN"
def grid(theme="light",extra_zero=False,missing_zero=False):
    im=Image.new("RGB",(1250,520),(245,245,245) if theme=="light" else (4,4,4))
    d=ImageDraw.Draw(im);x,y,w,h=85,55,1100,420
    g=(229,230,233) if theme=="light" else (60,60,60)
    for iy in range(35,420,35):d.line((x,y+iy,x+w-1,y+iy),fill=g,width=2)
    if not missing_zero:
        d.line((x,y+210,x+w-1,y+210),fill=(30,30,30) if theme=="light" else (215,215,215),width=1)
    if theme=="light":
        d.line((x,y+347,x+w-1,y+347),fill=(157,157,157),width=2)
        if extra_zero:d.line((x,y+290,x+w-1,y+290),fill=(25,25,25),width=1)
    return im,(x,y,w,h),(0,0,1250,520)
def test_light_grid_zero_and_scale():
    im,p,w=grid()
    r=fit_native_mag_grid(im,p,w,3.)
    assert r.accepted,r.reason
    assert abs(r.zero_px-210)<2 and abs(r.px_per_db-35/3)<.1
    assert abs(r.y_max-18)<.2 and abs(r.y_min+18)<.2
def test_dark_grid_kept():
    im,p,w=grid("dark")
    r=fit_native_mag_grid(im,p,w,3.)
    assert r.accepted,r.reason
def test_nonunique_zero_fails_closed():
    im,p,w=grid(extra_zero=True)
    assert not fit_native_mag_grid(im,p,w,3.).accepted
def test_missing_zero_fails_closed():
    im,p,w=grid(missing_zero=True)
    assert not fit_native_mag_grid(im,p,w,3.).accepted
def test_missing_saved_interval_fails_closed():
    im,p,w=grid()
    assert not fit_native_mag_grid(im,p,w,None).accepted
def test_plot_theme_legacy_default():
    assert Plots((1,1,20,20),(1,25,20,20),1.).theme=="dark"
