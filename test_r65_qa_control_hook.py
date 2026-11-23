import json
from types import SimpleNamespace

from signal_tools_gui_v813 import ToolHub


class _Text:
    def __init__(self,value): self.value=value
    def text(self): return self.value


class _Hub:
    _poll_qa_control=ToolHub._poll_qa_control
    _qa_snapshot=ToolHub._qa_snapshot

    def __init__(self,path):
        self._qa_control_path=path
        self._qa_control_seq=-1
        self.active="phase"
        self.workspace_visible=True
        self._last_hwnd=123
        self.calls=[]
        self.engine=SimpleNamespace(align=lambda:self.calls.append("align"))
        self.eq=SimpleNamespace(result=None,summary=_Text("eq"),
                                compute=lambda:self.calls.append("eq"))
        self.fir=SimpleNamespace(result=None,summary=_Text("fir"),
                                 compute=lambda:self.calls.append("fir"))

    def select(self,mode):
        self.active=mode
        self.calls.append("select_"+mode)


def _write(path,seq,command):
    path.write_text(json.dumps({"seq":seq,"command":command}),encoding="utf-8")


def test_qa_control_is_allowlisted_and_acknowledged(tmp_path):
    control=tmp_path/"control.json"
    hub=_Hub(control)
    _write(control,1,"select_eq")
    hub._poll_qa_control()
    ack=json.loads((tmp_path/"control.json.ack.json").read_text(encoding="utf-8"))
    assert ack["ok"] is True
    assert ack["state"]["active"]=="eq"
    assert hub.calls==["select_eq"]

    _write(control,2,"export_eq")
    hub._poll_qa_control()
    ack=json.loads((tmp_path/"control.json.ack.json").read_text(encoding="utf-8"))
    assert ack["ok"] is False
    assert "not allowed" in ack["error"]
    assert hub.calls==["select_eq"]


def test_qa_control_rejects_replayed_sequence(tmp_path):
    control=tmp_path/"control.json"
    hub=_Hub(control)
    _write(control,7,"compute_fir")
    hub._poll_qa_control()
    hub._poll_qa_control()
    assert hub.calls==["fir"]
