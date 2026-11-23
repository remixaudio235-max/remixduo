"""V8.117: a finished Auto EQ / FIR result survives one missed Data Bar scan.

Offscreen run on 18 real TRFs (2026-11-11): suspend_single_transient() at
the moment the worker finished made EQ show "Trace hoặc Fs Smaart đã thay
đổi: bỏ Auto EQ cũ" and FIR "Trace/Fs/taps thay đổi trong khi tính FIR",
although the trace never changed. Designs take 0.3-10 s.
"""
import pytest
from mageq_presentation_gate_v853 import token_still_current


class Obs:
    def __init__(self,token):
        self.single_tick=token;self.single_candidate=token[:3]
        self.ready=True;self.order=[token[0]];self.states={0:"on"}
    def current_single(self):return self.single_tick


T=("c:/a.trf",10,99,4)


def test_verified_token_is_current():
    assert token_still_current(Obs(T),T)


def test_rearming_same_candidate_is_accepted():
    o=Obs(T);o.single_tick=None            # one incomplete scan
    assert token_still_current(o,T)


@pytest.mark.parametrize("change",["other_verified","other_candidate","zero","two","unready"])
def test_contradictions_still_reject(change):
    o=Obs(T);o.single_tick=None
    if change=="other_verified":o.single_tick=("c:/b.trf",1,1,5)
    if change=="other_candidate":o.single_candidate=("c:/b.trf",1,1)
    if change=="zero":o.states={0:"off"}
    if change=="two":o.order=["a","b"];o.states={0:"on",1:"on"}
    if change=="unready":o.ready=False
    assert not token_still_current(o,T)


def test_none_inputs_reject():
    assert not token_still_current(None,T)
    assert not token_still_current(Obs(T),None)


def test_finish_paths_use_rearm_acceptance():
    src=open("signal_tools_gui_v813.py",encoding="utf-8").read()
    eq=src.split("class EQDialog",1)[1].split("class FIRDialog",1)[0]
    fir=src.split("class FIRDialog",1)[1]
    assert "token_still_current" in eq.split("def _finish",1)[1].split("def ",1)[0]
    assert "token_still_current" in fir.split("def _finish",1)[1].split("    def ",1)[0]
