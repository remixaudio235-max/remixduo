"""V8.162: evidence-bound budget for expensive native screenshot workers.

Never reuse a captured frame as fresh proof. This module throttles only the
request cadence; each accepted result still goes through the original strict
HWND, source, file-revision and viewport checks.
"""
from __future__ import annotations
import math


def poll_due(*,now,last_started,key,last_key,steady_seconds):
    """Schedule immediately when the verification identity changes.

    A cached key is only a cadence hint; it is never a native-identity proof.
    Invalid/rolled-over clocks fail safe by allowing a fresh request.
    """
    if not (math.isfinite(now) and math.isfinite(last_started)
            and math.isfinite(steady_seconds) and steady_seconds>0):
        return True
    if key != last_key:
        return True
    if last_started<=0. or now<last_started:
        return True
    return now-last_started>=steady_seconds


def native_proof_busy(*futures):
    """True while a native screenshot/axis/offset proof worker is still live.

    Never confuses a completed Future with proof; stale-result rejection and
    native source identity remain the caller's responsibility.
    """
    return any(future is not None and not future.done() for future in futures)


MAG_ANCHOR_STEADY_SECONDS=5.0
# 66-ms coordinator + native image fit normally finishes much sooner than
# the old 1.15-s first retry; fast fail-closed retries for STATIC source.
MAG_ANCHOR_FIRST_RETRY_SECONDS=.25
MAG_ANCHOR_RECOVERY_RETRY_SECONDS=.65
MAG_ANCHOR_HOLD_RETRY_SECONDS=1.50
TRACE_OFFSETS_STEADY_SECONDS=4.0
PHASE_AXIS_STEADY_SECONDS=1.65
