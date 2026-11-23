"""RemiX Duo V8.76 Cloudflare centralized license client (fail-closed).

Issue/revoke/renew keys ONLY in the Cloudflare Worker+D1 account.
This is an opt-in integration until cloud endpoint, D1 and signer are
provisioned, tested and the cloud public verification key is pinned.
No private key or Cloudflare administrator credential in the desktop app.
"""
from __future__ import annotations
from dataclasses import dataclass
import base64
import json
from pathlib import Path
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from remix_duo_license_v874 import (
    machine_code, verify_token, LicenseState,
)

# Deliberately unprovisioned until the real Cloudflare Worker is deployed.
CLOUD_WORKER_URL = ""
CLOUD_PUBLIC_KEY_B64 = "YhjHt2d56jqSpR5Sctssgg52lSo11zBaHJNHRLoGfNA"
MAX_JSON_BYTES = 12000


@dataclass(frozen=True)
class CloudActivation:
    valid: bool
    status: str
    certificate: str = ""
    expires_at: int = 0


def configured() -> bool:
    url = urllib.parse.urlsplit(CLOUD_WORKER_URL)
    return bool(
        url.scheme == "https" and url.hostname and url.username is None
        and url.password is None and not url.fragment and not url.query
        and CLOUD_PUBLIC_KEY_B64 and
        re.fullmatch(r"[A-Za-z0-9_-]{43}", CLOUD_PUBLIC_KEY_B64)
    )


def certificate_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise RuntimeError("LOCALAPPDATA_UNAVAILABLE")
    return Path(root) / "RemiXAudio" / "Duo" / "cloud_certificate.lic"


def activation_key_path() -> Path:
    root = os.environ.get("LOCALAPPDATA", "")
    if not root:
        raise RuntimeError("LOCALAPPDATA_UNAVAILABLE")
    return Path(root) / "RemiXAudio" / "Duo" / "cloud_key.dpapi"


def _remember_activation_key(key: str) -> None:
    """Encrypt activation key with current Windows user's DPAPI."""
    import win32crypt
    target = activation_key_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    encrypted = win32crypt.CryptProtectData(
        key.strip().upper().encode("ascii"),
        "RemiX Duo Cloudflare activation renewal", None, None, None, 0
    )
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent, prefix=".cloud-key-",
            suffix=".tmp", delete=False
        ) as out:
            tmp = Path(out.name)
            out.write(encrypted)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _cached_activation_key() -> str | None:
    try:
        import win32crypt
        path = activation_key_path()
        if path.stat().st_size > 4096:
            return None
        plain = win32crypt.CryptUnprotectData(
            path.read_bytes(), None, None, None, 0
        )[1].decode("ascii")
        return plain if re.fullmatch(
            r"RDX-(?:[0-9A-F]{8}-){3}[0-9A-F]{8}", plain
        ) else None
    except (OSError, ImportError, ValueError, UnicodeError):
        return None


def _cloud_claims(token: str) -> dict | None:
    if not isinstance(token, str) or not token.startswith("LIC1."):
        return None
    try:
        encoded = token.split(".")[1]
        raw = base64.b64decode(encoded + "=" * (-len(encoded)%4),
                               altchars=b"-_", validate=True)
        claims = json.loads(raw.decode("utf-8"))
    except (ValueError, IndexError, UnicodeError, TypeError):
        return None
    return claims if isinstance(claims,dict) else None


def verify_cloud_certificate(token: str, mid: str, *, now=None,
                             public_key_b64: str | None = None) -> LicenseState:
    public = CLOUD_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64
    result = verify_token(token, mid, public_key_b64=public, now=now)
    if not result.valid:
        return result
    claims = _cloud_claims(token)
    if claims is None or claims.get("issuer") != "CLOUDFLARE":
        return LicenseState(False, "NOT_CLOUDFLARE_ISSUED")
    # Require short time-bound server-issued activation proof.
    iat, exp = claims.get("iat"), claims.get("exp")
    if (type(iat) is not int or type(exp) is not int or
        not iat < exp <= iat + 72 * 3600):
        return LicenseState(False, "INVALID_CLOUD_GRACE")
    return result


def offline_state(*, mid=None, now=None, path=None,
                  public_key_b64=None) -> LicenseState:
    try:
        p = certificate_path() if path is None else Path(path)
        if not p.is_file():
            return LicenseState(False, "CLOUD_ACTIVATION_REQUIRED")
        if p.stat().st_size > MAX_JSON_BYTES:
            return LicenseState(False, "INVALID_TOKEN_LENGTH")
        return verify_cloud_certificate(
            p.read_text(encoding="utf-8"),
            machine_code() if mid is None else mid,
            now=now, public_key_b64=public_key_b64,
        )
    except (OSError, UnicodeError, ValueError, RuntimeError):
        return LicenseState(False, "CLOUD_CERTIFICATE_UNREADABLE")


