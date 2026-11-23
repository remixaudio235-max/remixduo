import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

def test_selection_requires_current_complete_window_evidence():
    from remix_duo.platforms.contracts import WindowRef, SelectionEvidence
    w=WindowRef('darwin',123,'start-123','AX:1')
    e=SelectionEvidence(w,('a','b'),100,True,('a','b'))
    assert e.verified_pair(w,100.2)==('a','b')
    assert e.verified_pair(w,102) is None
    assert e.verified_pair(WindowRef('darwin',123,'new-process','AX:1'),100.2) is None
    assert SelectionEvidence(w,('a','b'),100,False,('a','b')).verified_pair(w,100.2) is None
    assert SelectionEvidence(w,('a','b'),100,True,('a',)).verified_pair(w,100.2) is None
    assert e.verified_pair(w,99) is None

def test_pixel_transform_preserves_retina_and_negative_monitor_origin():
    from remix_duo.platforms.contracts import PixelTransform
    t=PixelTransform(logical_origin=(-1440,100),physical_origin=(-2880,200),scale=2)
    assert t.to_physical((-1430,110))==(-2860,220)
    assert t.to_logical((-2860,220))==(-1430,110)
    with pytest.raises(ValueError): PixelTransform((0,0),(0,0),0)

def test_paths_are_platform_specific_and_cwd_independent(tmp_path):
    from remix_duo.platforms.paths import app_paths
    assert app_paths('win32',environ={'LOCALAPPDATA':str(tmp_path)},home=tmp_path).license == tmp_path/'RemiXAudio/Duo/license.lic'
    mac=app_paths('darwin',environ={},home=tmp_path)
    assert mac.license == tmp_path/'Library/Application Support/RemiXAudio/Duo/license.lic'
    assert mac.resource('remix_activation_logo.jpg').is_file()
    with pytest.raises(ValueError): mac.resource('../secret')
    with pytest.raises(RuntimeError): app_paths('linux',environ={},home=tmp_path)

def test_mac_identity_is_product_scoped_architecture_independent():
    from remix_duo.platforms.macos.identity import hash_hardware_uuid
    a=hash_hardware_uuid('9D54A01C-F239-4F32-9987-771628021001')
    assert a==hash_hardware_uuid('9d54a01c-f239-4f32-9987-771628021001')
    assert a.startswith('DUOM4-') and len(a)==70
    assert '9D54' not in a
    with pytest.raises(RuntimeError): hash_hardware_uuid('')

def test_real_process_lock_rejects_contention_and_releases(tmp_path):
    from remix_duo.platforms.factory import services
    backend=services()
    name='RemiXDuo.Test.'+str(os.getpid())
    lock=backend.acquire_lock(name,tmp_path)
    assert lock is not None
    code='''from pathlib import Path
from remix_duo.platforms.factory import services
import sys
lock=services().acquire_lock(sys.argv[1],Path(sys.argv[2]))
print('acquired' if lock is not None else 'busy')
if lock: lock.close()
'''
    def probe():
        r=subprocess.run([sys.executable,'-c',code,name,str(tmp_path)],capture_output=True,text=True,
                         env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2]/'src')})
        assert r.returncode==0,r.stderr
        return r.stdout.strip()
    assert probe()=='busy'
    lock.close()
    assert probe()=='acquired'

def test_mac_backend_never_reports_native_ready_from_permission_alone():
    from remix_duo.platforms.macos.services import MacServices
    cap=MacServices().native_capability()
    assert not cap.ready and 'HOLD' in cap.reason
    with pytest.raises(RuntimeError,match='HOLD'): MacServices().read_selection(None)

def test_windows_fingerprint_matches_existing_bytes(monkeypatch):
    if sys.platform!='win32': pytest.skip('Windows registry contract')
    from remix_duo.platforms.windows.identity import machine_code
    import remix_duo_license_v874 as old
    assert machine_code()==old.machine_code()

def test_legacy_singleton_uses_real_backend_lease(monkeypatch,tmp_path):
    import single_instance_v823 as old
    from remix_duo.platforms import factory,paths
    lease=object();calls=[]
    class Backend:
        def acquire_lock(self,name,directory):
            calls.append((name,directory));return lease
    monkeypatch.setattr(factory,'services',lambda:Backend())
    monkeypatch.setattr(paths,'app_paths',lambda:type('Paths',(),{'data':tmp_path})())
    assert old.acquire_instance() is lease
    assert calls==[('RemiXSignalSmaartDataBarV823',tmp_path)]
