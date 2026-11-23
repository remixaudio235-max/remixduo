import hashlib
import re

def machine_code():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography') as key:
            guid, _ = winreg.QueryValueEx(key, 'MachineGuid')
    except (OSError, ImportError) as exc:
        raise RuntimeError('MACHINE_GUID_UNAVAILABLE') from exc
    if not isinstance(guid,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',guid.strip()):
        raise RuntimeError('INVALID_WINDOWS_MACHINE_GUID')
    digest=hashlib.sha256(('RemiX-Duo/Windows/FPV2/'+guid.strip().lower()).encode('ascii')).hexdigest().upper()
    return 'DUO2-'+digest[:32]
