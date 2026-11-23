"""V8.162: native worker cadence contracts, not permission/identity bypass."""
import math
import pytest
from native_poll_budget_v8162 import (
    poll_due,MAG_ANCHOR_STEADY_SECONDS,TRACE_OFFSETS_STEADY_SECONDS,
    PHASE_AXIS_STEADY_SECONDS,MAG_ANCHOR_FIRST_RETRY_SECONDS)


@pytest.mark.parametrize("key_a,key_b",[
    (("suite", 123,("a.trf","b.trf")),("suite",123,("a.trf","c.trf"))),
    (("suite",123,0),("suite",124,0)),
    (("suite",123,("plot",1)),("suite",123,("plot",2))),
    (("suite",123,("sha",1)),("suite",123,("sha",2))),
    (("suite",123,("smooth",1/6)),("suite",123,("smooth",1/24))),
    (("suite",123,("viewport",1)),("suite",123,("viewport",2)))])
def test_new_source_host_revision_plot_smooth_or_viewport_is_immediate(key_a,key_b):
    assert poll_due(now=100.1,last_started=100.,key=key_b,last_key=key_a,
                    steady_seconds=MAG_ANCHOR_STEADY_SECONDS)


@pytest.mark.parametrize("budget",[
    MAG_ANCHOR_STEADY_SECONDS,TRACE_OFFSETS_STEADY_SECONDS,PHASE_AXIS_STEADY_SECONDS,
    MAG_ANCHOR_FIRST_RETRY_SECONDS])
def test_steady_source_respects_bound_and_refreshes(budget):
    key=("suite",123,("a.trf","b.trf"),0)
    assert not poll_due(now=100.+budget-.01,last_started=100.,key=key,
                        last_key=key,steady_seconds=budget)
    assert poll_due(now=100.+budget,last_started=100.,key=key,
                    last_key=key,steady_seconds=budget)


@pytest.mark.parametrize("now,last,budget",[(10.,0.,5.),(10.,11.,5.),
                                            (math.nan,5.,5.),(10.,5.,math.nan),
                                            (10.,5.,0.)])
def test_missing_first_request_clock_errors_and_bad_budget_retry(now,last,budget):
    assert poll_due(now=now,last_started=last,key=1,last_key=1,steady_seconds=budget)


def test_not_a_native_source_identity_or_export_gate():
    # Only an ordinary Python bool scheduling decision. This helper cannot
    # mint a native frame, SHA, HWND, source color or enable Export.
    value=poll_due(now=100.,last_started=99.,key=("a",1),
                   last_key=("a",1),steady_seconds=5.)
    assert value is False
    assert isinstance(value,bool)


def test_idle_and_drag_budget_have_separate_fast_path():
    from native_dual_y_v82 import native_pan_poll_interval
    assert native_pan_poll_interval("mag",99.)==.025
    assert native_pan_poll_interval("phase",99.)==.025
    assert .15<=native_pan_poll_interval(None,99.)<=.20
