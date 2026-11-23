"""Read-only Smaart TRF parser and complex SUM model (Windows V7).
No binary patching, no license changes, no live TF stream claim.
"""
from dataclasses import dataclass
from pathlib import Path
import struct
import numpy as np
from .smoothing import smooth_log_octaves, smooth_phase_unit_phasor

class TraceError(ValueError): pass

@dataclass(frozen=True)
class TFTrace:
    name:str
    path:Path
    hz:np.ndarray
    h:np.ndarray
    coherence:np.ndarray
    kind:str
    file_mtime_ns:int

@dataclass(frozen=True)
class Candidate:
    delay_ms:float
    invert_trace2:bool
    score_db:float
    roi_bins:int

@dataclass(frozen=True)
class SumTrace:
    hz:np.ndarray
    mag_db:np.ndarray
    phase_deg:np.ndarray
    coherence:np.ndarray
    valid:np.ndarray
    delay_ms:float
    invert_trace2:bool
    sources:tuple[str,str]
    phase_valid:np.ndarray|None=None
    phase_concentration:np.ndarray|None=None

# V8.113: Smaart Suite 9 stores estimator rounding as slightly negative
# coherence (observed -0.0192). It is clipped to 0 below; only clearly
# corrupt values are rejected.
COHERENCE_NEG_TOL=-0.05

def read_trf(path):
    path=Path(path); st=path.stat()
    if not 750<=st.st_size<=32*1024*1024:raise TraceError("unsupported file length")
    b=path.read_bytes()
    if b[:8]!=b"JACKREF!":raise TraceError("not JACKREF! .trf")
    name=b[0x28:0x49].split(b"\x00",1)[0].decode("utf-8","replace") or path.stem
    tag=b.find(b"MTWBEAST",0x250,min(len(b),0x388))
    if tag>=0:
        if struct.unpack_from("<I",b,tag+8)[0]!=36:raise TraceError("unsupported MTW version")
        n=struct.unpack_from("<I",b,tag+12)[0]
        ptr=struct.unpack_from("<5I",b,tag+16)
        kind="MTW"
    else:
        ptr=struct.unpack_from("<5I",b,0x288)
        if not(ptr[0]>=0x2a8 and ptr[1]>ptr[0] and (ptr[1]-ptr[0])%4==0):
            raise TraceError("unsupported legacy header")
        n=(ptr[1]-ptr[0])//4
        kind="Legacy"
    if not(2<=n<=131072) or len(set(ptr))!=5:raise TraceError("invalid pointers/count")
    for at,stride in zip(ptr,(4,8,8,8,8)):
        if at<0x200 or at+n*stride>len(b):raise TraceError("truncated TRF array")
    f=np.frombuffer(b,dtype="<f4",count=n,offset=ptr[0]).astype(float)
    db=np.frombuffer(b,dtype="<f8",count=n,offset=ptr[1]).copy()
    re=np.frombuffer(b,dtype="<f8",count=n,offset=ptr[2])
    im=np.frombuffer(b,dtype="<f8",count=n,offset=ptr[3])
    coh=np.frombuffer(b,dtype="<f8",count=n,offset=ptr[4]).copy()
    if not(all(np.all(np.isfinite(a)) for a in (f,db,re,im,coh))
        and np.all(np.diff(f)>0) and np.all(f<=100000)
        and np.all((coh>=COHERENCE_NEG_TOL)&(coh<=1.01))):raise TraceError("bad TRF samples")
    good=f>0
    if np.count_nonzero(good)<51:raise TraceError("too few bins")
    h=np.power(10.,db[good]/20.)*np.exp(1j*np.arctan2(im[good],re[good]))
    return TFTrace(name,path,f[good],h,np.clip(coh[good],0,1),kind,st.st_mtime_ns)

TRACE_GAIN_LIMIT_DB=40.

def with_gain_db(trace,gain_db):
    """V8.114: the same TF with a linear level change (Smaart trace dB offset).

    H' = H * 10^(gain/20). Phase and coherence are unchanged, so the complex
    SUM, Auto Phase and Phase Match all see the level the user set in Smaart.
    A 0 dB gain returns the original object (bit-identical downstream).
    """
    g=float(gain_db)
    if not np.isfinite(g) or abs(g)>TRACE_GAIN_LIMIT_DB:
        raise ValueError(f"trace gain out of range: {gain_db}")
    if g==0.:
        return trace
    from dataclasses import replace
    return replace(trace,h=np.asarray(trace.h)*(10.**(g/20.)))

