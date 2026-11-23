"""RemiX Duo V8.74: product-scoped, offline Ed25519 license verification.

Compatible with RemiX Tune's LIC1.<base64url-payload>.<base64url-signature>
signed payload v2 (WIN, fpv=2, machine_ids, iat, exp), but independently
provisioned DUO_PRO public key and edition. No signing secret in the client.

Security: a locally modified Python program cannot be considered tamper-proof.
Commercial release should package/attest its runtime; online revocation is
separate and is NOT provided by this offline entitlement.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

PRODUCT_EDITION = "DUO_PRO"
PLATFORM = "WIN"
FORMAT_VERSION = 2
FINGERPRINT_VERSION = 2
# Generated once by the admin-only issuer; pinned in signed client source.
TRUSTED_PUBLIC_KEY_B64 = "9V4pAxQsDxiC-WufEw_Fyy7P9pKFmZTVuje03Ro6gCg"
TOKEN_LIMIT = 12000
PAYLOAD_LIMIT = 4096
MAX_FUTURE_SKEW = 300


@dataclass(frozen=True)
class LicenseState:
    valid: bool
    code: str
    lic_id: str = ""
    customer: str = ""
    expires_at: int = 0


def license_display(state: LicenseState) -> tuple[str, str]:
    """Return a compact status badge without ever exposing the license key."""
    if state.valid:
        details = ["License: ACTIVE"]
        if state.lic_id:
            details.append("ID: " + state.lic_id)
        if state.customer:
            details.append("Customer: " + state.customer)
        details.append("Expires: never" if not state.expires_at else
                       "Expires (UTC epoch): " + str(state.expires_at))
        return "RemiX Duo · ACTIVE", "\n".join(details)
    return "RemiX Duo", "License: " + state.code


def machine_code() -> str:
    from ..platforms.factory import services
    return services().machine_code()


def license_path() -> Path:
    from ..platforms.paths import app_paths
    return app_paths().license


def _b64url_decode(value: str, max_bytes: int) -> bytes:
    if not isinstance(value, str) or not value or len(value) > max_bytes * 2:
        raise ValueError("INVALID_BASE64")
    if re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise ValueError("INVALID_BASE64")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4),
                               altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("INVALID_BASE64") from exc
    if len(raw) > max_bytes or base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value:
        raise ValueError("INVALID_BASE64")
    return raw


def _reject_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_PAYLOAD_KEY")
        out[key] = value
    return out


def verify_token(token: str, machine_id: str, *,
                 public_key_b64: str | None = None,
                 now: int | None = None) -> LicenseState:
    """Cryptographically verify exact raw payload, then machine/edition/time.

    public_key_b64 override is for isolated QA with disposable test keys only;
    the runtime gate below intentionally uses the pinned release public key.
    """
    if not isinstance(token, str) or len(token) > TOKEN_LIMIT:
        return LicenseState(False, "INVALID_TOKEN_LENGTH")
    chunks = token.strip().split(".")
    if len(chunks) != 3 or chunks[0] != "LIC1":
        return LicenseState(False, "INVALID_TOKEN_FORMAT")
    pub = TRUSTED_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64
    if not pub:
        return LicenseState(False, "ISSUER_PUBLIC_KEY_NOT_PROVISIONED")
    try:
        payload_bytes = _b64url_decode(chunks[1], PAYLOAD_LIMIT)
        signature = _b64url_decode(chunks[2], 64)
        key_bytes = _b64url_decode(pub, 32)
        if len(signature) != 64 or len(key_bytes) != 32:
            return LicenseState(False, "INVALID_KEY_OR_SIGNATURE")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature, payload_bytes)
    except Exception:
        return LicenseState(False, "INVALID_SIGNATURE")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"),
                             object_pairs_hook=_reject_duplicates)
    except (ValueError, UnicodeError, TypeError):
        return LicenseState(False, "INVALID_PAYLOAD_JSON")
    if not isinstance(payload, dict):
        return LicenseState(False, "INVALID_PAYLOAD")
    if (type(payload.get("v")) is not int or payload["v"] != FORMAT_VERSION or
        type(payload.get("fpv")) is not int or payload["fpv"] != FINGERPRINT_VERSION):
        return LicenseState(False, "UNSUPPORTED_LICENSE_VERSION")
    from ..platforms.factory import services
    if services().platform != PLATFORM or payload.get("platform") != PLATFORM:
        return LicenseState(False, "PLATFORM_MISMATCH")
    if payload.get("edition") != PRODUCT_EDITION:
        return LicenseState(False, "PRODUCT_EDITION_MISMATCH")
    mids = payload.get("machine_ids")
    if (not isinstance(mids, list) or not 1 <= len(mids) <= 2 or
        any(not isinstance(x, str) or not re.fullmatch(r"DUO2-[0-9A-F]{32}", x) for x in mids) or
        len(set(mids)) != len(mids)):
        return LicenseState(False, "INVALID_MACHINE_IDS")
    if payload.get("machine") != mids[0] or payload.get("machine_id") != mids[0]:
        return LicenseState(False, "MACHINE_ALIAS_MISMATCH")
    if not isinstance(machine_id, str) or machine_id not in mids:
        return LicenseState(False, "MACHINE_MISMATCH")
    iat, exp = payload.get("iat"), payload.get("exp")
    if (type(iat) is not int or type(exp) is not int or
        iat <= 0 or exp < 0 or (exp > 0 and exp <= iat)):
        return LicenseState(False, "INVALID_LICENSE_DATES")
    current = int(time.time()) if now is None else now
    if type(current) is not int:
        return LicenseState(False, "INVALID_CLOCK")
    if iat > current + MAX_FUTURE_SKEW:
        return LicenseState(False, "ISSUED_IN_FUTURE")
    if exp and current >= exp:
        return LicenseState(False, "EXPIRED")
    lic_id, customer = payload.get("lic_id"), payload.get("name")
    if (not isinstance(lic_id, str) or not 1 <= len(lic_id) <= 128 or
        not isinstance(customer, str) or not 1 <= len(customer) <= 128):
        return LicenseState(False, "INVALID_LICENSE_IDENTITY")
    return LicenseState(True, "ACTIVE", lic_id, customer, exp)


def load_installed_license(*, machine_id: str | None = None,
                           public_key_b64: str | None = None,
                           now: int | None = None,
                           path: Path | None = None) -> LicenseState:
    try:
        mid = machine_code() if machine_id is None else machine_id
        location = license_path() if path is None else Path(path)
        if not location.is_file():
            return LicenseState(False, "NOT_ACTIVATED")
        if location.stat().st_size > TOKEN_LIMIT:
            return LicenseState(False, "INVALID_TOKEN_LENGTH")
        token = location.read_text("utf-8")
        state = verify_token(token, mid, public_key_b64=public_key_b64, now=now)
        if state.valid or public_key_b64 is not None:
            return state
        from .online import verify_online_token
        online = verify_online_token(token, mid, now=now)
        if online.valid:
            return LicenseState(True, "ACTIVE", online.lic_id,
                                online.customer, online.expires_at)
        return state if state.code not in {
            "INVALID_SIGNATURE", "UNSUPPORTED_LICENSE_VERSION",
            "PRODUCT_EDITION_MISMATCH"
        } else LicenseState(False, online.status)
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        return LicenseState(False, type(exc).__name__.upper())


def activate_token(token: str, *, machine_id: str | None = None,
                   public_key_b64: str | None = None,
                   now: int | None = None,
                   path: Path | None = None) -> LicenseState:
    try:
        mid = machine_code() if machine_id is None else machine_id
        target = license_path() if path is None else Path(path)
    except (OSError, RuntimeError) as exc:
        return LicenseState(False, type(exc).__name__.upper())
    verified = verify_token(token, mid, public_key_b64=public_key_b64, now=now)
    from ..platforms.factory import services
    if services().platform == "MAC":
        from .online import verify_online_token, ONLINE_PUBLIC_KEY_B64
        result = verify_online_token(token, mid, public_key_b64=ONLINE_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64, now=now)
        verified = LicenseState(result.valid, result.status, result.lic_id, result.customer, result.expires_at)
    if not verified.valid:
        return verified
    # Atomic installation; never replace an existing valid token with invalid data.
    tmp = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         newline="\n", prefix=".lic-",
                                         suffix=".tmp", dir=target.parent,
                                         delete=False) as out:
            tmp = Path(out.name)
            out.write(token.strip())
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    except OSError:
        return LicenseState(False, "LICENSE_WRITE_FAILED")
    finally:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    return load_installed_license(machine_id=mid, public_key_b64=public_key_b64,
                                  now=now, path=target)


def activation_gate() -> bool:
    """Run in GUI thread after QApplication creation, before any Smaart UI."""
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QLabel, QPlainTextEdit,
        QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QTabWidget,
        QWidget
    )
    from PyQt6.QtGui import QGuiApplication, QPixmap, QIcon
    from PyQt6.QtCore import Qt, QObject, pyqtSignal
    import threading

    try:
        mid = machine_code()
    except RuntimeError as exc:
        QMessageBox.critical(None, "RemiX Duo License", str(exc))
        return False
    current = load_installed_license(machine_id=mid)
    if current.valid:
        return True

    from .online import activate_online_and_save

    class ActivationDialog(QDialog):
        busy = False
        def reject(self):
            if not self.busy:
                super().reject()

    class ActivationEvents(QObject):
        finished = pyqtSignal(object, str)

    dlg = ActivationDialog()
    events = ActivationEvents(dlg)
    dlg.setWindowTitle("RemiX Duo | Kích hoạt bản quyền")
    dlg.setMinimumSize(640, 600)
    dlg.resize(700, 660)
    dlg.setStyleSheet("""
    QDialog, QWidget {background:#15101F;color:#F5F1FC;font:14px 'Segoe UI';}
    QLabel {background:transparent;color:#D8CCE8;}
    QLabel#activationTitle {font-size:25px;font-weight:700;color:#F5F1FC;}
    QLabel#activationStatus {background:#251A34;border:1px solid #674D85;
        border-radius:10px;padding:12px;color:#E3D5F7;}
    QLabel#activationLogo {background:white;border-radius:10px;padding:8px;}
    QPlainTextEdit, QLineEdit {background:#0F0B17;color:#FAF7FF;
        border:1px solid #675477;border-radius:8px;padding:10px;
        font:15px 'Segoe UI';selection-background-color:#7C3AED;}
    QLineEdit {min-height:24px;}
    QLineEdit:read-only {color:#C4B5FD;font:13px Consolas;}
    QPlainTextEdit:focus, QLineEdit:focus {border:2px solid #C4B5FD;}
    QPushButton {background:#30233F;color:#F5F1FC;min-height:26px;
        border:1px solid #71558B;border-radius:8px;padding:9px 16px;
        font-weight:600;}
    QPushButton:hover {background:#49325E;border-color:#B69AE2;}
    QPushButton:focus {border:2px solid #D5BDFF;}
    QPushButton:disabled {background:#28212F;color:#A396B2;}
    QPushButton#activatePrimary {background:#7C3AED;color:white;border:1px solid #A78BFA;}
    QPushButton#activatePrimary:hover {background:#8B5CF6;}
    QTabWidget::pane {border:1px solid #544063;border-radius:10px;background:#1D1528;}
    QTabBar::tab {background:#251B31;color:#CDBEDB;padding:11px 20px;
        border:1px solid #544063;min-height:22px;}
    QTabBar::tab:selected {background:#49305F;color:white;border-bottom:3px solid #B89BFF;}
    """)
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(24, 24, 24, 20)
    layout.setSpacing(16)
    header = QHBoxLayout()
    header.setSpacing(20)
    logo_path = Path(__file__).resolve().parents[1] / 'resources' / 'remix_activation_logo.jpg'
    icon_path = Path(__file__).resolve().parents[1] / 'resources' / 'remixduo_app.ico'
    logo = QPixmap(str(logo_path))
    brand = QLabel()
    brand.setObjectName('activationLogo')
    brand.setFixedSize(154, 122)
    brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if not logo.isNull():
        brand.setPixmap(logo.scaled(138, 106, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation))
        dlg.setWindowIcon(QIcon(str(icon_path)))
    else:
        brand.setText('RemiX Audio')
    header.addWidget(brand)
    heading = QVBoxLayout()
    title = QLabel("Kích hoạt RemiX Duo")
    title.setObjectName('activationTitle')
    title.setWordWrap(True)
    heading.addWidget(title)
    description = QLabel("Nhập số điện thoại hoặc License ID đã đăng ký để sử dụng phần mềm trên máy này.")
    description.setWordWrap(True)
    heading.addWidget(description)
    header.addLayout(heading, 1)
    layout.addLayout(header)
    machine = QLineEdit(mid)
    machine.setReadOnly(True)
    machine.setAccessibleName('Mã máy dùng để cấp license')
    layout.addWidget(QLabel("Mã máy · Machine ID"))
    machine_row = QHBoxLayout()
    machine_row.setSpacing(10)
    machine_row.addWidget(machine, 1)
    copy_btn = QPushButton("Sao chép mã máy")
    copy_btn.clicked.connect(lambda: QGuiApplication.clipboard().setText(mid))
    machine_row.addWidget(copy_btn)
    layout.addLayout(machine_row)

    tabs = QTabWidget()
    layout.addWidget(tabs, 1)

    online_tab = QWidget()
    online_layout = QVBoxLayout(online_tab)
    online_layout.setContentsMargins(20, 20, 20, 20)
    online_layout.setSpacing(14)
    online_layout.addWidget(QLabel("Số điện thoại / License ID"))
    online_id = QLineEdit()
    online_id.setAccessibleName('Số điện thoại hoặc License ID')
    online_id.setPlaceholderText("Nhập số điện thoại hoặc mã khách hàng")
    online_layout.addWidget(online_id)
    online_note = QLabel(
        "Cần kết nối Internet. Nếu chưa được cấp license, hệ thống sẽ gửi "
        "yêu cầu đến quản trị viên để duyệt."
    )
    online_note.setWordWrap(True)
    online_layout.addWidget(online_note)
    online_activate = QPushButton("Kích hoạt online")
    online_activate.setObjectName('activatePrimary')
    online_layout.addWidget(online_activate, 0, Qt.AlignmentFlag.AlignRight)
    online_layout.addStretch(1)
    tabs.addTab(online_tab, "Kích hoạt online")

    offline_tab = QWidget()
    offline_layout = QVBoxLayout(offline_tab)
    offline_layout.setContentsMargins(20, 20, 20, 20)
    offline_layout.setSpacing(12)
    offline_layout.addWidget(QLabel("License token do kỹ thuật RemiX Audio cấp:"))
    entry = QPlainTextEdit()
    entry.setAccessibleName('License token do kỹ thuật RemiX Audio cấp')
    entry.setPlaceholderText("LIC1.xxxxx.yyyyy")
    offline_layout.addWidget(entry, 1)
    offline_activate = QPushButton("Kích hoạt token")
    offline_layout.addWidget(offline_activate, 0, Qt.AlignmentFlag.AlignRight)
    tabs.addTab(offline_tab, "Offline nâng cao")

    status = QLabel("Trạng thái: Chưa kích hoạt")
    status.setObjectName('activationStatus')
    status.setMinimumHeight(58)
    status.setAccessibleName('Kết quả kích hoạt')
    status.setWordWrap(True)
    layout.addWidget(status)
    row = QHBoxLayout()
    row.addStretch(1)
    cancel = QPushButton("Thoát")
    row.addWidget(cancel)
    layout.addLayout(row)
    cancel.clicked.connect(dlg.reject)

    def apply_online():
        if dlg.busy:
            return
        code = online_id.text().strip()
        if not code:
            status.setText("Vui lòng nhập Số điện thoại / License ID.")
            return
        online_activate.setEnabled(False)
        offline_activate.setEnabled(False)
        cancel.setEnabled(False)
        online_id.setEnabled(False)
        dlg.busy = True
        status.setText("Đang kết nối máy chủ… Bạn có thể di chuyển cửa sổ. Vui lòng chờ kết quả.")
        def run():
            try:
                result = activate_online_and_save(code, mid, path=license_path())
                error = ""
            except Exception as exc:
                result, error = None, type(exc).__name__
            try:
                events.finished.emit(result, error)
            except RuntimeError:
                pass  # Dialog/application already destroyed.
        threading.Thread(target=run, name='RemiX-license-online', daemon=True).start()

    def finish_online(result, error):
        dlg.busy = False
        online_activate.setEnabled(True)
        offline_activate.setEnabled(True)
        cancel.setEnabled(True)
        online_id.setEnabled(True)
        if error:
            status.setText("Không thể kết nối máy chủ. Hãy thử lại. (" + error + ")")
        else:
            status.setText(result.message or result.status)
            if result.valid:
                QMessageBox.information(dlg, "RemiX Duo", "Kích hoạt online thành công.")
                dlg.accept()

    events.finished.connect(finish_online, Qt.ConnectionType.QueuedConnection)

    def apply_offline():
        state = activate_token(entry.toPlainText())
        if state.valid:
            status.setText("Kích hoạt thành công.")
            dlg.accept()
        else:
            status.setText("Không thể kích hoạt: " + state.code)

    online_activate.clicked.connect(apply_online)
    offline_activate.clicked.connect(apply_offline)
    online_id.setFocus()
    return dlg.exec() == QDialog.DialogCode.Accepted
