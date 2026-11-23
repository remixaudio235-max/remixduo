"""V8.7 signed solver -> positive delay target validation."""
import numpy as np
from pathlib import Path
from trf_core import auto_align,matched,compute_sum,synthetic
from positive_delay_route_v87 import route_candidate

def verify(a,b,expect_delay_trace,expect_invert,maximum_ms=30.0):
    c=auto_align(a,b,lf=85.,hf=1300.,max_delay_ms=maximum_ms,
                 step_ms=.1,top_k=3)
    assert c,c
    r=route_candidate(c[0])
    print("CASE",a.name,b.name,"SIGNED",c[0].delay_ms,
          "TARGET",r.delay_trace,"REF",r.reference_trace,
          "DELAY_POS",r.delay_ms,"INVERT_TARGET",r.invert_target,
          "SCORE",r.score_db,flush=True)
    assert r.delay_trace==expect_delay_trace,(r,expect_delay_trace)
    assert r.invert_target==expect_invert,(r,expect_invert)
    assert r.delay_ms>=0
    assert abs(r.delay_ms-12.3)<.15,(r,c)
    # Realigned SUM has the same magnitude as signed advanced model.
    original=compute_sum(a,b,c[0].delay_ms,c[0].invert_trace2)
    reordered=(a,b) if r.reference_index==0 else (b,a)
    corrected=compute_sum(*reordered,r.delay_ms,r.invert_target)
    assert np.allclose(original.hz,corrected.hz)
    assert np.max(np.abs(original.mag_db-corrected.mag_db))<1e-6
    return r

f=np.geomspace(20,20000,750)
verify(synthetic("T1_late_12_3",f,delay_ms=12.3),
       synthetic("T2_early",f),2,False)
verify(synthetic("T1_early",f),
       synthetic("T2_late_12_3",f,delay_ms=12.3),1,False)
verify(synthetic("T1_early",f),
       synthetic("T2_late_inverted",f,delay_ms=12.3,invert=True),1,True)
verify(synthetic("T1_late_inverted",f,delay_ms=12.3,invert=True),
       synthetic("T2_early",f),2,True)
print("V87_POSITIVE_ROUTE_SYNTHETIC_ALL_PASS")
