"""Regression for exact AutoEQ LRU against frozen original R54 result evidence."""
import sys,time,json,hashlib
from pathlib import Path
import numpy as np
import pytest
BASE=Path(r"D:\R56_AUTOEQ_FIRST_RUN_QA")
sys.path.insert(0,str(BASE/"src"))
import _remix_bootstrap
from trf_core import read_trf
from remix_duo.core.autoeq import (design_remix_eq_auto_limits,
                                  _exact_cached_auto_design)
REF=json.loads((BASE/"autoeq_R54_baseline.json").read_text(encoding="utf8"))
FOLDER=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def packed(r,filename,mode):
    return dict(filename=filename,mode=mode,outcome="PASS",status=r.status,
                peqs=[[x.freq_hz,x.gain_db,x.q] for x in r.peqs],
                rms_before=r.rms_before,rms_after=r.rms_after,
                boost=r.boost_limit_db,cut=r.cut_limit_db,
                filters=r.filter_limit,warnings=list(r.warnings),
                arrays={k:hashlib.sha256(np.asarray(getattr(r,k)).tobytes()).hexdigest()
                        for k in ("hz","before_db","after_db","target_db")})

@pytest.mark.parametrize("reference",REF,ids=lambda x:x["filename"]+":"+x["mode"])
def test_r55_exact_numerical_equivalence(reference):
    if reference["outcome"]!="PASS":
        pytest.skip("This reference is not an approved plan")
    t=read_trf(FOLDER/reference["filename"])
    args=dict(fs=48000,target="Flat",lf=60,hf=12000,source=t.path.stem,
              filters=(0 if reference["mode"]=="AUTO" else 8))
    started=time.perf_counter()
    result=design_remix_eq_auto_limits(t.hz,t.h,t.coherence,**args)
    elapsed_ms=1000*(time.perf_counter()-started)
    actual=packed(result,reference["filename"],reference["mode"])
    expected={k:v for k,v in reference.items() if k!="ms"}
    assert actual==expected
    start=time.perf_counter()
    repeated=design_remix_eq_auto_limits(t.hz,t.h,t.coherence,**args)
    repeated_ms=1000*(time.perf_counter()-start)
    assert packed(repeated,reference["filename"],reference["mode"])==expected
    assert repeated_ms<40.,repeated_ms
    print("R55_EQ_PERF",reference["filename"],reference["mode"],
          "first_ms",round(elapsed_ms,2),"warm_ms",round(repeated_ms,2),flush=True)

def test_lru_defensive_result_copy_and_changed_source():
    t=read_trf(FOLDER/"TUNNINNGGG-3-1.trf")
    args=dict(fs=48000,target="Flat",lf=60,hf=12000,source=t.path.stem,filters=0)
    r=design_remix_eq_auto_limits(t.hz,t.h,t.coherence,**args)
    baseline=r.before_db.copy()
    r.before_db[:]=-999.
    fresh=design_remix_eq_auto_limits(t.hz,t.h,t.coherence,**args)
    np.testing.assert_array_equal(fresh.before_db,baseline)
    mutated=t.h.copy()
    mutated[50]*=1.13
    before=_exact_cached_auto_design.cache_info()
    result=design_remix_eq_auto_limits(t.hz,mutated,t.coherence,**args)
    after=_exact_cached_auto_design.cache_info()
    assert after.misses==before.misses+1
    assert result is not fresh
    print("R55_EQ_IMMUTABLE_INPUTS_PASS",before,after,flush=True)
