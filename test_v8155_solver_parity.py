"""V8.155: shared-rotation solver must remain numerically identical."""
from dataclasses import replace
import numpy as np
import pytest
from remix_duo.core.traces import (synthetic,auto_align,alignment_delays,
    alignment_penalty_db,alignment_roi,ALIGN_CHUNK,Candidate)

def reference(a,b,lf,hf,max_delay_ms,step_ms=.1,top_k=4):
    f,h1,h2,coh=alignment_roi(a,b,lf,hf,.6)
    if len(f)<12:return []
    weights=coh**2
    delays=alignment_delays(max_delay_ms,step_ms)
    results=[]
    for invert in (False,True):
        scores=np.empty(len(delays))
        for k in range(0,len(delays),ALIGN_CHUNK):
            ds=delays[k:k+ALIGN_CHUNK]
            scores[k:k+len(ds)]=(alignment_penalty_db(f,h1,h2,ds,invert)@weights)/weights.sum()
        results.extend(Candidate(float(d),invert,float(s),len(f)) for d,s in zip(delays,scores))
    out=[]
    for item in sorted(results,key=lambda x:x.score_db,reverse=True):
        if all(p.invert_trace2!=item.invert_trace2 or abs(p.delay_ms-item.delay_ms)>.45 for p in out):
            out.append(item)
            if len(out)>=top_k:break
    return out

@pytest.mark.parametrize("lf,hf,max_delay",[(60,200,8),(60,200,180),(180,3500,40)])
def test_shared_delay_rotation_same_candidates_and_scores(lf,hf,max_delay):
    hz=np.geomspace(20,20000,440)
    a=synthetic("measure",hz,db=1,delay_ms=6.1)
    b=synthetic("reference",hz,db=-3,delay_ms=1.5,invert=True)
    coh=np.linspace(.65,.98,len(hz))
    a=replace(a,coherence=coh)
    b=replace(b,coherence=coh)
    expected=reference(a,b,lf,hf,max_delay)
    got=auto_align(a,b,lf=lf,hf=hf,max_delay_ms=max_delay)
    assert len(got)==len(expected)
    for lhs,rhs in zip(got,expected):
        assert lhs.invert_trace2==rhs.invert_trace2
        assert lhs.delay_ms==rhs.delay_ms
        assert lhs.score_db==pytest.approx(rhs.score_db,abs=1e-12)
