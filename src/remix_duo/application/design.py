from dataclasses import dataclass, replace
import numpy as np
from ..core.traces import TFTrace, auto_align
from ..core.filters import design_linear_phase_fir, design_phase_only_fir
from ..core.autoeq import design_remix_eq

def _snapshot(trace):
    arrays={}
    for field in ('hz','h','coherence'):
        value=np.array(getattr(trace,field),copy=True)
        value.setflags(write=False)
        arrays[field]=value
    return replace(trace,**arrays)

@dataclass(frozen=True)
class DesignRequest:
    tool: str
    trace: TFTrace
    reference: TFTrace | None
    fs: int
    taps: int = 1024

    @classmethod
    def create(cls, tool, trace, reference=None, *, fs, taps=1024):
        if type(fs) is not int or fs not in (44100,48000,88200,96000,192000):
            raise ValueError('Fs phải được chọn/xác nhận từ phép đo gốc')
        if tool not in ('phase','eq','fir','fir_phase'):
            raise ValueError('Unknown design tool')
        if tool=='phase' and reference is None:
            raise ValueError('Auto Phase cần hai TRF đã chọn')
        if tool!='phase':
            reference=None
        for t in (trace,reference):
            if t is not None and (not len(t.hz) or t.hz[-1]>=fs/2):
                raise ValueError('TRF frequency exceeds selected Fs Nyquist')
        return cls(tool,_snapshot(trace),_snapshot(reference) if reference is not None else None,fs,taps)

def calculate(request):
    t=request.trace
    if request.tool=='phase':
        return auto_align(t,request.reference)
    if request.tool=='eq':
        return design_remix_eq(t.hz,t.h,t.coherence,fs=request.fs,source=t.name)
    # V8.125: always create the FIR; weak results carry result.warnings.
    if request.tool=='fir':
        return design_linear_phase_fir(t.hz,t.h,t.coherence,taps=request.taps,fs=request.fs,source=t.name,strict=False)
    if request.tool=='fir_phase':
        return design_phase_only_fir(t.hz,t.h,t.coherence,taps=request.taps,fs=request.fs,source=t.name,strict=False)
    raise ValueError('Unknown design tool')
