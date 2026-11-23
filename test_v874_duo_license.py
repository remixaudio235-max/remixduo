"""V8.74 offline licensing synthetic QA: no real private key/PII in fixtures."""
import base64
import json
from dataclasses import replace
from pathlib import Path
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

import remix_duo_license_v874 as license
import remix_duo_issuer_admin_v874 as issuer

MID = "DUO2-" + "A" * 32
MID2 = "DUO2-" + "B" * 32
NOW = 1793552400


def public_key(key):
    return license.base64.urlsafe_b64encode(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    ).rstrip(b"=").decode("ascii")


def payload(**kw):
    data = dict(
        v=2, fpv=2, platform="WIN", edition="DUO_PRO",
        machine_ids=[MID], machine=MID, machine_id=MID,
        lic_id="DUO-QA", name="QA", iat=NOW-100,
        exp=NOW+86400,
    )
    data.update(kw)
    return data


def sign(key, data=None, raw=None):
    if raw is None:
        raw = json.dumps(data if data is not None else payload(),
                         separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    enc = license.base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    sig = license.base64.urlsafe_b64encode(key.sign(raw)).rstrip(b"=").decode()
    return "LIC1." + enc + "." + sig


@pytest.fixture
def keys():
    key = Ed25519PrivateKey.generate()
    return key, public_key(key)


def verify(keys, data=None, token=None, *, mid=MID, now=NOW):
    key, pub = keys
    return license.verify_token(
        token if token is not None else sign(key, data), mid,
        public_key_b64=pub, now=now
    )


def test_tune_compatible_lic1_product_scoped(keys):
    state = verify(keys)
    assert state.valid and state.code == "ACTIVE"
    assert state.lic_id == "DUO-QA" and state.expires_at == NOW+86400


@pytest.mark.parametrize("changes,expected", [
    ({"edition": "PRO"}, "PRODUCT_EDITION_MISMATCH"),
    ({"edition": "SUITE"}, "PRODUCT_EDITION_MISMATCH"),
    ({"platform": "MAC"}, "PLATFORM_MISMATCH"),
    ({"platform": "ANY"}, "PLATFORM_MISMATCH"),
    ({"v": 1}, "UNSUPPORTED_LICENSE_VERSION"),
    ({"fpv": 1}, "UNSUPPORTED_LICENSE_VERSION"),
    ({"machine_ids": [MID2], "machine": MID2, "machine_id": MID2}, "MACHINE_MISMATCH"),
    ({"machine_ids": [MID], "machine": MID2}, "MACHINE_ALIAS_MISMATCH"),
    ({"machine_ids": [MID, MID, MID]}, "INVALID_MACHINE_IDS"),
    ({"exp": NOW-1}, "EXPIRED"),
    ({"exp": NOW-200}, "INVALID_LICENSE_DATES"),
    ({"iat": NOW+500}, "ISSUED_IN_FUTURE"),
    ({"iat": "1"}, "INVALID_LICENSE_DATES"),
    ({"exp": True}, "INVALID_LICENSE_DATES"),
    ({"exp": NOW-100}, "INVALID_LICENSE_DATES"),
    ({"name": ""}, "INVALID_LICENSE_IDENTITY"),
])
def test_invalid_claims_fail_closed(keys, changes, expected):
    assert verify(keys, payload(**changes)).code == expected


def test_perpetual_and_second_machine(keys):
    state = verify(keys, payload(exp=0, machine_ids=[MID, MID2]), mid=MID2,
                   now=NOW + 20*365*86400)
    assert state.valid and state.expires_at == 0


def test_modified_signature_or_wrong_key(keys):
    token = sign(keys[0])
    other_key = Ed25519PrivateKey.generate()
    assert license.verify_token(token, MID, public_key_b64=public_key(other_key),
                                now=NOW).code == "INVALID_SIGNATURE"
    head, b64pay, sig = token.split(".")
    wrong = "A" if sig[0] != "A" else "B"
    tampered = ".".join((head,b64pay,wrong + sig[1:]))
    assert verify(keys, token=tampered).code == "INVALID_SIGNATURE"


def test_duplicate_json_key_rejected(keys):
    raw = (b'{"v":2,"v":2,"fpv":2,"edition":"DUO_PRO","platform":"WIN"}')
    assert verify(keys, token=sign(keys[0], raw=raw)).code == "INVALID_PAYLOAD_JSON"


@pytest.mark.parametrize("token,expected", [
    ("foo", "INVALID_TOKEN_FORMAT"),
    ("LIC1.*.no", "INVALID_SIGNATURE"),
    ("LIC1.a.a", "INVALID_SIGNATURE"),
    ("x" * 12001, "INVALID_TOKEN_LENGTH"),
])
def test_bad_token(keys, token, expected):
    assert verify(keys, token=token).code == expected


def test_unprovisioned_runtime_public_key_refuses_license(keys):
    token = sign(keys[0])
    assert license.verify_token(token, MID, now=NOW,
                                public_key_b64="").code == "ISSUER_PUBLIC_KEY_NOT_PROVISIONED"


def test_activate_then_restore_and_reject_expired(keys, tmp_path):
    key, pub = keys
    path = tmp_path/"license.lic"
    valid = sign(key)
    first = license.activate_token(valid, machine_id=MID,
                                   public_key_b64=pub, now=NOW, path=path)
    assert first.valid and path.read_text("utf-8") == valid
    invalid = sign(key, payload(exp=NOW-1))
    result = license.activate_token(invalid, machine_id=MID,
                                    public_key_b64=pub, now=NOW, path=path)
    assert result.code == "EXPIRED"
    assert path.read_text("utf-8") == valid
    assert license.load_installed_license(machine_id=MID, public_key_b64=pub,
                                          now=NOW, path=path).valid
    assert not license.load_installed_license(machine_id=MID2, public_key_b64=pub,
                                              now=NOW, path=path).valid


def test_absent_or_malformed_lic(keys, tmp_path):
    path = tmp_path/"license.lic"
    assert license.load_installed_license(machine_id=MID, path=path).code == "NOT_ACTIVATED"
    path.write_text("invalid", encoding="utf-8")
    assert license.load_installed_license(machine_id=MID, path=path).code == "ISSUER_PUBLIC_KEY_NOT_PROVISIONED" or \
           license.load_installed_license(machine_id=MID, public_key_b64=keys[1],path=path).code == "INVALID_TOKEN_FORMAT"


def test_issuer_matches_tune_lic1_and_product_and_ledger(keys, tmp_path, monkeypatch):
    monkeypatch.setattr(issuer, "admin_store", lambda: tmp_path)
    output = tmp_path/"issued.lic"
    assert issuer.issue(machine_ids=[MID,MID2], lic_id="DL-001",
                        name="QA", days=30, output_path=output,
                        signer=keys[0], now=NOW) == str(output.resolve())
    token = output.read_text("utf-8").strip()
    assert verify(keys, token=token, mid=MID2).valid
    assert (tmp_path/"duo_license_ledger.tsv").exists()
    with pytest.raises(FileExistsError):
        issuer.issue(machine_ids=[MID], lic_id="DL-002", name="QA",
                     days=0, output_path=output,
                     signer=keys[0], now=NOW)
    with pytest.raises(ValueError, match="INVALID_DUO_MACHINE_ID"):
        issuer.issue(machine_ids=["MACHINE"], lic_id="X", name="QA",
                     days=30, output_path=tmp_path/"invalid.lic",
                     signer=keys[0], now=NOW)


def test_issuer_perpetual_and_invalid_day_count(keys, tmp_path, monkeypatch):
    monkeypatch.setattr(issuer, "admin_store", lambda: tmp_path)
    output=tmp_path/"perpetual.lic"
    issuer.issue(machine_ids=[MID], lic_id="D-1", name="QA",
                 days=0, output_path=output, now=NOW, signer=keys[0])
    assert verify(keys, token=output.read_text("utf-8"), now=NOW+100000).valid
    with pytest.raises(ValueError, match="INVALID_LICENSE_DAYS"):
        issuer.issue(machine_ids=[MID], lic_id="D-2", name="QA",
                     days=-1, output_path=tmp_path/"invalid.lic",
                     signer=keys[0], now=NOW)
