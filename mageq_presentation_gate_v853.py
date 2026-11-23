"""V8.53: bounded native MagEQ presentation gate.

Live drawing may bridge a *short* Data Bar 3/3 re-arm only while
the SAME immutable source is still the candidate. Independent native
pixel/viewport verification is still mandatory at paint time.
This function NEVER grants Export EQ or a new Auto EQ calculation.
"""
from __future__ import annotations
import time

# V8.107: one incomplete scan forces a 3/3 re-arm = 1 failed + 3 fresh polls
# (~0.2-0.35 s each live: 0.16 s throttle + PrintWindow ~155 ms). 0.44 s
# expired mid re-arm and blinked MagEQ/FIR/SUM. Bounded by the observer's
# own 1.5 s row-freshness proof; contradicting complete scans still stop.
TRANSIENT_DISPLAY_GRACE_S = 1.5


def presentation_tick_ok(observer, approved_token, last_good_at,
                         *, now=None, grace=TRANSIENT_DISPLAY_GRACE_S):
    if observer is None or approved_token is None:
        return False, last_good_at, "no_approved_source"
    # V8.109: a reset/uninitialized scanner cannot authorize stale pixels,
    # even if a test double or a race still holds the previous candidate.
    if not getattr(observer,"ready",False):
        return False,0.,"scanner_not_ready"
    if now is None:
        now=time.perf_counter()
    current=getattr(observer,"current_single",lambda:None)()
    if current==approved_token:
        return True,now,"verified_single"
    # A different, fully verified source is an immediate HARD stop.
    if current is not None and current!=approved_token:
        return False,0.,"different_verified_source"
    # invalidate_single() clears single_candidate for a different tick,
    # a 0/2 tick scan, an intentionally hidden Data Bar or foreground loss.
    candidate=getattr(observer,"single_candidate",None)
    if candidate!=approved_token[:3]:
        return False,0.,"different_or_unavailable_candidate"
    age=now-float(last_good_at or 0.)
    if age<0 or age>float(grace):
        return False,last_good_at,"candidate_expired"
    # A partial map with TWO known checked rows is already contradictory.
    # "unknown" third rows must not mask that explicit evidence. An
    # all-known 0/2+ count also hard-stops; only uncertainty may bridge.
    order=getattr(observer,"order",())
    states=getattr(observer,"states",{})
    if (not order or len(states)!=len(order) or
            any(v not in ("on","off","unknown") for v in states.values())):
        return False,0.,"scanner_map_unverified"
    known_on=sum(v=="on" for v in states.values())
    if known_on>1 or (all(v in ("on","off") for v in states.values())
                      and known_on!=1):
        return False,0.,"explicit_tick_count_changed"
    return True,last_good_at,"verified_candidate_rearming"


def token_still_current(observer, token, *, now=None):
    """V8.117: may a finished Auto EQ / FIR worker result be ACCEPTED?

    True when the exact token is verified, or the same immutable candidate is
    only being re-armed after an incomplete scan (no complete scan contradicts
    it). Callers still verify the file SHA; export keeps its strict 3/3 gate.
    Live: one missed Data Bar scan at the end of a 1-10 s design silently
    discarded the result ("Trace ... đã thay đổi").
    """
    if observer is None or token is None:
        return False
    current=getattr(observer,"current_single",lambda:None)()
    if current is not None:
        return current==token
    if now is None:
        now=time.perf_counter()
    ok,_,_=presentation_tick_ok(observer,token,now,now=now)
    return ok


def keep_preview_on_partial_scan(token,previous,candidate,count):
    """Do not destroy solved EQ on a missing/incomplete scan.

    Still disallow drawing/export until a separately verified token
    (or bounded presentation gate + fresh independent pixels).
    A COMPLETE count of 0 or >1 invalidates immediately.
    """
    # A verified 0/2+ tick count is a REAL selection change, even if
    # the scanner's candidate still reflects an older successful frame.
    # Only incomplete/unknown scans may retain solved EQ data.
    return (token is None and previous is not None and
            (count is None or count==1) and
            (candidate==previous[:3] or (candidate is None and count is None)))
