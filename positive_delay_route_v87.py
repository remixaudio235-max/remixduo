"""Convert signed TF relative alignment into a realizable positive DSP delay.

Original signed convention from trf_core.auto_align(TRACE1,TRACE2):
  H1 + s * H2 * exp(-j*omega*d), where d may be negative.

Physically realizable reference selection:
  d>=0: keep TRACE1, delay(+d) TRACE2.
  d<0 : keep TRACE2, delay(-d) TRACE1.

For inverse polarity the inverted TRACE is the delayed target. The
complex SUM of the two descriptions can differ by a common phase rotation
(and 180 degrees if polarity convention swaps), but magnitudes and
relative acoustic alignment remain equivalent. All labels refer to a
model-only preview, NEVER direct changes to Smaart or a hardware DSP.
"""
from dataclasses import dataclass
import math
from trf_core import Candidate

@dataclass(frozen=True)
class DelayRoute:
    reference_index:int
    delay_target_index:int
    delay_ms:float
    invert_target:bool
    score_db:float
    signed_solver_shift_ms:float

    @property
    def reference_trace(self):
        return self.reference_index+1

    @property
    def delay_trace(self):
        return self.delay_target_index+1


def route_candidate(candidate:Candidate)->DelayRoute:
    signed=float(candidate.delay_ms)
    if not math.isfinite(signed):
        raise ValueError("Invalid shift: nonfinite")
    # Stable direction when exactly zero; default to TRACE 2.
    target=1 if signed>=0 else 0
    ref=1-target
    return DelayRoute(ref,target,abs(signed),
                      bool(candidate.invert_trace2),
                      float(candidate.score_db),signed)
