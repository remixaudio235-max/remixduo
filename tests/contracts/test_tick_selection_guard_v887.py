"""V8.87+ macOS native selection gate: no stale or ambiguous AX evidence."""
from dataclasses import replace
import math

from remix_duo.platforms.contracts import SelectionEvidence, WindowRef


def ref():
    return WindowRef('darwin', 1234, 'process-start', 'window-20')


def evidence(*selected, visible=('a.trf', 'b.trf', 'c.trf'), complete=True):
    return SelectionEvidence(ref(), tuple(selected), 100.0, complete, tuple(visible))


def test_single_trace_for_autoeq_and_fir():
    e = evidence('a.trf')
    assert e.verified_selected(ref(), 100.1, 1) == ('a.trf',)
    assert e.verified_selected(ref(), 100.1, 2) is None
    assert e.verified_pair(ref(), 100.1) is None


def test_two_trace_phase_and_existing_pair_api():
    e = evidence('a.trf', 'b.trf')
    assert e.verified_selected(ref(), 100.1, 2) == ('a.trf', 'b.trf')
    assert e.verified_pair(ref(), 100.1) == ('a.trf', 'b.trf')
    assert e.verified_selected(ref(), 100.1, 1) is None


def test_rejects_identity_age_and_incomplete_scan():
    e = evidence('a.trf')
    assert e.verified_selected(None, 100.1, 1) is None
    assert e.verified_selected(replace(ref(), process_started='other'), 100.1, 1) is None
    assert e.verified_selected(replace(ref(), opaque_id='other'), 100.1, 1) is None
    assert e.verified_selected(ref(), 99.9, 1) is None
    assert e.verified_selected(ref(), 102.0, 1) is None
    assert e.verified_selected(ref(), math.nan, 1) is None
    assert replace(e, complete=False).verified_selected(ref(), 100.1, 1) is None


def test_rejects_ghost_duplicate_and_unverified_trace():
    assert evidence('ghost.trf').verified_selected(ref(), 100.1, 1) is None
    assert evidence('a.trf', 'a.trf').verified_selected(ref(), 100.1, 2) is None
    assert evidence('a.trf', visible=('a.trf', 'a.trf')).verified_selected(ref(), 100.1, 1) is None
    assert evidence('a.trf', visible=('b.trf',)).verified_selected(ref(), 100.1, 1) is None
    assert evidence('a.trf').verified_selected(ref(), 100.1, 3) is None
    assert evidence('a.trf').verified_selected(ref(), 100.1, True) is None
