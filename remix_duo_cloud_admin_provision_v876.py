"""Admin-PC-only Cloudflare RemiX Duo signing secret provisioning.

Generates a NEW Cloudflare issuer (not the V8.74 legacy local license
signing key), plus an administrator API token. Both are stored in DPAPI
encrypted files under the admin's LOCALAPPDATA, never in Git. Public key
can be safely compiled into the client when the matching Worker is online.

Optional upload sends secrets directly to an authenticated Wrangler
process via stdin. No secret is printed, stored in CLI args or git.
Requires D1 binding/real Cloudflare account login already configured.
"""
from __future__ import annotations
import argparse
import base64
import os
from pathlib import Path
import secrets
import subprocess
import sys


def store():
    root=os.environ.get("LOCALAPPDATA","")
    if not root or os.name!="nt":
        raise RuntimeError("ADMIN_WINDOWS_PROFILE_REQUIRED")
    return Path(root)/"RemiXAudioIssuer"/"DuoCloud"


def encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _write_protected(name, plain):
    import win32crypt
    folder=store()
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(name+".dpapi")
    encrypted=win32crypt.CryptProtectData(
        plain, "RemiX Duo Cloudflare server-only secret",None,None,None,0
    )
    with target.open("xb") as file:
        file.write(encrypted)
        file.flush()
        os.fsync(file.fileno())
    return target


def _read_protected(name):
    import win32crypt
    data=(store()/(name+".dpapi")).read_bytes()
    return win32crypt.CryptUnprotectData(data,None,None,None,0)[1]


def initialize():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    folder=store()
    folder.mkdir(parents=True,exist_ok=True)
    private=folder/"cloud_signer_pkcs8.dpapi"
    token=folder/"admin_token.dpapi"
    if not private.exists():
        key=Ed25519PrivateKey.generate()
        raw=key.private_bytes(encoding=serialization.Encoding.DER,
                              format=serialization.PrivateFormat.PKCS8,
                              encryption_algorithm=serialization.NoEncryption())
        _write_protected("cloud_signer_pkcs8",raw)
    if not token.exists():
        _write_protected("admin_token",secrets.token_urlsafe(48).encode("ascii"))
    return public_key()


def public_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import load_der_private_key
    key=load_der_private_key(_read_protected("cloud_signer_pkcs8"),password=None)
    return encode(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ))


def upload_secrets(config, *, wrangler="npx.cmd"):
    """Only run after independent admin confirms Cloudflare identity/D1.

    Wrangler must have an already-authenticated CLI identity for the exact
    Cloudflare account declared in config. Exits on any failed secret.
    """
    config=Path(config).resolve()
    if not config.is_file():
        raise RuntimeError("CLOUDFLARE_CONFIG_NOT_FOUND")
    for name,content in (
        ("LICENSE_ADMIN_TOKEN", _read_protected("admin_token")),
        ("LICENSE_ED25519_PRIVATE_PKCS8_B64",
         encode(_read_protected("cloud_signer_pkcs8")).encode("ascii")),
    ):
        command=[wrangler,"wrangler","secret","put",name,
                 "--config",str(config)]
        result=subprocess.run(command,input=content+b"\n",
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            cwd=str(config.parent),timeout=120,check=False)
        if result.returncode!=0:
            # Do not print tool stdout/stderr; they could contain secrets.
            raise RuntimeError("WRANGLER_SECRET_UPLOAD_FAILED_"+name)
    return "BOTH_CLOUDFLARE_SECRETS_UPLOADED"


def copy_admin_token():
    """Admin-only direct clipboard transfer; token never enters logs/CLI args."""
    import win32clipboard
    token=_read_protected("admin_token").decode("ascii")
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(token,win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    return "ADMIN_TOKEN_COPIED_TO_CLIPBOARD_CLEAR_AFTER_USE"


def main(argv=None):
    p=argparse.ArgumentParser(description="Cloudflare Duo signing-key provisioning")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init")
    sub.add_parser("public")
    sub.add_parser("copy-admin-token")
    deploy=sub.add_parser("upload-secrets")
    deploy.add_argument("--config",type=Path,required=True)
    args=p.parse_args(argv)
    if args.cmd=="init":
        print("CLOUD_PUBLIC_KEY_B64="+initialize())
    elif args.cmd=="public":
        print("CLOUD_PUBLIC_KEY_B64="+public_key())
    elif args.cmd=="copy-admin-token":
        print(copy_admin_token())
    else:
        print(upload_secrets(args.config))
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("ERROR="+type(error).__name__+" "+str(error),file=sys.stderr)
        raise SystemExit(2)
