"""V8.179 QA regression: static TRF first paint prioritizes strict MAG proof.

No native proof is cached; only which worker runs first changes. After
successful MAG calibration the ordinary serialized Phase/MAG/offset order
remains unchanged. Retry intervals never alter acceptance criteria.
"""
from concurrent.futures import Future
from native_poll_budget_v8162 import (
 MAG_ANCHOR_FIRST_RETRY_SECONDS,MAG_ANCHOR_RECOVERY_RETRY_SECONDS,
 MAG_ANCHOR_HOLD_RETRY_SECONDS,MAG_ANCHOR_STEADY_SECONDS,
 native_proof_busy,poll_due)
from overlay_v7 import App

class Fake:
 def __init__(self,verified):
  self._mag_anchor_verified=verified
  self.axis_drag=None
  self.axis_future=self.mag_anchor_future=self.offset_future=None
  self.calls=[]
 def _schedule_mag_ref_anchor(self,target):
  if "mag" not in self.calls:
   self.calls.append("mag")
   self.mag_anchor_future=Future()
 def _schedule_absolute_axis_calibration(self,target):
  if "phase" not in self.calls:
   self.calls.append("phase")
   self.axis_future=Future()
 def _schedule_trace_offsets(self,target):
  if "offset" not in self.calls:
   self.calls.append("offset")
   self.offset_future=Future()

def test_smaart8_static_unverified_mag_first_not_phase():
 d=Fake(False)
 App._schedule_steady_native_proofs(d,object())
 assert d.calls==["mag"]
 assert native_proof_busy(d.mag_anchor_future)
 # phase cannot concurrently steal CPU from pending native MAG capture.
 App._schedule_steady_native_proofs(d,object())
 assert d.calls==["mag"]

def test_after_native_mag_acceptance_other_axis_can_run():
 d=Fake(True)
 App._schedule_steady_native_proofs(d,object())
 assert d.calls==["phase"]
 d.axis_future.set_result(None)
 App._schedule_steady_native_proofs(d,object())
 assert d.calls==["phase","mag"]
 d.mag_anchor_future.set_result(None)
 App._schedule_steady_native_proofs(d,object())
 assert d.calls==["phase","mag","offset"]

def test_no_premature_retry_while_fresh_worker_busy():
 assert .15<=MAG_ANCHOR_FIRST_RETRY_SECONDS<=.35
 assert MAG_ANCHOR_FIRST_RETRY_SECONDS<MAG_ANCHOR_RECOVERY_RETRY_SECONDS
 assert MAG_ANCHOR_RECOVERY_RETRY_SECONDS<MAG_ANCHOR_HOLD_RETRY_SECONDS
 assert MAG_ANCHOR_HOLD_RETRY_SECONDS<MAG_ANCHOR_STEADY_SECONDS
 key=("smaart8",123,"immutable_sha")
 for interval in (MAG_ANCHOR_FIRST_RETRY_SECONDS,
                  MAG_ANCHOR_RECOVERY_RETRY_SECONDS,
                  MAG_ANCHOR_HOLD_RETRY_SECONDS):
  assert not poll_due(now=100+interval-.01,last_started=100,
                      key=key,last_key=key,steady_seconds=interval)
  assert poll_due(now=100+interval,last_started=100,
                  key=key,last_key=key,steady_seconds=interval)

def test_changed_source_or_theme_rearms_immediately_even_after_steady():
 assert poll_due(now=100.1,last_started=100.,key=("smaart8","dark",7),
                 last_key=("smaart8","light",7),
                 steady_seconds=MAG_ANCHOR_STEADY_SECONDS)
