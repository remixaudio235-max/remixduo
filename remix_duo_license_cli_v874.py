"""Safe RemiX Duo end-user license status and activation CLI (no issuer keys)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from remix_duo_license_v874 import machine_code, load_installed_license, activate_token


def main(argv=None):
    p = argparse.ArgumentParser(description="RemiX Duo License / Key Active")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("machine")
    sub.add_parser("status")
    a = sub.add_parser("activate")
    a.add_argument("--file", type=Path, required=True)
    args = p.parse_args(argv)
    if args.command == "machine":
        print(machine_code())
        return 0
    if args.command == "status":
        state = load_installed_license()
    else:
        source = args.file.resolve()
        if not source.is_file() or source.stat().st_size > 12000:
            print('{"valid":false,"code":"LICENSE_FILE_NOT_READABLE"}')
            return 2
        state = activate_token(source.read_text(encoding="utf-8"))
    print(json.dumps({
        "valid": state.valid, "code": state.code,
        "edition": "DUO_PRO" if state.valid else None,
        "license_id": state.lic_id, "expires_at": state.expires_at,
    }, ensure_ascii=False))
    return 0 if state.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
