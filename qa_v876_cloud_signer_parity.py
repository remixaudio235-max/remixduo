"""Verify DPAPI-staged Cloudflare signer and pinned public key match.

Signs only a synthetic test certificate in memory, NOT a customer key.
Never writes/signs production license, never prints signing secret or token.
"""
from __future__ import annotations
from cryptography.hazmat.primitives.serialization import load_der_private_key
import base64
import json
import time
from remix_duo_cloud_admin_provision_v876 import _read_protected,public_key
from remix_duo_cloud_license_v876 import CLOUD_PUBLIC_KEY_B64,verify_cloud_certificate

key=load_der_private_key(_read_protected("cloud_signer_pkcs8"),password=None)
assert public_key()==CLOUD_PUBLIC_KEY_B64
mid="DUO2-"+"A"*32
now=int(time.time())
claims=dict(v=2,fpv=2,platform="WIN",issuer="CLOUDFLARE",
  edition="DUO_PRO",machine_ids=[mid],machine=mid,machine_id=mid,
  lic_id="QA-ONLY-NO-CUSTOMER-LICENSE",name="QA",iat=now,
  exp=now+72*3600)
raw=json.dumps(claims,separators=(",",":")).encode()
enc=lambda x:base64.urlsafe_b64encode(x).rstrip(b"=").decode("ascii")
token="LIC1."+enc(raw)+"."+enc(key.sign(raw))
result=verify_cloud_certificate(token,mid,now=now)
assert result.valid and result.code=="ACTIVE"
print("CLOUD_DPAPI_SIGNER_PUBLIC_PIN_PARITY_PASS")