def matched(a,b):
    f=a.hz
    j=np.searchsorted(b.hz,f)
    safe=np.clip(j,0,len(b.hz)-1); lo=np.clip(safe-1,0,len(b.hz)-1)
    exact=(j<len(b.hz))&(np.abs(b.hz[safe]-f)<0.002)
    valid=(exact|((j>0)&(j<len(b.hz))&(b.hz[safe]/np.maximum(b.hz[lo],1e-9)<1.25)))
    valid &= (f>=b.hz[0])&(f<=b.hz[-1])
    # Interpolate magnitude and a resolved phase, not a chord through the
    # complex plane (which attenuates even a constant-amplitude pure delay).
    magnitude=np.abs(b.h)
    phase=np.unwrap(np.angle(b.h))
    resolved=((magnitude[lo]>1e-12)&(magnitude[safe]>1e-12)&
              (np.abs(phase[safe]-phase[lo])<.9*np.pi))
    valid &= exact|resolved
    ii=np.flatnonzero(valid)
    if len(ii)<1:raise TraceError("no matching frequencies")
    f=f[ii]; j=safe[ii]; k=lo[ii]; eq=exact[ii]
    alpha=(f-b.hz[k])/np.maximum(b.hz[j]-b.hz[k],1e-12)
    logmag=np.log(np.maximum(magnitude,1e-300))
    interpolated=np.exp(logmag[k]+(logmag[j]-logmag[k])*alpha+
                        1j*(phase[k]+(phase[j]-phase[k])*alpha))
    h2=np.where(eq,b.h[j],interpolated)
    c2=np.where(eq,b.coherence[j],b.coherence[k]+(b.coherence[j]-b.coherence[k])*alpha)
    return f,a.h[ii],h2,np.minimum(a.coherence[ii],c2)

ALIGN_MIN_BINS=12
ALIGN_CHUNK=128

def alignment_roi(a,b,lf,hf,coh_gate):
    """Matched, coherence-gated ROI used by AutoPhase and its confidence."""
    f,h1,h2,coh=matched(a,b)
    roi=(f>=lf)&(f<=hf)&(coh>=coh_gate)&(np.abs(h1)>1e-12)&(np.abs(h2)>1e-12)
    return f[roi],h1[roi],h2[roi],coh[roi]

def alignment_delays(max_delay_ms,step_ms):
    return np.arange(-max_delay_ms,max_delay_ms+step_ms/4.,step_ms)

def alignment_penalty_db(f,h1,h2,delays_ms,invert):
    """Per-bin SUM penalty (dB) for a delay chunk: shape (len(delays), bins).

    Single source of the AutoPhase objective; never duplicated elsewhere.
    """
    sign=-1 if invert else 1
    norm=np.maximum(np.abs(h1)+np.abs(h2),1e-15)
    shifted=h2[None,:]*np.exp(-2j*np.pi*np.outer(delays_ms/1000,f))
    ratio=np.maximum(np.abs(h1[None,:]+sign*shifted)/norm[None,:],1e-5)
    return 20*np.log10(ratio)

