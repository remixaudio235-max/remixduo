import base64
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def signed(platform,fpv,machine):
    key=Ed25519PrivateKey.generate()
    b64=lambda x:base64.urlsafe_b64encode(x).rstrip(b'=').decode()
    claims=dict(v=3,fpv=fpv,platform=platform,edition='PRO',plan='PRO',machine=machine,
                machine_id=machine,machine_ids=[machine],iat=1700000000,exp=1900000000,lic_id='qa',name='QA')
    raw=json.dumps(claims).encode()
    return 'LIC1.'+b64(raw)+'.'+b64(key.sign(raw)), b64(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))

def test_mac_token_strict_platform_machine_and_version(monkeypatch):
    from remix_duo.licensing import online
    monkeypatch.setattr(online.sys,'platform','darwin')
    mid='DUOM4-'+'A'*64
    token,pub=signed('MAC',4,mid)
    assert online.verify_online_token(token,mid,public_key_b64=pub,now=1800000000).valid
    for platform,fpv in [('WIN',4),('ANY',4),('MAC',3)]:
        token,pub=signed(platform,fpv,mid)
        assert not online.verify_online_token(token,mid,public_key_b64=pub,now=1800000000).valid
    token,pub=signed('MAC',4,mid)
    monkeypatch.setattr(online.sys,'platform','win32')
    assert not online.verify_online_token(token,mid,public_key_b64=pub,now=1800000000).valid

def test_mac_activation_posts_mac_identity_and_never_saves_wrong_token(monkeypatch,tmp_path):
    from remix_duo.licensing import online
    monkeypatch.setattr(online.sys,'platform','darwin')
    mid='DUOM4-'+'B'*64
    token,pub=signed('MAC',4,mid)
    bodies=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n): return json.dumps({'ok':True,'signed_token':token}).encode()
    def transport(request,timeout):
        bodies.append(json.loads(request.data));return Response()
    target=tmp_path/'license.lic'
    result=online.activate_online_and_save('123456',mid,path=target,transport=transport,public_key_b64=pub,now=1800000000)
    assert result.valid and target.read_text()==token
    assert bodies[0]['platform']=='MAC' and bodies[0]['fpv']==4
    token,pub=signed('WIN',3,mid)
    target.unlink()
    assert not online.activate_online_and_save('123456',mid,path=target,transport=transport,public_key_b64=pub,now=1800000000).valid
    assert not target.exists()
