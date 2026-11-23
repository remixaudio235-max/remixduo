"""V8.76 Cloudflare activation cert QA using ephemeral offline signing fixtures."""
import base64
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import remix_duo_cloud_license_v876 as client

MID="DUO2-"+"A"*32
MID2="DUO2-"+"B"*32
NOW=1793576700


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@pytest.fixture
def signer():
    key=Ed25519PrivateKey.generate()
    public=b64(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))
    return key,public


def certificate(key, **updates):
    raw=dict(v=2,fpv=2,platform="WIN",edition="DUO_PRO",issuer="CLOUDFLARE",
             machine_ids=[MID],machine=MID,machine_id=MID,
             lic_id="CLOUD-TEST",name="QA",iat=NOW-100,exp=NOW+3600)
    raw.update(updates)
    payload=json.dumps(raw,separators=(",",":"),ensure_ascii=False).encode()
    return "LIC1."+b64(payload)+"."+b64(key.sign(payload))


def test_valid_cloud_certificate(signer):
    key,pub=signer
    actual=client.verify_cloud_certificate(certificate(key),MID,now=NOW,
                                           public_key_b64=pub)
    assert actual.valid and actual.code=="ACTIVE"


@pytest.mark.parametrize("changes,expected",[
    ({"issuer":"LOCAL"}, "NOT_CLOUDFLARE_ISSUED"),
    ({"issuer":"CLOUDFLARE","edition":"PRO"}, "PRODUCT_EDITION_MISMATCH"),
    ({"exp":NOW+73*3600}, "INVALID_CLOUD_GRACE"),
    ({"exp":0}, "INVALID_CLOUD_GRACE"),
    ({"exp":NOW-1}, "EXPIRED"),
    ({"machine_ids":[MID2],"machine":MID2,"machine_id":MID2},"MACHINE_MISMATCH"),
])
def test_reject_non_cloud_or_forged_claims(signer,changes,expected):
    key,pub=signer
    assert client.verify_cloud_certificate(
        certificate(key,**changes),MID,now=NOW,public_key_b64=pub).code==expected


def test_unprovisioned_cloud_cannot_activate(signer):
    key,pub=signer
    assert not client.configured()
    result=client.activate_cloud(
        "RDX-"+"ABCD1234-"*3+"ABCD1234",mid=MID,
        public_key_b64=pub)
    assert result.status=="CLOUD_NOT_CONFIGURED"


def test_mock_server_issue_certificate_and_store_atomically(signer,tmp_path):
    key,pub=signer
    token=certificate(key)
    url="https://test-only-license.example"
    class MockResponse:
        def __init__(self):
            self.data=json.dumps({"ok":True,"token":token}).encode()
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,max_count):return self.data[:max_count]
    seen=[]
    def stub(req,timeout):
        seen.append((req.full_url,req.get_method(),req.data,timeout))
        return MockResponse()
    p=tmp_path/"cloud_certificate.lic"
    result=client.activate_cloud("RDX-"+"ABCD1234-"*3+"ABCD1234",
        mid=MID,url=url,public_key_b64=pub,now=NOW,path=p,transport=stub)
    assert result.valid and result.status=="CLOUD_ACTIVE"
    assert result.expires_at==NOW+3600
    assert p.read_text()==token
    assert seen[0][0].endswith("/v1/activate")
    assert seen[0][1]=="POST"
    sent=json.loads(seen[0][2])
    assert sent["machine_id"]==MID and sent["key"].startswith("RDX-")
    assert client.offline_state(mid=MID,path=p,now=NOW,public_key_b64=pub).valid


def test_mock_server_wrong_signer_cannot_overwrite_valid(signer,tmp_path):
    key,pub=signer
    original=certificate(key)
    other=Ed25519PrivateKey.generate()
    malicious=certificate(other)
    p=tmp_path/"old.lic"
    p.write_text(original)
    class Resp:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,*_):
            return json.dumps({"ok":True,"token":malicious}).encode()
    result=client.activate_cloud("RDX-"+"ABCDEF12-"*3+"ABCDEF12",
        mid=MID,url="https://test-only-license.example",public_key_b64=pub,
        now=NOW,path=p,transport=lambda *a,**kw:Resp())
    assert not result.valid and result.status=="INVALID_SIGNATURE"
    assert p.read_text()==original


def test_malformed_or_missing_cached_cert(signer,tmp_path):
    key,pub=signer
    p=tmp_path/"missing.lic"
    assert client.offline_state(mid=MID,path=p,now=NOW,
                                public_key_b64=pub).code=="CLOUD_ACTIVATION_REQUIRED"
    p.write_text("LIC1.invalid.invalid")
    assert not client.offline_state(mid=MID,path=p,now=NOW,
                                    public_key_b64=pub).valid


def test_certificate_expiration_requires_cloud_refresh(signer,tmp_path):
    key,pub=signer
    p=tmp_path/"cert.lic"
    p.write_text(certificate(key))
    state=client.offline_state(mid=MID,path=p,now=NOW+3601,public_key_b64=pub)
    assert state.code=="EXPIRED"


def test_activation_key_encrypted_by_windows_dpapi(monkeypatch,tmp_path):
    import os
    if os.name!="nt":
        pytest.skip("Windows-only DPAPI")
    path=tmp_path/"cloud_key.dpapi"
    monkeypatch.setattr(client,"activation_key_path",lambda:path)
    assert client._cached_activation_key() is None
    token="RDX-"+"ABCD1234-"*3+"ABCD1234"
    client._remember_activation_key(token)
    assert path.is_file() and token.encode() not in path.read_bytes()
    assert client._cached_activation_key()==token


def test_endpoint_rejects_http_or_unsafe_urls(signer):
    key,pub=signer
    for url in ["http://example.com", "https://user:pass@server.example",
                "https://server.example/path?secret=x"]:
        result=client.activate_cloud("RDX-"+"ABCDEF12-"*3+"ABCDEF12",
            mid=MID,url=url,public_key_b64=pub)
        assert not result.valid and result.status=="CLOUD_NOT_CONFIGURED"
