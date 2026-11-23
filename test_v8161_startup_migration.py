"""V8.161: installer may migrate ONLY exact RemiX V8.87 source Run entry."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import smaart_postinstall_v875 as post

OLD = (r"C:\rdv311\Scripts\pythonw.exe "
       r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA"
       r"\smaart_autostart_v875.py --watch")
NEW = r"C:\Users\Administrator\AppData\Local\Programs\RemiX Duo\RemiXDuoSmaartWatcher.exe --watch"

@pytest.mark.parametrize("value,expected", [
    (OLD, True),
    ('"C:\\Program Files\\Python311\\pythonw.exe" '
     '"D:\\REMIX_AUTO_ALIGN_V6_DEV\\windows_v8_87_MAC_OVERLAY_QA\\smaart_autostart_v875.py" --watch',True),
    (OLD.replace("v8_87","v8_86"),False),
    (OLD.replace("pythonw.exe","powershell.exe"),False),
    (OLD.replace("REMIX_AUTO_ALIGN_V6_DEV","SOMEONE_ELSES_PROJECT"),False),
    (OLD.replace("--watch","--disable"),False),
    (OLD+" && echo surprise",False),
    ("foreign",False),
    (None,False),
])
def test_only_exact_owned_legacy_watcher_is_migratable(value,expected):
    assert post._owned_v887_startup(value) is expected

def test_atomic_migration_backups_then_writes(monkeypatch,tmp_path):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setattr(post,"watcher_command",lambda:NEW)
    monkeypatch.setattr(post,"registered_command",lambda:OLD)
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path))
    events=[]
    class FakeKey:
        def __enter__(self):return self
        def __exit__(self,*a):pass
    class FakeReg:
        REG_SZ=1
        @staticmethod
        def SetValueEx(key,name,reserved,typ,value):
            backups=list((tmp_path/"RemiXDuo"/"backups").glob("*.json"))
            assert len(backups)==1, "MUST_BACKUP_BEFORE_WRITE"
            obj=json.loads(backups[0].read_text(encoding="utf-8"))
            assert obj["previous_command"]==OLD
            events.append((name,value))
    monkeypatch.setitem(sys.modules,"winreg",FakeReg)
    monkeypatch.setattr(post,"_reg_open",lambda create=False:FakeKey())
    assert post.configure_autostart(True)=="MIGRATED_OWN_V887_SOURCE_ENTRY"
    assert events==[(post.REGISTRY_NAME,NEW)]

def test_foreign_is_never_replaced(monkeypatch):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setattr(post,"watcher_command",lambda:NEW)
    monkeypatch.setattr(post,"registered_command",lambda:"other-company-watcher")
    monkeypatch.setattr(post,"_backup_legacy_startup",lambda _ :pytest.fail("foreign backup"))
    assert post.configure_autostart(True)=="OTHER_INSTALL_OWNS_STARTUP_ENTRY"
    assert post.configure_autostart(False)=="OTHER_INSTALL_OWNS_STARTUP_ENTRY"

def test_backup_failure_cannot_mutate_registry(monkeypatch):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setattr(post,"watcher_command",lambda:NEW)
    monkeypatch.setattr(post,"registered_command",lambda:OLD)
    def fail(_):raise OSError("readonly")
    monkeypatch.setattr(post,"_backup_legacy_startup",fail)
    assert post.configure_autostart(True)=="LEGACY_BACKUP_FAILED"

def test_migration_remains_disabled_until_next_logon(monkeypatch,capsys):
    monkeypatch.setattr(post,"configure_autostart",lambda enabled:"MIGRATED_OWN_V887_SOURCE_ENTRY")
    monkeypatch.setattr(post,"watcher_command",lambda:NEW)
    monkeypatch.setattr(post.subprocess,"Popen",lambda *a,**k:pytest.fail("must not autostart"))
    assert post.main(["--enable","--start-now"])==0
    assert "NEXT_USER_LOGON_ONLY" in capsys.readouterr().out


def test_unconditional_cleanup_only_deletes_exact_legacy(monkeypatch,tmp_path):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path))
    monkeypatch.setattr(post,"registered_command",lambda:OLD)
    calls=[]
    class Reg:
        REG_SZ=1
        @staticmethod
        def QueryValueEx(key,name):return OLD,1
        @staticmethod
        def DeleteValue(key,name):calls.append(name)
    class Key:
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setitem(sys.modules,"winreg",Reg)
    monkeypatch.setattr(post,"_reg_open",lambda create=False:Key())
    assert post.cleanup_legacy_autostart()=="REMOVED_OWN_V887_SOURCE_ENTRY"
    assert calls==[post.REGISTRY_NAME]
    assert len(list((tmp_path/"RemiXDuo"/"backups").glob("*.json")))==1

def test_unconditional_cleanup_does_not_touch_foreign(monkeypatch):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setattr(post,"registered_command",lambda:"foreign")
    monkeypatch.setattr(post,"_backup_legacy_startup",lambda _:pytest.fail("backup foreign"))
    assert post.cleanup_legacy_autostart()=="FOREIGN_ENTRY_UNCHANGED"

def test_cleanup_rechecks_value_before_delete(monkeypatch,tmp_path):
    monkeypatch.setattr(post.sys,"platform","win32")
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path))
    monkeypatch.setattr(post,"registered_command",lambda:OLD)
    class Reg:
        REG_SZ=1
        @staticmethod
        def QueryValueEx(key,name):return "changed-after-backup",1
        @staticmethod
        def DeleteValue(key,name):pytest.fail("should not delete")
    class Key:
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setitem(sys.modules,"winreg",Reg)
    monkeypatch.setattr(post,"_reg_open",lambda create=False:Key())
    assert post.cleanup_legacy_autostart()=="ENTRY_CHANGED_DURING_CLEANUP"