def activate_cloud(key: str, *, mid: str | None = None,
                   url: str | None = None, public_key_b64: str | None = None,
                   now=None, path=None, transport=None,
                   remember: bool = False) -> CloudActivation:
    """POST activation only. No admin token, and no GET/SET to Smaart.

    url, key override and transport are strictly for isolated QA (test server).
    Production activation_gate uses only compiled, pinned configuration.
    """
    endpoint = CLOUD_WORKER_URL if url is None else url
    public = CLOUD_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != "https" or not parsed.hostname or
        parsed.username or parsed.password or parsed.fragment or parsed.query):
        return CloudActivation(False, "CLOUD_NOT_CONFIGURED")
    if not public:
        return CloudActivation(False, "CLOUD_PUBLIC_KEY_MISSING")
    if not isinstance(key, str) or not re.fullmatch(
            r"RDX-(?:[0-9A-F]{8}-){3}[0-9A-F]{8}",key.strip().upper()):
        return CloudActivation(False, "INVALID_LICENSE_KEY")
    try:
        machine=machine_code() if mid is None else mid
        req=urllib.request.Request(
            endpoint.rstrip("/") + "/v1/activate",
            data=json.dumps({"key":key.strip().upper(),
                             "machine_id":machine},
                            separators=(",",":")).encode("utf-8"),
            headers={"content-type":"application/json", "accept":"application/json"},
            method="POST")
        perform=urllib.request.urlopen if transport is None else transport
        with perform(req,timeout=6.0) as resp:
            raw=resp.read(MAX_JSON_BYTES+1)
        if len(raw)>MAX_JSON_BYTES:
            return CloudActivation(False, "CLOUD_RESPONSE_TOO_LARGE")
        body=json.loads(raw)
        if not isinstance(body,dict) or body.get("ok") is not True:
            return CloudActivation(False, "CLOUD_REJECTED")
        token=body.get("token")
        verified=verify_cloud_certificate(token,machine,now=now,
                                          public_key_b64=public)
        if not verified.valid:
            return CloudActivation(False, verified.code)
        target=certificate_path() if path is None else Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",encoding="utf-8",newline="\n",
                dir=target.parent,prefix=".cloud-lic-",suffix=".tmp",
                delete=False) as f:
                temporary=Path(f.name)
                f.write(token)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary,target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        if remember:
            try:
                _remember_activation_key(key)
            except (OSError, ImportError, RuntimeError, ValueError):
                pass  # Activation remains signed; re-entry may be needed.
        return CloudActivation(True, "CLOUD_ACTIVE",token,verified.expires_at)
    except urllib.error.HTTPError as exc:
        return CloudActivation(False, "CLOUD_HTTP_"+str(exc.code))
    except (urllib.error.URLError,TimeoutError):
        return CloudActivation(False, "CLOUD_UNREACHABLE")
    except (ValueError,TypeError,OSError,UnicodeError,RuntimeError):
        return CloudActivation(False, "CLOUD_ACTIVATION_FAILED")


def activation_gate() -> bool:
    """A separately provisioned gate for the Cloudflare-only production build."""
    if not configured():
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "RemiX Duo Cloud License",
                             "Cloudflare License chua duoc cau hinh. Khong the mo app.")
        return False
    mid=machine_code()
    current=offline_state(mid=mid)
    if current.valid:
        return True
    cached_key=_cached_activation_key()
    if cached_key:
        renewed=activate_cloud(cached_key,mid=mid)
        if renewed.valid:
            return True
    from PyQt6.QtWidgets import (
        QDialog,QVBoxLayout,QLabel,QPlainTextEdit,QPushButton,
        QHBoxLayout
    )
    from PyQt6.QtGui import QGuiApplication
    dlg=QDialog()
    dlg.setWindowTitle("RemiX Duo | Cloudflare Key Active")
    dlg.setMinimumWidth(470)
    layout=QVBoxLayout(dlg)
    layout.addWidget(QLabel("RemiX Duo - License duoc cap tren Cloudflare"))
    layout.addWidget(QLabel("Machine ID: "+mid))
    copy=QPushButton("Copy Machine ID")
    copy.clicked.connect(lambda:QGuiApplication.clipboard().setText(mid))
    layout.addWidget(copy)
    entry=QPlainTextEdit()
    entry.setPlaceholderText("RDX-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX")
    entry.setMaximumHeight(70)
    layout.addWidget(entry)
    status=QLabel(current.code)
    layout.addWidget(status)
    controls=QHBoxLayout()
    activate=QPushButton("Kich hoat Cloudflare")
    cancel=QPushButton("Thoat")
    controls.addWidget(activate)
    controls.addWidget(cancel)
    layout.addLayout(controls)
    cancel.clicked.connect(dlg.reject)
    def on_activate():
        result=activate_cloud(entry.toPlainText(),remember=True)
        status.setText(result.status)
        if result.valid:
            dlg.accept()
    activate.clicked.connect(on_activate)
    return dlg.exec() == QDialog.DialogCode.Accepted
