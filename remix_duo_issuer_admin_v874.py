"""V8.74 ADMIN ONLY - RemiX Duo Ed25519 issuer (Tune LIC1 v2 compatible).

The signing key is Windows-user-DPAPI-encrypted under LOCALAPPDATA,
NEVER in the source directory, client package or Git. Do not bundle this
script with the distributed Duo installer. Run only from the issuer PC.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time


def admin_store() -> Path:
    root = os.environ.get("LOCALAPPDATA", "")
    if not root or os.name != "nt":
        raise RuntimeError("WINDOWS_ISSUER_ONLY")
    return Path(root) / "RemiXAudioIssuer" / "Duo"


def key_path() -> Path:
    return admin_store() / "duo_signer_ed25519.dpapi"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _load_key():
    import win32crypt
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    encrypted = key_path().read_bytes()
    seed = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1]
    if len(seed) != 32:
        raise ValueError("INVALID_PRIVATE_KEY_SIZE")
    return Ed25519PrivateKey.from_private_bytes(seed)


def _public_b64(key) -> str:
    from cryptography.hazmat.primitives import serialization
    return b64(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ))


def initialize() -> str:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    import win32crypt
    p = key_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        return _public_b64(_load_key())
    secret = Ed25519PrivateKey.generate()
    seed = secret.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    protected = win32crypt.CryptProtectData(
        seed, "RemiX Duo signer - Windows user protected", None, None, None, 0
    )
    # Exclusive creation; no overwrite. File lives in current user's profile.
    with p.open("xb") as out:
        out.write(protected)
        out.flush()
        os.fsync(out.fileno())
    return _public_b64(secret)


def _machine(mid: str) -> str:
    mid = mid.strip().upper()
    if not re.fullmatch(r"DUO2-[0-9A-F]{32}", mid):
        raise ValueError("INVALID_DUO_MACHINE_ID")
    return mid


def issue(*, machine_ids: list[str], lic_id: str, name: str, days: int,
          output_path: Path, now: int | None = None, signer=None) -> str:
    if not 1 <= len(machine_ids) <= 2:
        raise ValueError("MACHINE_COUNT_MUST_BE_1_OR_2")
    mids = list(dict.fromkeys(_machine(mid) for mid in machine_ids))
    if not 1 <= len(mids) <= 2:
        raise ValueError("DUPLICATE_MACHINES")
    lic_id = lic_id.strip()
    name = name.strip()
    if not 1 <= len(lic_id) <= 128 or not 1 <= len(name) <= 128:
        raise ValueError("INVALID_CUSTOMER_OR_LICENSE_ID")
    if type(days) is not int or not 0 <= days <= 36500:
        raise ValueError("INVALID_LICENSE_DAYS")
    at = int(time.time()) if now is None else now
    if type(at) is not int or at <= 0:
        raise ValueError("INVALID_ISSUE_TIME")
    expires = 0 if days == 0 else at + days * 86400
    payload = {
        "v": 2, "fpv": 2, "platform": "WIN",
        "machine_ids": mids, "machine": mids[0], "machine_id": mids[0],
        "lic_id": lic_id, "edition": "DUO_PRO", "name": name,
        "iat": at, "exp": expires
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    key = _load_key() if signer is None else signer
    token = "LIC1." + b64(raw) + "." + b64(key.sign(raw))
    output = Path(output_path).resolve()
    if output.suffix.lower() != ".lic":
        raise ValueError("OUTPUT_MUST_BE_LIC")
    if output.exists():
        raise FileExistsError("REFUSE_TO_OVERWRITE_ISSUED_LICENSE")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as out:
        out.write(token + "\n")
    # Retain the Tune-style issuance ledger, NOT a log of private keys or tokens.
    ledger = admin_store() / "duo_license_ledger.tsv"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", newline="", encoding="utf-8") as out:
        csv.writer(out, delimiter="\t").writerow([
            datetime.fromtimestamp(at, timezone.utc).isoformat(),
            lic_id, name, "|".join(mids), "WIN", "DUO_PRO", days,
            at, expires, str(output)
        ])
    return str(output)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RemiX Duo admin-only license issuer")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Generate DPAPI-protected private key if absent")
    sub.add_parser("public", help="Print ONLY public verification key")
    issue_parser = sub.add_parser("issue", help="Sign DUO_PRO .lic")
    issue_parser.add_argument("--machine", required=True, action="append")
    issue_parser.add_argument("--license-id", required=True)
    issue_parser.add_argument("--customer", required=True)
    issue_parser.add_argument("--days", required=True, type=int)
    issue_parser.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    if args.command == "init":
        print("PUBLIC_KEY_B64=" + initialize())
        return 0
    if args.command == "public":
        print("PUBLIC_KEY_B64=" + _public_b64(_load_key()))
        return 0
    if args.command == "issue":
        print("LICENSE_FILE=" + issue(machine_ids=args.machine,
              lic_id=args.license_id, name=args.customer, days=args.days,
              output_path=args.output))
        return 0
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("ISSUER_ERROR=" + type(e).__name__ + ": " + str(e), file=sys.stderr)
        raise SystemExit(2)
