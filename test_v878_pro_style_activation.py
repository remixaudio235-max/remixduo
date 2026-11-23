import base64
import io
import json
from pathlib import Path
import urllib.error

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


ROOT = Path(__file__).resolve().parent


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self._payload


def _signed_online_token(machine_id: str):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    claims = {
        "v": 3,
        "fpv": 3,
        "platform": "WIN",
        "edition": "PRO",
        "plan": "PRO",
        "machine": machine_id,
        "machine_id": machine_id,
        "machine_ids": [machine_id],
        "hw_ids": [machine_id],
        "iat": 1_700_000_000,
        "exp": 1_900_000_000,
        "lic_id": "0937246967",
        "name": "RemiX QA",
        "online": True,
    }
    raw = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
    token = "LIC1." + _b64(raw) + "." + _b64(private.sign(raw))
    return token, _b64(public)


def test_online_activation_posts_pro_style_contract_and_saves_verified_token(tmp_path):
    from remix_duo_online_license_v878 import activate_online_and_save

    machine = "DUO2-" + "A" * 32
    token, public = _signed_online_token(machine)
    captured = {}

    def transport(request, timeout=0):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"ok": True, "signed_token": token})

    target = tmp_path / "license.lic"
    result = activate_online_and_save(
        "0937246967",
        machine,
        path=target,
        public_key_b64=public,
        now=1_800_000_000,
        transport=transport,
    )

    assert result.valid and result.status == "ACTIVE"
    assert captured["url"].endswith("/api/license/activate")
    assert captured["body"]["license_id"] == "0937246967"
    assert captured["body"]["machine_hash"] == machine
    assert target.read_text("utf-8") == token


def test_duo_gate_is_online_first_and_raw_token_is_advanced_fallback():
    source = (ROOT / "src/remix_duo/licensing/gate.py").read_text("utf-8")
    assert "Số điện thoại / License ID" in source
    assert "Kích hoạt online" in source
    assert "Offline nâng cao" in source
    assert "activate_online_and_save" in source


def test_online_token_must_match_machine_and_signature(tmp_path):
    from remix_duo_online_license_v878 import activate_online_and_save

    machine = "DUO2-" + "B" * 32
    token, public = _signed_online_token("DUO2-" + "C" * 32)

    def transport(_request, timeout=0):
        return _Response({"ok": True, "signed_token": token})

    target = tmp_path / "license.lic"
    result = activate_online_and_save(
        "KH001",
        machine,
        path=target,
        public_key_b64=public,
        now=1_800_000_000,
        transport=transport,
    )
    assert not result.valid and result.status == "MACHINE_MISMATCH"
    assert not target.exists()


def test_build_accepts_fresh_unlicensed_profile_but_not_package_errors():
    script = (ROOT / "build_remix_duo_qa_v877.ps1").read_text("utf-8")
    assert "$selfCheck.ExitCode -notin @(0, 22)" in script
    assert "PACKAGE_SELF_CHECK_LICENSE_STATUS=" in script


def test_frozen_build_gates_on_online_activation_module_import():
    hook = (ROOT / "qa_runtime_hook_remix_duo_v877.py").read_text("utf-8")
    build = (ROOT / "build_remix_duo_qa_v877.ps1").read_text("utf-8")
    assert 'if "--online-license-selfcheck" in sys.argv:' in hook
    assert "remix_duo_online_license_v878" in hook
    assert "--online-license-selfcheck" in build
    assert "ONLINE_LICENSE_SELF_CHECK_FAILED" in build


def test_http_404_json_falls_through_to_request_activation(tmp_path):
    from remix_duo_online_license_v878 import activate_online_and_save

    calls = []

    def transport(request, timeout=0):
        calls.append(request.full_url)
        if request.full_url.endswith("/api/license/activate"):
            payload = json.dumps({
                "ok": False,
                "status": "LICENSE_NOT_FOUND",
                "reason": "License ID chưa được cấp",
            }).encode()
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(payload)
            )
        return _Response({
            "ok": True,
            "status": "ACTIVATION_REQUEST_SENT",
            "message": "Đã gửi yêu cầu kích hoạt đến đại lý.",
        })

    result = activate_online_and_save(
        "KH404",
        "DUO2-" + "D" * 32,
        path=tmp_path / "license.lic",
        transport=transport,
    )
    assert not result.valid
    assert result.status == "ACTIVATION_REQUEST_SENT"
    assert result.message == "Đã gửi yêu cầu kích hoạt đến đại lý."
    assert calls[0].endswith("/api/license/activate")
    assert calls[1].endswith("/api/license/request-activation")


def test_duo_uses_product_scoped_cloudflare_gateway():
    from remix_duo_online_license_v878 import LICENSE_SERVER_URL

    assert LICENSE_SERVER_URL == (
        "https://remix-duo-license.remixaudio235.workers.dev"
    )
