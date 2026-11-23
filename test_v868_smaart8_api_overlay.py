"""Smaart 8 read-only API3 and three-panel role QA."""
from unittest.mock import patch
import json
import numpy as np
from PIL import Image
import pytest
from plot_geometry_v7 import choose_canvas_pair
from smaart8_api3_readonly_v868 import read_only_query,probe_api_v3
from smaart8_plot_profile_v868 import (title_template,detect_v8_roles,detect_v8_profile,
                                        search_role)

class FakeSocket:
    def __init__(self,reply):
        self.sent=[]
        self.reply=reply
        self.closed=False
    def send(self,value):self.sent.append(json.loads(value))
    def recv(self):return json.dumps(self.reply)
    def close(self):self.closed=True

def test_api3_only_whitelisted_get_and_no_commands():
    sock=FakeSocket({"sequenceNumber":1,"response":{"server":"Smaart8","authenticationRequired":False}})
    reply=read_only_query(sock)
    assert reply["response"]["server"]=="Smaart8"
    assert sock.sent==[{"sequenceNumber":1,"action":"get"}]
    with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=9):
        result=probe_api_v3(123)
        assert not result.ok and result.status=="NOT_SMAART_8"

def test_api3_rejects_password_required_or_wrong_host():
    pytest.importorskip("websocket",reason="optional Smaart 8 API3 client not installed")
    with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=8):
        with patch("websocket.create_connection") as factory:
            socket=FakeSocket({"sequenceNumber":1,"response":{"authenticationRequired":True}})
            factory.return_value=socket
            result=probe_api_v3(12)
            assert not result.ok and result.status=="AUTH_REQUIRED"
            assert socket.closed and socket.sent==[{"sequenceNumber":1,"action":"get"}]
        result=probe_api_v3(12,host="192.168.0.1")
        assert not result.ok and result.status=="REMOTE_HOST_DISABLED"
    with pytest.raises(ValueError):
        read_only_query(FakeSocket({"sequenceNumber":40,"response":{}}))

def scene(order=("PHASE","MAG")):
    # Original screenshot x=1920, native Lin top, Phase/Mag below it.
    image=Image.new("RGB",(1920,1080),(10,10,10))
    canvas=np.asarray(image).copy()
    top=(215,287,1470,313)
    bottom=(215,625,1470,315)
    line=(215,113,1470,150)
    for role,rect in (("LIN",line),(order[0],top),(order[1],bottom)):
        mask=title_template(role)
        h,w=mask.shape
        x,y=rect[:2]
        y+=4
        x+=7
        canvas[y:y+h,x:x+w]=np.where(mask[:,:,None],(238,238,238),(10,10,10))
    return Image.fromarray(canvas),top,bottom,line

def test_three_panel_v8_role_binding_never_uses_lin():
    image,phase,mag,lin=scene()
    window=(0,0,1920,1080)
    chosen=choose_canvas_pair([
        (lin[0],lin[1],lin[0]+lin[2],lin[1]+lin[3]),
        (phase[0],phase[1],phase[0]+phase[2],phase[1]+phase[3]),
        (mag[0],mag[1],mag[0]+mag[2],mag[1]+mag[3])],window)
    assert chosen is not None
    upper,lower=chosen
    assert upper[1]>lin[1]+lin[3]
    assert lower[1]>upper[1]+upper[3]
    assert detect_v8_roles(image,phase,mag)=="PHASE_TOP"

def test_reversed_layout_and_empty_title_fail_closed():
    image,a,b,_=scene(("MAG","PHASE"))
    assert detect_v8_roles(image,a,b)=="MAG_TOP"
    assert detect_v8_roles(Image.new("RGB",(1920,1080),(10,10,10)),a,b) is None
    assert detect_v8_roles(image,(160,287,1470,313),b) is None


def test_native_two_plot_v8_profile_exposes_phase_and_mag_for_lf_hf():
    image=Image.new("RGB",(1920,1032),(10,10,10))
    canvas=np.asarray(image).copy()
    phase=(215,114,1474,400);mag=(215,538,1474,399)
    for role,rect in (("PHASE",phase),("MAG",mag)):
        mask=title_template(role);h,w=mask.shape;x,y=rect[:2]
        canvas[y:y+h,x:x+w]=np.where(mask[:,:,None],(238,238,238),(10,10,10))
    assert detect_v8_profile(Image.fromarray(canvas))==(phase,mag)


def test_v8_profile_without_verified_titles_fails_closed():
    assert detect_v8_profile(Image.new("RGB",(1920,1032),(10,10,10))) is None

def test_visible_smaart9_process_never_probes_v3():
    with patch("plot_role_v812.locate_plots",return_value=None):
        with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=9):
            from plot_role_v812 import locate_role_plots
            assert locate_role_plots(44) is None