def auto_align(a,b,lf=60.,hf=200.,coh_gate=0.60,max_delay_ms=180.,
               step_ms=.1,top_k=4):
    f,h1,h2,coh=alignment_roi(a,b,lf,hf,coh_gate)
    if len(f)<ALIGN_MIN_BINS:return []
    weights=coh**2
    delays=alignment_delays(max_delay_ms,step_ms)
    # Compute the complex delay rotation once per chunk, share it between
    # normal/inverted routes. The score formula and candidate ordering are
    # identical to alignment_penalty_db; only duplicate np.exp is eliminated.
    norm=np.maximum(np.abs(h1)+np.abs(h2),1e-15)
    weight_total=weights.sum()
    scores_by_invert=(np.empty(len(delays)),np.empty(len(delays)))
    for k in range(0,len(delays),ALIGN_CHUNK):
        d=delays[k:k+ALIGN_CHUNK]
        shifted=h2[None,:]*np.exp(-2j*np.pi*np.outer(d/1000,f))
        for invert,sign in enumerate((1,-1)):
            ratio=np.maximum(np.abs(h1[None,:]+sign*shifted)/norm[None,:],1e-5)
            scores_by_invert[invert][k:k+len(d)]=(20*np.log10(ratio)@weights)/weight_total
    results=[]
    for invert,scores in enumerate(scores_by_invert):
        results.extend(Candidate(float(d),bool(invert),float(s),len(f))
                       for d,s in zip(delays,scores))
    out=[]
    for item in sorted(results,key=lambda x:x.score_db,reverse=True):
        if all(p.invert_trace2 != item.invert_trace2 or
               abs(p.delay_ms-item.delay_ms)>.45 for p in out):
            out.append(item)
            if len(out)>=top_k:break
    return out

def _octave_smooth(f,values,fraction,phase=False):
    if fraction==0:return values.copy()
    x=np.log2(f); sigma=1./(fraction*2.355)
    smooth=np.empty_like(values)
    for i,center in enumerate(x):
        indices=np.flatnonzero(np.abs(x-center)<=3*sigma)
        w=np.exp(-.5*((x[indices]-center)/sigma)**2)
        if phase:
            z=np.sum(np.exp(1j*np.deg2rad(values[indices]))*w)
            smooth[i]=np.rad2deg(np.angle(z))
        else:smooth[i]=float(np.dot(w,values[indices])/w.sum())
    return smooth

def no_data_bins(trace):
    """V8.115: Smaart writes unmeasured bins as exactly H=1+0j, coherence 0.

    Observed on every Smaart 9 TRF (band-limited measurements); never seen on
    real data. They carry no measurement, so they must not enter a SUM.
    """
    return (np.asarray(trace.h)==1+0j)&(np.asarray(trace.coherence)<=0.)

def _no_data_on(f,trace):
    """Placeholder flag of `trace` on grid f (conservative at bracket edges)."""
    flags=no_data_bins(trace)
    j=np.clip(np.searchsorted(trace.hz,f),0,len(trace.hz)-1)
    k=np.clip(j-1,0,len(trace.hz)-1)
    exact=np.abs(trace.hz[j]-f)<0.002
    return np.where(exact,flags[j],flags[j]|flags[k])

def compute_sum(a,b,delay_ms=0.,invert_trace2=False,coh_gate=.60,
                mag_oct=0,phase_oct=0):
    f,h1,h2,coh=matched(a,b)
    # An unmeasured Smaart placeholder is not unity response.  It contributes
    # zero to the display SUM, so a one-sided measurement falls back exactly
    # to the measured trace.  Only a bin missing from both traces is unknown.
    # `valid` below stays false for this fallback because it is not evidence of
    # a measured two-trace sum.  Auto Align continues to use the raw traces.
    missing1=_no_data_on(f,a)
    missing2=_no_data_on(f,b)
    term1=np.where(missing1,0j,h1)
    term2=np.where(missing2,0j,h2)*np.exp(-2j*np.pi*f*delay_ms/1000.)
    h=term1+(-1 if invert_trace2 else 1)*term2
    nodata=missing1&missing2
    h=np.where(nodata,np.nan+0j,h)
    mag=20*np.log10(np.maximum(np.abs(h),1e-15))
    mag[nodata]=np.nan
    deg=np.rad2deg(np.angle(h))
    # Smooth only display series; AutoAlign solver and original H stay raw.
    # Legacy caller uses denominator=12 to mean 1/12 octave.
    mag_oct=(1.0/mag_oct if mag_oct>=1 else mag_oct)
    phase_oct=(1.0/phase_oct if phase_oct>=1 else phase_oct)
    if mag_oct:
        mag=smooth_log_octaves(f,mag,mag_oct)
    deg,phase_valid,concentration=smooth_phase_unit_phasor(
        f,h,coh,phase_oct,coh_gate=coh_gate)
    mask=(coh>=coh_gate)&np.isfinite(mag)&np.isfinite(deg)
    return SumTrace(f,mag,deg,coh,mask,float(delay_ms),bool(invert_trace2),
                    (a.path.name,b.path.name),phase_valid,concentration)


