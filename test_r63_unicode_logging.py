import io,sys
from pathlib import Path
import pytest
from gui_watchdog_v8118 import configure_unicode_output

class CP1252TTY:
    def isatty(self):return True
    def write(self,txt):return len(txt.encode("cp1252"))
    def flush(self):pass

def test_frozen_gui_utf8_log_even_when_tty_claims_true(monkeypatch,tmp_path):
    bad=CP1252TTY()
    with pytest.raises(UnicodeEncodeError):
        bad.write("Hiệu chỉnh 100%")
    monkeypatch.setattr(sys,"frozen",True,raising=False)
    original=(sys.stdout,sys.stderr)
    file=tmp_path/"overlay.log"
    try:
        with open(file,"a",encoding="utf-8",buffering=1) as log:
            sys.stdout=bad;sys.stderr=bad
            configure_unicode_output(log)
            assert sys.stdout is log and sys.stderr is log
            print("V8124_FIR_OK phase | Hiệu chỉnh 100%")
            print("FIR Phase TOTAL HOLD: coherence≥0.65 chỉ 105/215 bins",file=sys.stderr)
    finally:
        sys.stdout,sys.stderr=original
    data=file.read_text(encoding="utf-8")
    assert "Hiệu chỉnh 100%" in data
    assert "coherence≥0.65 chỉ 105/215 bins" in data

def test_developer_tty_reconfigures_utf8_without_stealing_console(monkeypatch):
    class TTY:
        def __init__(self):self.encoding="cp1252"
        def isatty(self):return True
        def reconfigure(self,encoding,errors):self.encoding=encoding;self.errors=errors
    fake=TTY()
    monkeypatch.delattr(sys,"frozen",raising=False)
    original=(sys.stdout,sys.stderr)
    try:
        sys.stdout=fake;sys.stderr=fake
        configure_unicode_output(io.StringIO())
        assert sys.stdout is fake and sys.stderr is fake
        assert fake.encoding=="utf-8" and fake.errors=="backslashreplace"
    finally:sys.stdout,sys.stderr=original

def test_redirect_disabled_leaves_existing_streams(monkeypatch):
    monkeypatch.setattr(sys,"frozen",True,raising=False)
    original=(sys.stdout,sys.stderr)
    fake=CP1252TTY()
    try:
        sys.stdout=fake;sys.stderr=fake
        configure_unicode_output(io.StringIO(),redirect=False)
        assert sys.stdout is fake and sys.stderr is fake
    finally:sys.stdout,sys.stderr=original

def test_frozen_no_console_is_safe(monkeypatch):
    monkeypatch.setattr(sys,"frozen",True,raising=False)
    original=(sys.stdout,sys.stderr)
    try:
        sys.stdout=None;sys.stderr=None
        log=io.StringIO()
        configure_unicode_output(log)
        assert sys.stdout is log and sys.stderr is log
        print("Thành công: Đã tạo FIR")
        assert "Đã tạo FIR" in log.getvalue()
    finally:sys.stdout,sys.stderr=original
