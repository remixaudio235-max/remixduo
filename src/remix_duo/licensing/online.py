"""RemiX Duo online activation compatible with the RemiX Audio Pro flow.

The customer enters a phone number or License ID. The client sends only that
identifier, a product-scoped machine hash and a non-secret machine label. A
returned LIC1 token is verified with the pinned Ed25519 public key before it is
atomically installed. No signing/admin secret is present in the desktop app.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import sys
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


LICENSE_SERVER_URL = "https://remix-duo-license.remixaudio235.workers.dev"
ONLINE_PUBLIC_KEY_B64 = "zLGQbDZwLyFaYf8zzK9Vv6eT43rdG9NqbDzPzAh6XPY"
from .. import __version__
APP_VERSION = __version__
MAX_RESPONSE_BYTES = 12_000
MAX_TOKEN_BYTES = 12_000
MAX_PAYLOAD_BYTES = 4_096
MAX_FUTURE_SKEW = 300


@dataclass(frozen=True)
class OnlineLicenseResult:
    valid: bool
    status: str
    message: str = ""
    token: str = ""
    lic_id: str = ""
    customer: str = ""
    expires_at: int = 0


def _b64decode(value: str, maximum: int) -> bytes:
    if not isinstance(value, str) or not value or len(value) > maximum * 2:
        raise ValueError("INVALID_BASE64")
    if re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ValueError("INVALID_BASE64")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(raw) > maximum:
        raise ValueError("VALUE_TOO_LARGE")
    return raw


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_PAYLOAD_KEY")
        result[key] = value
    return result


def _machine_ids(payload: dict) -> list[str]:
    values = []
    for key in ("machine", "machine_id", "hw_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip().upper())
    for key in ("machine_ids", "hw_ids"):
        items = payload.get(key)
        if isinstance(items, list):
            values.extend(
                item.strip().upper()
                for item in items
                if isinstance(item, str) and item.strip()
            )
    return list(dict.fromkeys(values))


def _profile():
    if sys.platform == "win32":
        return "WIN", 3, r"DUO2-[0-9A-F]{32}"
    if sys.platform == "darwin":
        return "MAC", 4, r"DUOM4-[0-9A-F]{64}"
    raise RuntimeError("UNSUPPORTED_PLATFORM")


def verify_online_token(token: str, machine_id: str, *,
                        public_key_b64: str = ONLINE_PUBLIC_KEY_B64,
                        now: int | None = None) -> OnlineLicenseResult:
    if not isinstance(token, str) or len(token.encode("utf-8")) > MAX_TOKEN_BYTES:
        return OnlineLicenseResult(False, "INVALID_TOKEN_LENGTH")
    chunks = token.strip().split(".")
    if len(chunks) != 3 or chunks[0] != "LIC1":
        return OnlineLicenseResult(False, "INVALID_TOKEN_FORMAT")
    try:
        payload_bytes = _b64decode(chunks[1], MAX_PAYLOAD_BYTES)
        signature = _b64decode(chunks[2], 64)
        public = _b64decode(public_key_b64, 32)
        if len(signature) != 64 or len(public) != 32:
            return OnlineLicenseResult(False, "INVALID_KEY_OR_SIGNATURE")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(signature, payload_bytes)
    except Exception:
        return OnlineLicenseResult(False, "INVALID_SIGNATURE")
    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"), object_pairs_hook=_reject_duplicates
        )
    except (UnicodeError, ValueError, TypeError):
        return OnlineLicenseResult(False, "INVALID_PAYLOAD_JSON")
    if not isinstance(payload, dict):
        return OnlineLicenseResult(False, "INVALID_PAYLOAD")
    if (type(payload.get("v")) is not int or payload["v"] != 3 or
            type(payload.get("fpv")) is not int or payload["fpv"] != _profile()[1]):
        return OnlineLicenseResult(False, "UNSUPPORTED_LICENSE_VERSION")
    if payload.get("platform") != _profile()[0]:
        return OnlineLicenseResult(False, "PLATFORM_MISMATCH")
    if payload.get("edition") != "PRO" or payload.get("plan") != "PRO":
        return OnlineLicenseResult(False, "PRODUCT_EDITION_MISMATCH")
    mids = _machine_ids(payload)
    wanted = str(machine_id or "").strip().upper()
    if not mids:
        return OnlineLicenseResult(False, "INVALID_MACHINE_IDS")
    if not wanted or wanted not in mids:
        return OnlineLicenseResult(False, "MACHINE_MISMATCH")
    iat, exp = payload.get("iat"), payload.get("exp")
    if (type(iat) is not int or type(exp) is not int or iat <= 0 or
            exp < 0 or (exp > 0 and exp <= iat)):
        return OnlineLicenseResult(False, "INVALID_LICENSE_DATES")
    current = int(time.time()) if now is None else now
    if type(current) is not int:
        return OnlineLicenseResult(False, "INVALID_CLOCK")
    if iat > current + MAX_FUTURE_SKEW:
        return OnlineLicenseResult(False, "ISSUED_IN_FUTURE")
    if exp and current >= exp:
        return OnlineLicenseResult(False, "EXPIRED")
    lic_id = payload.get("lic_id") or payload.get("license_id")
    customer = payload.get("name") or payload.get("customer_phone")
    if not isinstance(lic_id, str) or not 1 <= len(lic_id) <= 128:
        return OnlineLicenseResult(False, "INVALID_LICENSE_IDENTITY")
    if not isinstance(customer, str) or not 1 <= len(customer) <= 128:
        return OnlineLicenseResult(False, "INVALID_LICENSE_IDENTITY")
    return OnlineLicenseResult(
        True, "ACTIVE", "Kích hoạt online thành công.", token.strip(),
        lic_id, customer, exp,
    )


def _valid_server_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return bool(
        parsed.scheme == "https" and parsed.hostname and
        parsed.username is None and parsed.password is None and
        not parsed.query and not parsed.fragment
    )


def configured() -> bool:
    """Return whether the pinned public production endpoint/key are usable."""
    try:
        key = _b64decode(ONLINE_PUBLIC_KEY_B64, 32)
    except (ValueError, TypeError):
        return False
    return _valid_server_url(LICENSE_SERVER_URL) and len(key) == 32


def _request_json(path: str, body: dict, *, transport=None) -> dict:
    if not _valid_server_url(LICENSE_SERVER_URL):
        raise ValueError("LICENSE_SERVER_NOT_CONFIGURED")
    request = urllib.request.Request(
        LICENSE_SERVER_URL.rstrip("/") + path,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": f"RemiXDuo/{APP_VERSION} Windows LicenseClient",
        },
        method="POST",
    )
    perform = urllib.request.urlopen if transport is None else transport
    try:
        with perform(request, timeout=8.0) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("LICENSE_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
        except (UnicodeError, ValueError, TypeError):
            result = {"ok": False, "error": "HTTP " + str(exc.code)}
        if not isinstance(result, dict):
            result = {"ok": False, "error": "HTTP " + str(exc.code)}
        result.setdefault("ok", False)
        result.setdefault("http_status", int(exc.code))
        return result
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("LICENSE_RESPONSE_TOO_LARGE")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("INVALID_LICENSE_RESPONSE")
    return result


def _clean_license_id(value: str) -> str:
    cleaned = str(value or "").strip()
    if (not 3 <= len(cleaned) <= 128 or "\r" in cleaned or "\n" in cleaned or
            re.fullmatch(r"[0-9A-Za-z@._+ -]+", cleaned) is None):
        raise ValueError("INVALID_LICENSE_ID")
    return cleaned


def machine_label() -> str:
    return (platform.node() or os.environ.get("COMPUTERNAME") or "Windows")[:120]


def _atomic_write_token(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".online-lic-", suffix=".tmp", delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(token.strip())
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def activate_online_and_save(license_id: str, machine_id: str, *, path: Path,
                             public_key_b64: str = ONLINE_PUBLIC_KEY_B64,
                             now: int | None = None,
                             transport=None) -> OnlineLicenseResult:
    try:
        code = _clean_license_id(license_id)
        machine = str(machine_id or "").strip().upper()
        if not re.fullmatch(_profile()[2], machine):
            return OnlineLicenseResult(False, "INVALID_MACHINE_ID")
        body = {
            "license_id": code,
            "machine_hash": machine,
            "machine_label": machine_label(),
            "app_version": APP_VERSION,
        }
        if _profile()[0] == "MAC":
            body.update(platform="MAC", fpv=4)
        response = _request_json("/api/license/activate", body, transport=transport)
        if response.get("ok") is not True:
            status = str(response.get("status") or response.get("reason") or "ACTIVATION_FAILED")
            message = str(response.get("message") or response.get("error") or response.get("reason") or status)
            if status in {"LICENSE_NOT_FOUND", "NOT_ACTIVATED"}:
                requested = _request_json(
                    "/api/license/request-activation",
                    {**body, "phone": code, "note": message[:300]},
                    transport=transport,
                )
                return OnlineLicenseResult(
                    False,
                    str(requested.get("status") or "ACTIVATION_REQUEST_SENT"),
                    str(requested.get("message") or "Đã gửi yêu cầu kích hoạt đến đại lý."),
                )
            return OnlineLicenseResult(False, status, message)
        token = str(response.get("signed_token") or response.get("token") or "").strip()
        if not token:
            return OnlineLicenseResult(False, "BAD_TOKEN", "Server không trả signed_token.")
        verified = verify_online_token(
            token, machine, public_key_b64=public_key_b64, now=now
        )
        if not verified.valid:
            return verified
        _atomic_write_token(Path(path), token)
        return verified
    except urllib.error.HTTPError as exc:
        return OnlineLicenseResult(False, f"HTTP_{exc.code}", "Máy chủ từ chối yêu cầu kích hoạt.")
    except (urllib.error.URLError, TimeoutError):
        return OnlineLicenseResult(False, "SERVER_UNREACHABLE", "Không kết nối được máy chủ kích hoạt.")
    except (OSError, UnicodeError, ValueError, TypeError, RuntimeError) as exc:
        return OnlineLicenseResult(False, str(exc) or "ACTIVATION_FAILED")