def phase_match_percent(a,b,delay_ms=0.0,invert_trace2=False,
                        lf=60.,hf=200.,coh_gate=.60,min_bins=12):
    """Coherence-weighted circular phase *agreement* in LF..HF.

    Score 100 means identical phase (0-degree difference); 0 means 180
    degrees apart. The metric is a model similarity percentage, NOT a
    probability or independently validated Smaart alignment score.
    Uses the same matched frequency bins as the complex SUM and solver,
    before any Mag/Phase display smoothing or display-only Mag offset.
    Returns (None, valid_bins) if too few trustworthy bins.
    """
    if not (20. <= float(lf) < float(hf) <= 20000.):
        return None, 0
    f,h1,h2,coh=matched(a,b)
    mask=((f>=float(lf)) & (f<=float(hf)) & (coh>=float(coh_gate))
          & np.isfinite(h1.real)&np.isfinite(h1.imag)
          & np.isfinite(h2.real)&np.isfinite(h2.imag)
          & (np.abs(h1)>1e-12) & (np.abs(h2)>1e-12))
    n=int(np.count_nonzero(mask))
    if n<int(min_bins):
        return None,n
    freqs=f[mask]
    shifted=h2[mask]*np.exp(-2j*np.pi*freqs*(float(delay_ms)/1000.))
    if invert_trace2:
        shifted=-shifted
    # Angle difference via normalized complex product (phase only).
    cross=h1[mask]*np.conj(shifted)
    cos_delta=np.clip(cross.real/np.maximum(np.abs(cross),1e-20),-1.,1.)
    weight=np.clip(coh[mask],0.,1.)**2
    denom=float(weight.sum())
    if not np.isfinite(denom) or denom<=1e-15:
        return None,n
    agreement=50. * (1.+float(np.dot(weight,cos_delta)/denom))
    return float(np.clip(agreement,0.,100.)),n


def sum_ref_phase_delta(ref,other,delay_ms=0.,invert_other=False,
                        lf=60.,hf=200.,coh_gate=.60,min_bins=12):
    """Circular |Phase(SUM)-Phase(REF)| on *raw* complex TF in LF/HF.

    ref is NEVER delayed/inverted. Only other is corrected with signed
    relative shift. The returned mean absolute circular difference is
    coherence-squared-weighted. P95 is an unweighted percentile of
    the same valid bins, in degrees. Values are model estimates, not
    Smaart internal phase renderer parity.
    """
    if not(20.<=float(lf)<float(hf)<=20000.):
        return None,None,0
    f,h_ref,h_other,coh=matched(ref,other)
    roi=((f>=lf)&(f<=hf)&(coh>=coh_gate)
         & np.isfinite(h_ref.real)&np.isfinite(h_ref.imag)
         & np.isfinite(h_other.real)&np.isfinite(h_other.imag)
         & (np.abs(h_ref)>1e-12)&(np.abs(h_other)>1e-12))
    h_corrected=h_other*np.exp(-2j*np.pi*f*float(delay_ms)/1000.)
    if invert_other:
        h_corrected=-h_corrected
    h_sum=h_ref+h_corrected
    # Suppress cancellation notches whose SUM phase is effectively undefined.
    roi &= (np.abs(h_sum) >
            1e-6*(np.abs(h_ref)+np.abs(h_corrected)))
    count=int(roi.sum())
    if count<int(min_bins):
        return None,None,count
    delta=np.rad2deg(np.angle(h_sum[roi]*np.conj(h_ref[roi])))
    weights=np.square(np.clip(coh[roi],0.,1.))
    if float(weights.sum())<=1e-15:
        return None,None,count
    mean=float(np.average(np.abs(delta),weights=weights))
    p95=float(np.percentile(np.abs(delta),95))
    return mean,p95,count

def synthetic(name,hz,db=0.,delay_ms=0.,invert=False):
    f=np.asarray(hz,dtype=float)
    h=10**(db/20.)*np.exp(-2j*np.pi*f*delay_ms/1000.)*(-1 if invert else 1)
    return TFTrace(name,Path(name+".trf"),f,h,np.ones_like(f),"SYNTH",0)
