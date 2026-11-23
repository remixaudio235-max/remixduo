import hashlib
import plistlib
import re
import subprocess

def hash_hardware_uuid(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value.strip()):
        raise RuntimeError('MAC_HARDWARE_UUID_UNAVAILABLE')
    # No CPU architecture: native arm64 and Rosetta share one entitlement.
    value=value.strip().lower()
    return 'DUOM4-'+hashlib.sha256(('RemiX-Duo/macOS/FPV4/'+value).encode('ascii')).hexdigest().upper()

def machine_code():
    try:
        response=subprocess.run(['/usr/sbin/ioreg','-a','-rd1','-c','IOPlatformExpertDevice'],
                                capture_output=True,check=True,timeout=5)
        records=plistlib.loads(response.stdout)
        return hash_hardware_uuid(records[0].get('IOPlatformUUID'))
    except (OSError,ValueError,IndexError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        raise RuntimeError('MAC_HARDWARE_UUID_UNAVAILABLE') from exc
