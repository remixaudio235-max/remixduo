"""3-snapshot selection commit gate for Smaart's read-only Data Bar.

A full 108-row map is established by the existing initial scan. Every fresh
poll validates viewport tick pixels and status, but off-screen rows are cached:
three consecutive matching snapshots guard transient frame races, not proof
that off-screen pixels changed in between. Log this limitation explicitly.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class Decision:
    state:str  # pending|valid|invalid|transient
    pair:tuple[str,str]|None
    count:int|None
    stable:int
    reason:str
    changed:bool=False

class StableTickGate:
    def __init__(self,required=3,capacity=500):
        self.required=required
        self.history=deque(maxlen=capacity)
        self.signature=None
        self.stable=0
        self.committed=None
        self.last_state="transient"
        # Native provenance for production scanner. None remains supported
        # by older offscreen/synthetic regression fixtures.
        self.source_id=None
        self.last_frame_id=None

    def evaluate(self,result,active_names=(),unknown=0):
        status=str(getattr(result,"status",""))
        pair=getattr(result,"pair",None)
        rows=int(getattr(result,"rows",0) or 0)
        verified=int(getattr(result,"verified",0) or 0)
        names=tuple(active_names or ())
        source_id=getattr(result,"source_id",None)
        frame_id=getattr(result,"frame_id",None)
        witnessed=getattr(result,"observed_active_names",None)
        # A new Smaart HWND or TRF folder MUST NOT inherit an already
        # committed pair, even when both editions use the same filenames.
        if source_id is not None and source_id!=self.source_id:
            self.source_id=source_id
            self.last_frame_id=None
            self.signature=None
            self.stable=0
            self.committed=None
        if frame_id is not None:
            if (self.last_frame_id is not None and
                    frame_id<=self.last_frame_id):
                self.signature=None
                self.stable=0
                self.last_state="transient"
                decision=Decision("transient",None,None,0,
                                  "REPLAYED_OR_OUT_OF_ORDER_NATIVE_FRAME")
                self._log(decision,rows,verified,names)
                return decision
            self.last_frame_id=frame_id
        # A frame proves a selected trace only when its icon was observed
        # in that exact image, not merely read from a previously cached page.
        if witnessed is not None and not set(names).issubset(witnessed):
            self.signature=None
            self.stable=0
            self.last_state="transient"
            decision=Decision("transient",None,len(names),0,
                              "CHECKED_TRACE_NOT_VISIBLE_IN_FRAME")
            self._log(decision,rows,verified,names)
            return decision
        full=(rows>=2 and verified==rows
              and status.startswith(("Verified ","FULL SCAN "))
              and not unknown)
        if not full:
            self.signature=None
            self.stable=0
            self.last_state="transient"
            decision=Decision("transient",None,None,0,status or "no result")
            self._log(decision,rows,verified,names)
            return decision
        # Pair provided by scanner MUST correspond to the exactly two
        # enabled trace paths. Other counts must have pair=None.
        count=len(names)
        if count==2:
            expected=tuple(names)
            if not pair or tuple(pair)!=expected:
                self.signature=None
                self.stable=0
                decision=Decision("transient",None,count,0,"PAIR_PATH_MISMATCH")
                self._log(decision,rows,verified,names)
                return decision
            signature=("valid",expected)
        else:
            if pair is not None:
                self.signature=None
                self.stable=0
                decision=Decision("transient",None,count,0,"INVALID_COUNT_HAS_PAIR")
                self._log(decision,rows,verified,names)
                return decision
            signature=("invalid",names)
        if self.signature==signature:
            self.stable+=1
        else:
            self.signature=signature
            self.stable=1
        if self.stable<self.required:
            decision=Decision("pending",None,count,self.stable,
                              f"STABLE_{self.stable}/{self.required}")
        elif count==2:
            changed=self.committed!=signature[1]
            self.committed=signature[1]
            decision=Decision("valid",signature[1],count,self.stable,
                              "TWO_CHECKED_VERIFIED",changed)
        else:
            changed=self.committed is not None
            self.committed=None
            decision=Decision("invalid",None,count,self.stable,
                              "ACTIVE_COUNT_NE_2",changed)
        self.last_state=decision.state
        self._log(decision,rows,verified,names)
        return decision

    def _log(self,d,rows,verified,names):
        self.history.append({
            "t":round(time.monotonic(),3),
            "verified":verified,"rows":rows,
            "active_count":d.count,"active_names":names,
            "pair_candidate":d.pair,"state":d.state,
            "stable":d.stable,"reason":d.reason,
            "committed_pair":self.committed,
            "source_id":self.source_id,
            "frame_id":self.last_frame_id,
            "changed":d.changed
        })
