"""RemiX Auto EQ Unified production solver â€” AEQ-U1 candidate.

Promoted from the AEQ-R0.2 research gate after synthetic, real-capture and
topology-stability validation. No UI/audio imports. Consumes canonical complex
H_corr and returns an immutable plan; caller owns all DSP state mutation.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
from contextlib import contextmanager
from typing import Optional, Sequence
import math
from collections import OrderedDict
from contextvars import ContextVar
import numpy as np
from scipy.signal import find_peaks, peak_widths
from scipy.optimize import least_squares, minimize

__version__ = "AEQ-U1.2-R2.4"

_EPS = 1e-15
_response_cache = ContextVar('autoeq_response_cache', default=None)

@contextmanager
def shared_autoeq_request_cache():
    """Scope reusable bases to ONE immutable AUTO-EQ request, never across users.

    Candidate plans still run the exact original solver and safety gates.
    The cache contains only grid/biquad responses and input analysis whose
    profile inputs are provably independent of the budget and gain limits.
    """
    token = _response_cache.set({
        'grids': {}, 'bands': OrderedDict(), 'analysis': {},
    })
    try:
        yield
    finally:
        _response_cache.reset(token)


@dataclass(frozen=True)
class AutoEQInput:
    freqs_hz: np.ndarray
    h_corr: np.ndarray
    quality: np.ndarray
    quality_kind: str
    sample_rate: float
    measurement_kind: str
    target_freqs_hz: Optional[np.ndarray] = None
    target_db: Optional[np.ndarray] = None
    smoothing_bpo: Optional[float] = None
    def __post_init__(self):
        f=np.asarray(self.freqs_hz); h=np.asarray(self.h_corr); q=np.asarray(self.quality)
        if f.ndim!=1 or h.ndim!=1 or q.ndim!=1 or not (len(f)==len(h)==len(q)) or len(f)<8:
            raise ValueError('freqs/h_corr/quality must be equal 1-D arrays with >=8 points')
        if not np.isfinite(float(self.sample_rate)) or float(self.sample_rate)<=0:
            raise ValueError('sample_rate must be finite and >0')
        if self.smoothing_bpo is not None:
            if not np.isfinite(float(self.smoothing_bpo)) or float(self.smoothing_bpo) < 0:
                raise ValueError('smoothing_bpo must be finite and >=0')
        if (self.target_freqs_hz is None) != (self.target_db is None):
            raise ValueError('target frequency/db arrays must be supplied together')
        if self.target_freqs_hz is not None:
            tf=np.asarray(self.target_freqs_hz); td=np.asarray(self.target_db)
            if tf.ndim!=1 or td.ndim!=1 or len(tf)!=len(td) or len(tf)<2:
                raise ValueError('target arrays invalid')

@dataclass(frozen=True)
class AutoEQProfile:
    analysis_points: int = 512
    f_min_hz: float = 20.0
    f_max_hz: float = 20000.0
    max_filters: int = 12
    max_peq: int = 12
    max_low_shelf: int = 1
    max_high_shelf: int = 1
    max_cut_db: float = -9.0
    max_boost_db: float = 2.0
    min_q: float = 0.30
    max_q: float = 6.00
    max_resonance_q: float = 16.00
    min_effective_gain_db: float = 0.30
    quality_floor: float = 0.30
    boost_quality_floor: float = 0.65
    deep_null_db: float = -8.0
    hf_weight_start_hz: float = 8000.0
    hf_trend_only_hz: float = 12000.0
    robust_loss: str = 'soft_l1'
    f_scale_db: float = 1.0
    max_solver_nfev: int = 50
    full_joint_max_filters: int = 5
    fast_gain_max_nfev: int = 45
    boost_local_quality_fraction: float = 0.70
    low_quality_energy_fraction_max: float = 0.35
    min_trustworthy_coverage: float = 0.35
    # R0.2 topology stability hardening. The first few filters carry the
    # dominant stable correction. Additional filters pay an increasing model
    # complexity penalty and must produce meaningful global WRMS improvement.
    topology_knee_filters: int = 4
    filter_count_penalty_db: float = 0.002
    min_marginal_net_wrms_db: float = 0.002
    min_marginal_relative_improvement: float = 0.005
    post_knee_allow_boost: bool = False
    post_knee_max_q: float = 5.0
    q_snap_step: float = 0.50
    # Default only. Production U2.1 overrides this from the TF magnitude
    # smoothing selector so Auto EQ analyzes the same Mag curve the user sees.
    candidate_smoothing_bpo: float = 12.0
    practical_overlap_db: float = 0.75
    practical_boost_benefit_db: float = 0.10
    residual_max_passes: int = 5
    residual_max_new_bands: int = 2
    residual_eval_budget: int = 1200
    residual_wrms_budget_db: float = .02
    residual_p90_budget_db: float = .02
    residual_shoulder_budget_db: float = .20
    residual_negative_budget_db: float = .50

@dataclass(frozen=True)
class AutoEQBand:
    type: str
    f_hz: float
    gain_db: float
    q: float

@dataclass(frozen=True)
class AutoEQMetrics:
    weighted_rms_db: float
    p90_abs_error_db: float
    worst_abs_error_db: float
    max_cut_db: float
    max_boost_db: float
    max_q: float
    filter_count: int
    total_boost_db: float
    deep_null_boost_count: int
    low_quality_boost_count: int

@dataclass(frozen=True)
class AutoEQPlan:
    status: str
    bands: tuple[AutoEQBand,...]
    freqs_hz: np.ndarray
    target_db: np.ndarray
    h_eq: np.ndarray
    h_pred: np.ndarray
    mag_pred_db: np.ndarray
    phase_pred_deg: np.ndarray
    before: AutoEQMetrics
    after: AutoEQMetrics
    warnings: tuple[str,...]

@dataclass(frozen=True)
class AnalysisCurves:
    grid_hz: np.ndarray
    h_corr: np.ndarray
    mag_raw_db: np.ndarray
    mag_1_24: np.ndarray
    mag_1_6: np.ndarray
    mag_1_1: np.ndarray
    quality: np.ndarray
    reliability: np.ndarray
    frequency_confidence: np.ndarray
    weights: np.ndarray
    deep_null_mask: np.ndarray
    sample_rate: float


def sanitize_input(inp: AutoEQInput, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile()
    f=np.asarray(inp.freqs_hz,float).copy(); h=np.asarray(inp.h_corr,np.complex128).copy(); q=np.asarray(inp.quality,float).copy()
    m=np.isfinite(f)&(f>0)&np.isfinite(h.real)&np.isfinite(h.imag)&np.isfinite(q)
    f,h,q=f[m],h[m],np.clip(q[m],0,1)
    o=np.argsort(f); f,h,q=f[o],h[o],q[o]
    if len(f)<8: raise ValueError('not enough valid points')
    # collapse exact duplicate frequencies deterministically by first occurrence
    keep=np.r_[True,np.diff(f)>0]; f,h,q=f[keep],h[keep],q[keep]
    lo=max(float(p.f_min_hz),float(f[0])); hi=min(float(p.f_max_hz),float(f[-1]),0.49*float(inp.sample_rate))
    m=(f>=lo)&(f<=hi); f,h,q=f[m],h[m],q[m]
    if len(f)<8: raise ValueError('not enough valid points in analysis band')
    return f,h,q

def make_log_grid(freqs_hz, profile: AutoEQProfile|None=None, sample_rate=48000.0):
    p=profile or AutoEQProfile(); f=np.asarray(freqs_hz,float)
    lo=max(p.f_min_hz,float(np.nanmin(f))); hi=min(p.f_max_hz,float(np.nanmax(f)),0.49*sample_rate)
    return np.geomspace(lo,hi,int(p.analysis_points))

def resample_scalar_log(src_f, src_v, dst_f):
    sf=np.asarray(src_f,float); sv=np.asarray(src_v,float); df=np.asarray(dst_f,float)
    return np.interp(np.log(df),np.log(sf),sv)

def resample_complex_log(src_f, src_h, dst_f):
    sf=np.asarray(src_f,float); sh=np.asarray(src_h,np.complex128); df=np.asarray(dst_f,float)
    # interpolate log magnitude + unwrapped phase to preserve a complex canonical response
    lm=np.log(np.maximum(np.abs(sh),_EPS)); ph=np.unwrap(np.angle(sh))
    lmd=np.interp(np.log(df),np.log(sf),lm); phd=np.interp(np.log(df),np.log(sf),ph)
    return np.exp(lmd+1j*phd)

def fractional_octave_smooth(freqs, values, bands_per_octave):
    f=np.asarray(freqs,float); v=np.asarray(values,float)
    if len(f)<3 or bands_per_octave<=0: return v.copy()
    x=np.log2(f); step=float(np.median(np.diff(x)))
    half_oct=0.5/float(bands_per_octave); radius=max(1,int(round(half_oct/max(step,1e-12))))
    # triangular log-frequency kernel is deterministic and keeps broad trends stable
    k=np.arange(-radius,radius+1,dtype=float); ker=(radius+1)-np.abs(k); ker/=ker.sum()
    pad=np.pad(v,(radius,radius),mode='edge')
    return np.convolve(pad,ker,mode='valid')

def build_frequency_confidence(grid_hz, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); f=np.asarray(grid_hz,float); w=np.ones_like(f)
    m=f>p.hf_weight_start_hz
    if np.any(m):
        x=np.clip((np.log(f[m])-math.log(p.hf_weight_start_hz))/(math.log(p.hf_trend_only_hz)-math.log(p.hf_weight_start_hz)),0,1)
        w[m]=1.0-0.70*x
    w[f>=p.hf_trend_only_hz]=0.20
    return w

def detect_deep_null_mask(mag_detail, mag_1_1, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); raw=(np.asarray(mag_detail)-np.asarray(mag_1_1)) <= float(p.deep_null_db)
    # Expand by roughly 1/6 octave on the fixed log grid. The exclusion zone
    # blocks filters that merely sit on the shoulders of a cancellation null.
    if raw.size and np.any(raw):
        radius=max(1,int(round(raw.size/10.0/6.0)))  # ~1/6 octave over a 10-octave grid
        ker=np.ones(2*radius+1,dtype=int)
        return np.convolve(raw.astype(int),ker,mode='same')>0
    return raw

def build_reliability_map(mag_1_6, mag_1_1, quality, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); q=np.clip(np.asarray(quality,float),0,1)
    deficit=np.maximum(0.0,np.asarray(mag_1_1)-np.asarray(mag_1_6))
    null_penalty=np.clip((deficit-3.0)/7.0,0,1)
    return np.clip(q*(1.0-0.90*null_penalty),0,1)

def prepare_analysis_curves(inp: AutoEQInput, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile()
    # Across AUTO filter budgets / boost-cut presets these four values
    # affect the subsequent optimizer, not construction of analysis curves.
    # All other profile fields and *all source bytes* must match exactly.
    cache=_response_cache.get()
    key=None
    if cache is not None and 'analysis' in cache:
        varying={'max_filters','max_peq','max_cut_db','max_boost_db'}
        invariants=tuple((f.name,getattr(p,f.name))
                         for f in fields(AutoEQProfile) if f.name not in varying)
        source=tuple((a.dtype.str,a.shape,a.tobytes())
                     for a in (np.asarray(inp.freqs_hz),
                               np.asarray(inp.h_corr),np.asarray(inp.quality)))
        key=(invariants,source,float(inp.sample_rate),
             inp.quality_kind,inp.measurement_kind,inp.smoothing_bpo)
        prior=cache['analysis'].get(key)
        if prior is not None:
            return prior
    f,h,q=sanitize_input(inp,p); g=make_log_grid(f,p,float(inp.sample_rate))
    hg=resample_complex_log(f,h,g); mag=20*np.log10(np.maximum(np.abs(hg),_EPS)); qg=np.clip(resample_scalar_log(f,q,g),0,1)
    m24=fractional_octave_smooth(g,mag,24)
    _bpo=float(inp.smoothing_bpo) if inp.smoothing_bpo is not None else float(p.candidate_smoothing_bpo)
    m6=mag.copy() if _bpo<=0 else fractional_octave_smooth(g,mag,_bpo)
    m1=fractional_octave_smooth(g,mag,1)
    rel=build_reliability_map(m24,m1,qg,p); fc=build_frequency_confidence(g,p); dn=detect_deep_null_mask(m24,m1,p)
    weights=np.clip((qg**1.5)*rel*fc,0,1)
    # Private analysis outputs, owned by this solver request. Prevent
    # accidental mutation and permit identity-fast lookups of immutable
    # grid and residual-weight bases for the rest of the solve.
    if g.flags.owndata: g.setflags(write=False)
    if weights.flags.owndata: weights.setflags(write=False)
    # mag_raw_db is the analysis/source magnitude authority for the solver.
    # Keep the field name for compatibility; its values follow the TF smoothing selector.
    result=AnalysisCurves(g,hg,m6,m24,m6,m1,qg,rel,fc,weights,dn,float(inp.sample_rate))
    if key is not None:
        cache['analysis'][key]=result
    return result

def build_auto_target(data: AnalysisCurves):
    """Build the default Auto-EQ reference without following the DUT's own trend.

    A 1-octave copy of the measurement is useful as a *trend estimator*, but it
    is not an EQ target: broad tonal errors then become their own reference and
    Auto EQ should converge toward a single robust mid-band level reference.
    Deep-null / low-quality / boost-limit rejection remains enforced downstream
    by the safety layer instead of bending the target to follow the DUT.
    """
    f=np.asarray(data.grid_hz,float); m=np.asarray(data.mag_1_6,float)
    roi=(f>=80.0)&(f<=8000.0)&np.isfinite(m)
    if not np.any(roi):
        roi=np.isfinite(m)
    if not np.any(roi):
        return np.asarray(data.mag_1_1,float).copy()
    # AEQ-FLAT-R1: the FLAT level is the robust median magnitude over
    # the explicit 80 Hz..8 kHz authority band.  Coherence/reliability belong
    # only to downstream candidate/safety gating and must not bias the target
    # level itself; otherwise high-confidence loud regions can shift flat_ref.
    ref=float(np.median(m[roi]))
    return np.full_like(m,ref,dtype=float)
def build_user_target(data: AnalysisCurves, inp: AutoEQInput):
    return np.interp(np.log(data.grid_hz),np.log(np.asarray(inp.target_freqs_hz,float)),np.asarray(inp.target_db,float))
def build_target(data: AnalysisCurves, inp: AutoEQInput):
    return build_user_target(data,inp) if inp.target_freqs_hz is not None else build_auto_target(data)

def estimate_q_from_peak_width(width_oct, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); bw=max(float(width_oct),1e-4); r=2.0**bw; q=math.sqrt(r)/max(r-1.0,1e-9)
    return float(np.clip(q,p.min_q,p.max_q))

def _candidate_list(data, target, sign, profile):
    # sign=+1 detects measurement excess (cut); sign=-1 detects deficit (boost)
    p=profile; residual=(data.mag_1_6-target)*sign
    prom=0.55 if sign>0 else 0.75
    peaks, props=find_peaks(residual,prominence=prom,height=0.45)
    if len(peaks)==0: return []
    widths=peak_widths(residual,peaks,rel_height=0.5)[0]
    step=float(np.median(np.diff(np.log2(data.grid_hz))))
    out=[]
    for k,i in enumerate(peaks):
        f=float(data.grid_hz[i]); qual=float(data.quality[i]); rel=float(data.reliability[i]); conf=float(data.frequency_confidence[i])
        if qual < p.quality_floor or rel < p.quality_floor: continue
        if data.deep_null_mask[i]: continue
        if f>=p.hf_trend_only_hz: continue
        width_oct=max(step,float(widths[k])*step); qseed=estimate_q_from_peak_width(width_oct,p)
        raw=float(residual[i])
        if sign<0:
            if qual < p.boost_quality_floor or data.deep_null_mask[i]: continue
            # A single high-coherence bin is not enough evidence for a boost.
            # Require the measured feature's local octave neighborhood to be
            # predominantly reliable, otherwise room/noise cancellations can
            # masquerade as a correctable dip.
            half_support=max(1.0/12.0, 0.60*width_oct)
            local=np.abs(np.log2(data.grid_hz/f)) <= half_support
            if not np.any(local): continue
            local_good=np.asarray(data.quality[local]) >= p.boost_quality_floor
            if float(np.mean(local_good)) < p.boost_local_quality_fraction: continue
            if float(np.median(data.quality[local])) < p.boost_quality_floor: continue
            gain=float(np.clip(raw*0.55,0,p.max_boost_db))
        else:
            gain=float(np.clip(-raw*0.72,p.max_cut_db,0))
        if abs(gain)<p.min_effective_gain_db: continue
        score=abs(gain)*qual*rel*conf
        out.append({'type':'P','f_hz':f,'gain_db':gain,'q':qseed,'score':score,'width_oct':width_oct,'index':int(i)})
    return out

def detect_peak_candidates(data,target,profile: AutoEQProfile|None=None): return _candidate_list(data,np.asarray(target),+1,profile or AutoEQProfile())
def detect_dip_candidates(data,target,profile: AutoEQProfile|None=None): return _candidate_list(data,np.asarray(target),-1,profile or AutoEQProfile())
def detect_broad_shelf_candidate(data,target,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); err=np.asarray(target)-data.mag_1_6; out=[]
    lf=data.grid_hz<=180; hf=data.grid_hz>=6000
    if p.max_low_shelf>0 and lf.any() and np.average(err[lf],weights=np.maximum(data.weights[lf],1e-9))<-1.2:
        out.append({'type':'LS','f_hz':120.0,'gain_db':float(np.clip(np.average(err[lf]),p.max_cut_db,p.max_boost_db)),'q':0.7,'score':2.0})
    if p.max_high_shelf>0 and hf.any() and np.average(err[hf],weights=np.maximum(data.weights[hf],1e-9))<-1.2:
        out.append({'type':'HS','f_hz':6500.0,'gain_db':float(np.clip(np.average(err[hf]),p.max_cut_db,p.max_boost_db)),'q':0.7,'score':1.5})
    return out

def biquad_response(freqs, band: AutoEQBand, fs):
    f=np.asarray(freqs,float); typ=str(band.type or 'P').upper(); f0=min(max(float(band.f_hz),5.0),float(fs)*0.49); g=float(band.gain_db); Q=min(max(float(band.q),0.05),50.0)
    if abs(g)<1e-15: return np.ones_like(f,dtype=np.complex128)
    cache=_response_cache.get()
    key=None
    if cache is not None:
        # Generating grid.tobytes() for every nonlinear optimizer sample
        # needlessly copies the SAME immutable 512-point grid ~10k times.
        # Optimize only private read-only owner arrays; writable/user arrays
        # still use the original content-addressed key on every evaluation.
        if f.flags.owndata and not f.flags.writeable:
            refs=cache.setdefault('_grid_identity',{})
            entry=refs.get(id(f))
            if entry is not None and entry[0] is f:
                grid_key=entry[1]
            else:
                grid_key=(float(fs),f.shape,f.tobytes())
                refs[id(f)]=(f,grid_key)
        else:
            grid_key=(float(fs),f.shape,f.tobytes())
        key=(grid_key,typ,f0,g,Q)
        hit=cache['bands'].get(key)
        if hit is not None:
            cache['bands'].move_to_end(key)
            return hit
        basis=cache['grids'].get(grid_key)
    else:
        basis=None
    if basis is None:
        w=2*np.pi*np.clip(f,1e-6,float(fs)*0.49)/float(fs); z1=np.exp(-1j*w); z2=np.exp(-2j*w)
        if cache is not None:
            if len(cache['grids'])>=8: cache['grids'].pop(next(iter(cache['grids'])))
            cache['grids'][grid_key]=(z1,z2)
    else:
        z1,z2=basis
    A=10**(g/40.0); w0=2*np.pi*f0/float(fs); cw0=math.cos(w0); sw0=math.sin(w0)
    if typ=='LS':
        slope=Q; alpha=sw0/2*math.sqrt(max(0.0,(A+1/A)*(1/slope-1)+2)); beta=2*math.sqrt(A)*alpha
        b0=A*((A+1)-(A-1)*cw0+beta); b1=2*A*((A-1)-(A+1)*cw0); b2=A*((A+1)-(A-1)*cw0-beta)
        a0=(A+1)+(A-1)*cw0+beta; a1=-2*((A-1)+(A+1)*cw0); a2=(A+1)+(A-1)*cw0-beta
    elif typ=='HS':
        slope=Q; alpha=sw0/2*math.sqrt(max(0.0,(A+1/A)*(1/slope-1)+2)); beta=2*math.sqrt(A)*alpha
        b0=A*((A+1)+(A-1)*cw0+beta); b1=-2*A*((A-1)+(A+1)*cw0); b2=A*((A+1)+(A-1)*cw0-beta)
        a0=(A+1)-(A-1)*cw0+beta; a1=2*((A-1)-(A+1)*cw0); a2=(A+1)-(A-1)*cw0-beta
    else:
        alpha=sw0/(2*Q); b0=1+alpha*A; b1=-2*cw0; b2=1-alpha*A; a0=1+alpha/A; a1=-2*cw0; a2=1-alpha/A
    b0/=a0; b1/=a0; b2/=a0; a1/=a0; a2/=a0
    den=1+a1*z1+a2*z2; den=np.where(np.abs(den)<1e-12,1e-12+0j,den)
    response=(b0+b1*z1+b2*z2)/den
    if cache is not None:
        response.setflags(write=False)
        cache['bands'][key]=response
        if len(cache['bands'])>256: cache['bands'].popitem(last=False)
    return response

def cascade_biquads(freqs,bands: Sequence[AutoEQBand],fs):
    H=np.ones_like(np.asarray(freqs,float),dtype=np.complex128)
    for b in bands: H*=biquad_response(freqs,b,fs)
    return H

def predict_response(data: AnalysisCurves,bands):
    heq=cascade_biquads(data.grid_hz,bands,data.sample_rate); hp=data.h_corr*heq
    eq_mag=20*np.log10(np.maximum(np.abs(heq),_EPS))
    # Auto EQ magnitude authority is the user-selected smoothed Source curve.
    # Prediction is Source + exact biquad gain on the same absolute dB axis.
    mag=np.asarray(data.mag_raw_db,float)+eq_mag
    ph=np.degrees(np.unwrap(np.angle(hp)))
    return heq,hp,mag,ph

def boost_allowance_db(data: AnalysisCurves, profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); a=p.max_boost_db*np.clip((data.quality-p.boost_quality_floor)/(1-p.boost_quality_floor+1e-9),0,1)*data.reliability
    a=np.where(data.deep_null_mask,0,a); return a

def topology_penalty_db(filter_count, profile: AutoEQProfile|None=None):
    """Triangular complexity penalty in dB-equivalent WRMS units.

    Filters up to topology_knee_filters are unpenalized.  Each extra filter
    costs progressively more, so marginal bands must earn their complexity.
    """
    p=profile or AutoEQProfile(); n=max(0,int(filter_count)-int(p.topology_knee_filters))
    return float(p.filter_count_penalty_db)*float(n*(n+1))/2.0

def _predicted_mag_only(data, bands):
    """Same exact biquad magnitude as predict_response, omitting only phase
    multiplication/unwrap which least_squares never consumes."""
    heq = cascade_biquads(data.grid_hz, bands, data.sample_rate)
    return np.asarray(data.mag_raw_db, float) + 20*np.log10(np.maximum(np.abs(heq), _EPS))

def _wrms_from_mag(data,target,mag_pred):
    # Exact weighted metric for an already-evaluated magnitude curve.
    # Avoid running the same biquad cascade twice for a trial.
    e=np.asarray(target)-np.asarray(mag_pred)
    w=np.asarray(data.weights)
    return float(np.sqrt(np.sum(w*e*e)/max(np.sum(w),1e-12)))

def _wrms_for_bands(data,target,bands):
    # Ranking uses exact WRMS; full safety metrics remain at acceptance.
    return _wrms_from_mag(data,target,_predicted_mag_only(data,bands))

def seed_greedy_bands(data: AnalysisCurves,target,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); target=np.asarray(target,float); selected=[]; used=[]
    shelf=detect_broad_shelf_candidate(data,target,p)
    candidates=detect_peak_candidates(data,target,p)+detect_dip_candidates(data,target,p)+shelf
    # R0.2: choose topology by global WRMS benefit minus an explicit filter-count
    # complexity penalty.  This prevents small residual wiggles from filling all
    # available bands and makes near-identical captures converge on core filters.
    for _ in range(p.max_filters):
        pred=_predicted_mag_only(data,selected); err=target-pred
        cur_wrms=compute_metrics(data,target,pred,selected).weighted_rms_db
        cur_score=cur_wrms+topology_penalty_db(len(selected),p)
        # Selected topology stays constant during this candidate pass.
        # It is unnecessarily re-evaluated for every trial in the original.
        selected_objective=objective_cost(data,target,selected,p)
        best=None
        best_cut=None
        for c in candidates:
            if c in used: continue
            # After the stable-core knee, only robust extra corrections are
            # eligible.  Marginal boosts and ultra-narrow filters are much more
            # sensitive to tiny Pink/Sweep/repeat-measurement perturbations.
            if len(selected) >= p.topology_knee_filters:
                if (not p.post_knee_allow_boost) and float(c.get('gain_db',0.0)) > 0.0:
                    continue
                if float(c.get('q',1.0)) > p.post_knee_max_q:
                    continue
            idx=int(np.argmin(np.abs(np.log(data.grid_hz/c['f_hz'])))); local=float(err[idx])
            if c['type']=='P':
                if c['gain_db']<0 and local>=-0.45: continue
                if c['gain_db']>0 and local<=0.45: continue
            g=c['gain_db']
            if c['type']=='P':
                if g<0: g=float(np.clip(local*0.70,p.max_cut_db,-p.min_effective_gain_db))
                else:
                    if data.deep_null_mask[idx] or data.quality[idx]<p.boost_quality_floor: continue
                    g=float(np.clip(local*0.50,p.min_effective_gain_db,p.max_boost_db))
            b=AutoEQBand(c['type'],float(c['f_hz']),g,float(c['q']))
            trial=selected+[b]
            # One exact complex biquad cascade powers both WRMS and the
            # legacy least-squares tie-breaker. Previously the same trial
            # cascade was evaluated twice (no candidate/safety pruning).
            trial_pred=_predicted_mag_only(data,trial)
            trial_wrms=_wrms_from_mag(data,target,trial_pred)
            raw_gain=cur_wrms-trial_wrms
            trial_score=trial_wrms+topology_penalty_db(len(trial),p)
            net_gain=cur_score-trial_score
            rel_gain=raw_gain/max(cur_wrms,1e-9)
            # Tie breaker preserves the pre-R0.2 true-biquad objective ranking.
            legacy_gain=selected_objective-_objective_cost_for_computed_mag(
                data,target,trial_pred,trial)
            rank=(net_gain,raw_gain,legacy_gain)
            cand=(rank,b,c,rel_gain)
            if best is None or rank>best[0]: best=cand
            if float(b.gain_db) < 0.0 and (best_cut is None or rank>best_cut[0]): best_cut=cand
        if best is None: break
        # TF-reference semantics: cuts get first refusal.  A correctable peak is
        # safer and more transferable than an early boost into a dip.  Only when
        # no cut clears the same marginal-improvement gates may a boost win.
        chosen=best
        if best_cut is not None:
            cut_net,cut_raw,_=best_cut[0]
            if cut_net >= p.min_marginal_net_wrms_db and best_cut[3] >= p.min_marginal_relative_improvement:
                chosen=best_cut
        net_gain,raw_gain,_=chosen[0]
        if net_gain < p.min_marginal_net_wrms_db: break
        if chosen[3] < p.min_marginal_relative_improvement: break
        selected.append(chosen[1]); used.append(chosen[2])
    if not selected:
        # Heavy smoothing can make width-derived cuts spill into LF rolloff;
        # try shallower/narrower versions of the same trusted detected peaks
        # before declaring that the measured response needs no correction.
        baseline=compute_metrics(data,target,data.mag_raw_db,()).weighted_rms_db
        fallback=[]
        for c in candidates:
            if c['type']!='P' or c['gain_db']>=0: continue
            for gain_scale in (.75,.5,.25):
                for q_scale in (1.,1.5,2.,3.):
                    b=AutoEQBand('P',float(c['f_hz']),float(c['gain_db'])*gain_scale,min(p.max_q,float(c['q'])*q_scale))
                    if abs(b.gain_db)<p.min_effective_gain_db: continue
                    score=_wrms_for_bands(data,target,(b,))
                    improvement=baseline-score
                    if improvement>=p.min_marginal_net_wrms_db and improvement/max(baseline,1e-9)>=p.min_marginal_relative_improvement:
                        fallback.append((score,b))
        if fallback: selected=[min(fallback,key=lambda v:v[0])[1]]
    return tuple(selected)

def pack_solver_params(bands):
    x=[]
    for b in bands: x += [math.log10(max(b.f_hz,1e-6)),math.log(max(b.q,1e-6)),b.gain_db]
    return np.asarray(x,float)
def unpack_solver_params(x,types,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); out=[]
    for i,t in enumerate(types):
        f=10**float(x[3*i]); q=math.exp(float(x[3*i+1])); g=float(x[3*i+2]); out.append(AutoEQBand(t,f,g,q))
    return tuple(out)
def _shared_sqrt_weights(data):
    """Exact sqrt(max(weights, 1e-9)), memoized for one immutable solve."""
    weights=data.weights
    cache=_response_cache.get()
    if (cache is not None and isinstance(weights,np.ndarray)
            and weights.flags.owndata and not weights.flags.writeable):
        refs=cache.setdefault('_sqrt_weights_identity',{})
        entry=refs.get(id(weights))
        if entry is not None and entry[0] is weights:
            return entry[1]
        basis=np.sqrt(np.maximum(weights,1e-9))
        refs[id(weights)]=(weights,basis)
        return basis
    return np.sqrt(np.maximum(weights,1e-9))


def solver_residual(data,target,bands,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile()
    # The optimizer evaluates only weighted magnitude residuals; full complex
    # phase prediction is reserved for the final accepted plan.
    pred=_predicted_mag_only(data,bands)
    e=(np.asarray(target)-pred)*_shared_sqrt_weights(data)
    # light regularizers: discourage boost and very high Q without dominating fit
    # Keep residual vector length fixed for scipy least_squares. Two smooth
    # regularizer residuals are emitted for every band, even when zero.
    reg=[]
    for b in bands:
        reg.append(0.10*max(float(b.gain_db),0.0))
        reg.append(0.04*max(float(b.q)-3.5,0.0))
    return np.r_[e,np.asarray(reg,float)]
def objective_cost(data,target,bands,profile: AutoEQProfile|None=None):
    r=solver_residual(data,target,bands,profile); return float(np.dot(r,r))

def _objective_cost_for_computed_mag(data,target,pred,bands):
    """Exact solver objective after the same candidate cascade is already computed.

    Preserve the exact residual concatenation, regularization, and np.dot
    order of solver_residual/objective_cost; no approximate ranking.
    """
    e=(np.asarray(target)-pred)*_shared_sqrt_weights(data)
    reg=[]
    for b in bands:
        reg.append(0.10*max(float(b.gain_db),0.0))
        reg.append(0.04*max(float(b.q)-3.5,0.0))
    r=np.r_[e,np.asarray(reg,float)]
    return float(np.dot(r,r))
def _actionable_cut_wrms(data, target, pred, profile: AutoEQProfile|None=None):
    """WRMS on trustworthy, non-null bins that cut-only PEQ can safely improve."""
    p=profile or AutoEQProfile()
    t=np.asarray(target,float); y=np.asarray(pred,float); src=np.asarray(data.mag_raw_db,float)
    f=np.asarray(data.grid_hz,float)
    mask=(
        np.isfinite(t)&np.isfinite(y)&np.isfinite(src)
        &(f>=80.0)&(f<=8000.0)
        &(np.asarray(data.quality)>=p.quality_floor)
        &(np.asarray(data.reliability)>=p.quality_floor)
        &(~np.asarray(data.deep_null_mask,dtype=bool))
    )
    if not np.any(mask):
        return 0.0,0.0
    w=np.maximum(np.asarray(data.weights,float)[mask],1e-12)
    den=max(float(np.sum(w)),1e-12)
    before=float(np.sqrt(np.sum(w*(src[mask]-t[mask])**2)/den))
    after=float(np.sqrt(np.sum(w*(y[mask]-t[mask])**2)/den))
    return before,after

def _optimize_joint_gains_fast(data,target,bands,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); bands=tuple(bands)
    if not bands: return bands
    x0=np.asarray([b.gain_db for b in bands],float)
    lo=np.asarray([p.max_cut_db for _ in bands],float)
    hi=np.asarray([p.max_boost_db for _ in bands],float)
    def unpack_gains(x):
        return tuple(AutoEQBand(b.type,b.f_hz,float(g),b.q) for b,g in zip(bands,x))
    def fun(x): return solver_residual(data,target,unpack_gains(x),p)
    try:
        res=least_squares(fun,x0,bounds=(lo,hi),loss=p.robust_loss,f_scale=p.f_scale_db,
                          max_nfev=p.fast_gain_max_nfev,xtol=1e-5,ftol=1e-5,gtol=1e-5)
        out=unpack_gains(res.x)
        if objective_cost(data,target,out,p) <= objective_cost(data,target,bands,p)+1e-8: return out
    except Exception:
        pass
    return bands

def _lock_cut_centers_to_residual_peaks(data,target,bands):
    """Snap cut PEQ centers to actual positive residual peaks on smoothed Source.

    Fc is measurement geometry, not a free WRMS variable.  Optimizers may move
    it onto a shoulder and improve global error while visibly missing the peak.
    """
    bands=tuple(bands)
    if not bands: return bands
    residual=np.asarray(data.mag_1_6,float)-np.asarray(target,float)
    peaks,_=find_peaks(residual,prominence=0.35,height=0.30)
    if len(peaks)==0: return bands
    pf=np.asarray(data.grid_hz,float)[peaks]
    out=[]
    for b in bands:
        if b.type!='P' or b.gain_db>=0:
            out.append(b); continue
        d=np.abs(np.log2(pf/max(float(b.f_hz),1e-9)))
        j=int(np.argmin(d))
        # Only snap to the same local feature, never jump to another peak.
        if float(d[j]) <= 0.10:
            out.append(AutoEQBand(b.type,float(pf[j]),float(b.gain_db),float(b.q)))
        else:
            out.append(b)
    return tuple(out)

def optimize_joint_bands(data,target,bands,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); bands=tuple(bands)
    if not bands: return bands
    # Numerical Jacobians scale with parameter count. For larger topologies,
    # jointly solve all gains against the exact biquad cascade while preserving
    # the peak-width-derived Fc/Q topology. Small topologies still receive full
    # Fc/Q/Gain joint refinement. This keeps click-time bounded on real traces.
    if len(bands) > p.full_joint_max_filters:
        return _optimize_joint_gains_fast(data,target,bands,p)
    types=[b.type for b in bands]; x0=pack_solver_params(bands); fhi=min(p.f_max_hz,0.45*data.sample_rate)
    lo=[]; hi=[]
    for b in bands:
        flo=max(p.f_min_hz,b.f_hz/1.8); fup=min(fhi,b.f_hz*1.8)
        qlo=p.min_q; qhi=p.max_q; glo=p.max_cut_db; ghi=p.max_boost_db
        if b.type in ('LS','HS'): qlo,qhi=0.3,1.5
        lo += [math.log10(flo),math.log(qlo),glo]; hi += [math.log10(fup),math.log(qhi),ghi]
    def fun(x): return solver_residual(data,target,unpack_solver_params(x,types,p),p)
    try:
        res=least_squares(fun,x0,bounds=(np.asarray(lo),np.asarray(hi)),loss=p.robust_loss,f_scale=p.f_scale_db,
                          max_nfev=p.max_solver_nfev,xtol=1e-7,ftol=1e-7,gtol=1e-7)
        out=unpack_solver_params(res.x,types,p)
        if objective_cost(data,target,out,p) <= objective_cost(data,target,bands,p)+1e-8: return out
    except Exception:
        pass
    return bands

def prune_weak_bands(bands,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); return tuple(b for b in bands if abs(b.gain_db)>=p.min_effective_gain_db)
def merge_nearby_bands(bands,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); out=[]
    for b in sorted(bands,key=lambda z:z.f_hz):
        if out and b.type==out[-1].type=='P' and np.sign(b.gain_db)==np.sign(out[-1].gain_db) and abs(math.log2(b.f_hz/out[-1].f_hz))<1/12:
            a=out.pop(); wa,wb=abs(a.gain_db),abs(b.gain_db); f=2**((wa*math.log2(a.f_hz)+wb*math.log2(b.f_hz))/max(wa+wb,1e-9)); g=float(np.clip(a.gain_db+b.gain_db,p.max_cut_db,p.max_boost_db)); q=min(a.q,b.q); out.append(AutoEQBand('P',f,g,q))
        else: out.append(b)
    return tuple(out)
def stabilize_band_q(bands, profile: AutoEQProfile|None=None):
    """Snap final Q to a small deterministic lattice for measurement-repeatability.

    Frequency and gain stay continuous; only Q is quantized.  Gain is then
    re-optimized against the exact production-parity biquad cascade.
    """
    p=profile or AutoEQProfile(); step=max(float(p.q_snap_step),1e-9); out=[]
    for b in bands:
        q=float(np.clip(round(float(b.q)/step)*step,p.min_q,p.max_q))
        out.append(AutoEQBand(b.type,float(b.f_hz),float(b.gain_db),q))
    return tuple(out)

def _refine_narrow_resonance_cuts(data,target,bands,profile=None):
    """Sharpen only strong residual resonances already assigned a high-Q cut."""
    p=profile or AutoEQProfile(); core=list(bands)
    for bi,b in enumerate(tuple(core)):
        if b.type!='P' or b.gain_db>=0 or b.q < max(5.5,p.max_q-0.5):
            continue
        pred=_predicted_mag_only(data,tuple(core))
        resid=np.asarray(pred,float)-np.asarray(target,float)
        center=_nearest_idx(data.grid_hz,b.f_hz)
        _oct=np.abs(np.log2(np.asarray(data.grid_hz,float)/max(float(b.f_hz),1e-9)))
        _ids=np.flatnonzero(_oct<=0.18)
        if _ids.size<5:
            continue
        lo=int(_ids[0]); hi=int(_ids[-1])+1
        loc=resid[lo:hi]
        if loc.size<5:
            continue
        pk=int(lo+np.argmax(loc)); peak=float(resid[pk])
        if peak < 2.0 or abs(math.log2(float(data.grid_hz[pk])/max(float(b.f_hz),1e-9))) > 0.08:
            continue
        if data.quality[pk] < p.quality_floor or data.reliability[pk] < p.quality_floor:
            continue
        good=np.asarray(data.weights)>1e-6
        base_wrms=_wrms_for_bands(data,target,tuple(core))
        base_p90=float(np.percentile(np.abs(np.asarray(target)[good]-pred[good]),90)) if np.any(good) else 0.0
        base_pos=float(np.max(loc)); base_min=float(np.min(loc)); best=None
        for qv in (8.0,10.0,12.0,16.0):
            if qv > p.max_resonance_q+1e-9:
                continue
            for frac in (0.50,0.65,0.80):
                gv=float(np.clip(float(b.gain_db)-frac*peak,p.max_cut_db,-p.min_effective_gain_db))
                trial=list(core); trial[bi]=AutoEQBand('P',float(b.f_hz),gv,float(qv)); trial=tuple(trial)
                tpred=_predicted_mag_only(data,trial); tr=np.asarray(tpred)-np.asarray(target)
                tw=_wrms_from_mag(data,target,tpred)
                tp90=float(np.percentile(np.abs(np.asarray(target)[good]-tpred[good]),90)) if np.any(good) else 0.0
                tloc=tr[lo:hi]; tpos=float(np.max(tloc)); tmin=float(np.min(tloc))
                if (tw <= base_wrms-0.01 and tp90 <= base_p90+0.03
                        and tpos <= base_pos-0.50 and tmin >= base_min-0.15):
                    rank=(tpos,tw,-tmin,tp90)
                    if best is None or rank < best[0]:
                        best=(rank,trial[bi])
        if best is not None:
            core[bi]=best[1]
    return tuple(core)

def _complete_strong_residual_peaks(data,target,bands,profile=None,max_extra=2):
    """Add cut-only bands for strong peaks left behind by the stable core."""
    p=profile or AutoEQProfile(); core=tuple(bands)
    for _ in range(int(max_extra)):
        if len(core)>=p.max_filters: break
        pred=_predicted_mag_only(data,core)
        resid=np.asarray(pred,float)-np.asarray(target,float)
        peaks,props=find_peaks(resid,prominence=0.80,height=2.20)
        if len(peaks)==0: break
        good=np.asarray(data.weights)>1e-6
        base=compute_metrics(data,target,pred,core)
        _,base_action_after=_actionable_cut_wrms(data,target,pred,p)
        base_danger=_dangerous_new_dip_count(data,target,pred)
        accepted=None
        order=sorted(range(len(peaks)),key=lambda k:float(resid[int(peaks[k])]),reverse=True)
        for k in order:
            i=int(peaks[k]); f0=float(data.grid_hz[i]); peak=float(resid[i])
            if data.quality[i]<p.quality_floor or data.reliability[i]<p.quality_floor: continue
            if data.deep_null_mask[i]: continue
            if f0>=p.hf_trend_only_hz: continue
            if any(b.type=='P' and abs(math.log2(f0/max(float(b.f_hz),1e-9)))<0.10 for b in core): continue
            octd=np.abs(np.log2(np.asarray(data.grid_hz,float)/f0)); ids=np.flatnonzero(octd<=0.18)
            if ids.size<5: continue
            lo=int(ids[0]); hi=int(ids[-1])+1; bloc=resid[lo:hi]
            bpos=float(np.max(bloc)); bmin=float(np.min(bloc))
            width=peak_widths(resid,peaks,rel_height=0.5)[0][k]
            step=float(np.median(np.diff(np.log2(data.grid_hz))))
            qseed=estimate_q_from_peak_width(max(step,float(width)*step),p)
            qvals=sorted(set([float(qseed),6.0,8.0,10.0,12.0,16.0]))
            for qv in qvals:
                if qv>p.max_resonance_q+1e-9: continue
                for frac in (0.45,0.60,0.75,0.90):
                    gv=float(np.clip(-frac*peak,p.max_cut_db,-p.min_effective_gain_db))
                    trial=core+(AutoEQBand('P',f0,gv,qv),)
                    tpred=_predicted_mag_only(data,trial); tr=np.asarray(tpred)-np.asarray(target)
                    met=compute_metrics(data,target,tpred,trial)
                    tloc=tr[lo:hi]; tpos=float(np.max(tloc)); tmin=float(np.min(tloc))
                    _,trial_action_after=_actionable_cut_wrms(data,target,tpred,p)
                    trial_danger=_dangerous_new_dip_count(data,target,tpred)
                    global_ok=met.weighted_rms_db <= base.weighted_rms_db-0.015
                    actionable_ok=(
                        (base_action_after-trial_action_after) >= 0.03
                        and met.weighted_rms_db <= base.weighted_rms_db+0.03
                    )
                    if ((global_ok or actionable_ok)
                            and trial_danger <= base_danger
                            and met.p90_abs_error_db <= base.p90_abs_error_db+0.03
                            and met.worst_abs_error_db <= base.worst_abs_error_db+0.05
                            and tpos <= bpos-0.75 and tmin >= bmin-0.50):
                        rank=(tpos,trial_action_after,met.weighted_rms_db,-tmin,met.p90_abs_error_db)
                        if accepted is None or rank<accepted[0]:
                            accepted=(rank,trial)
        if accepted is None: break
        core=accepted[1]
    return core

def _anti_overshoot_refine(data,target,bands,profile=None):
    """Reduce cut-skirt overshoot without giving back meaningful peak control.

    A speaker-EQ cut is not allowed to turn a previously near-target shoulder
    into a deep local dip. Fc stays fixed; only Gain/Q are adjusted.
    """
    p=profile or AutoEQProfile(); core=list(bands)
    srcres=np.asarray(data.mag_raw_db,float)-np.asarray(target,float)
    trusted=(np.asarray(data.quality)>=p.boost_quality_floor)&(np.asarray(data.reliability)>=p.boost_quality_floor)&(np.asarray(data.weights)>1e-6)

    def local_bad_and_pen(resid,fc):
        octd=np.abs(np.log2(np.asarray(data.grid_hz,float)/max(float(fc),1e-9)))
        ids=np.flatnonzero(octd<=0.24)
        if ids.size<5:
            return [],0.0,ids,octd
        protect=trusted & (srcres>-2.0) & (octd<=0.24)
        pen=float(np.sum(np.maximum(0.0,-2.5-resid[protect])))
        loc=resid[ids]
        mins,_=find_peaks(-loc,prominence=0.35)
        bad=[]
        for j in mins:
            i=int(ids[j])
            if protect[i] and resid[i]<-2.5 and (resid[i]-srcres[i])<-0.75:
                bad.append(i)
        return bad,pen,ids,octd

    for bi in range(len(core)):
        b=core[bi]
        if b.type!='P' or b.gain_db>=0:
            continue
        pred=_predicted_mag_only(data,tuple(core))
        resid=np.asarray(pred,float)-np.asarray(target,float)
        bad,pen,ids,_=local_bad_and_pen(resid,b.f_hz)
        if not bad:
            continue
        base=compute_metrics(data,target,pred,tuple(core))
        base_pos=float(np.max(resid[ids])) if ids.size else 0.0
        qvals=sorted(set([
            float(b.q),
            min(p.max_resonance_q,max(float(b.q)+1.0,float(b.q)*1.25)),
            min(p.max_resonance_q,max(float(b.q)+2.0,float(b.q)*1.50)),
            8.0,10.0,12.0,16.0,
        ]))
        best=None
        for qv in qvals:
            if qv<p.min_q or qv>p.max_resonance_q+1e-9:
                continue
            for scale in (1.0,.92,.84,.76,.68,.60,.52,.44,.36):
                gv=float(b.gain_db)*scale
                trial=list(core)
                trial[bi]=AutoEQBand('P',float(b.f_hz),gv,float(qv))
                trial=tuple(trial)
                tpred=_predicted_mag_only(data,trial)
                tr=np.asarray(tpred,float)-np.asarray(target,float)
                met=compute_metrics(data,target,tpred,trial)
                tbad,tpen,tids,_=local_bad_and_pen(tr,b.f_hz)
                tpos=float(np.max(tr[tids])) if tids.size else 0.0
                if met.weighted_rms_db>base.weighted_rms_db+0.08:
                    continue
                if met.p90_abs_error_db>base.p90_abs_error_db+0.05:
                    continue
                if met.worst_abs_error_db>base.worst_abs_error_db+0.10:
                    continue
                if tpos>base_pos+0.75:
                    continue
                rank=(len(tbad),tpen,max(tpos,0.0),met.weighted_rms_db,met.p90_abs_error_db)
                if best is None or rank<best[0]:
                    best=(rank,trial[bi])
        if best is not None and best[0][0]<=len(bad) and best[0][1]<pen-1e-6:
            core[bi]=best[1]
    return tuple(core)

def _residual_span_db(data,target,mag_pred):
    """Robust residual spread on weighted bins for R2.3 acceptance."""
    resid=np.asarray(mag_pred,float)-np.asarray(target,float)
    good=(np.asarray(data.weights,float)>1e-6)&np.isfinite(resid)
    vals=resid[good] if np.any(good) else resid[np.isfinite(resid)]
    if vals.size<2:
        return 0.0
    return float(np.percentile(vals,95.0)-np.percentile(vals,5.0))

def _coupled_neighbor_band_refine(data,target,bands,profile=None):
    """R2.3: jointly refine nearby PEQ pairs without adding topology.

    Two adjacent PEQs are optimized together in Fc/G/Q while every other band
    remains fixed.  A pair is committed only when WRMS, P90 and robust residual
    span all improve and no extra trustworthy dip is created.
    """
    p=profile or AutoEQProfile(); core=list(bands)
    if len(core)<2:
        return tuple(core)
    order=sorted(range(len(core)),key=lambda i:float(core[i].f_hz))
    for oi in range(len(order)-1):
        ia,ib=order[oi],order[oi+1]
        a,b=core[ia],core[ib]
        if a.type!='P' or b.type!='P':
            continue
        dist=abs(math.log2(max(float(b.f_hz),1e-9)/max(float(a.f_hz),1e-9)))
        if dist>0.35:
            continue
        base_bands=tuple(core)
        base_pred=_predicted_mag_only(data,base_bands)
        base=compute_metrics(data,target,base_pred,base_bands)
        base_span=_residual_span_db(data,target,base_pred)
        base_dips=_dangerous_new_dip_count(data,target,base_pred)
        x0=np.asarray([
            math.log2(float(a.f_hz)),float(a.gain_db),math.log(float(a.q)),
            math.log2(float(b.f_hz)),float(b.gain_db),math.log(float(b.q)),
        ],float)
        qhi_a=p.max_resonance_q if a.gain_db<=0 else p.max_q
        qhi_b=p.max_resonance_q if b.gain_db<=0 else p.max_q
        # Keep each Fc local and preserve band order/topology.
        mid=0.5*(math.log2(float(a.f_hz))+math.log2(float(b.f_hz)))
        alo=max(math.log2(p.f_min_hz),math.log2(float(a.f_hz))-0.18)
        ahi=min(mid-1e-4,math.log2(float(a.f_hz))+0.18)
        blo=max(mid+1e-4,math.log2(float(b.f_hz))-0.18)
        bhi=min(math.log2(min(p.f_max_hz,0.45*data.sample_rate)),math.log2(float(b.f_hz))+0.18)
        if ahi<=alo or bhi<=blo:
            continue
        ga_lo,ga_hi=(p.max_cut_db,-p.min_effective_gain_db) if a.gain_db<0 else (p.min_effective_gain_db,p.max_boost_db)
        gb_lo,gb_hi=(p.max_cut_db,-p.min_effective_gain_db) if b.gain_db<0 else (p.min_effective_gain_db,p.max_boost_db)
        lo=np.asarray([alo,ga_lo,math.log(p.min_q),blo,gb_lo,math.log(p.min_q)],float)
        hi=np.asarray([ahi,ga_hi,math.log(qhi_a),bhi,gb_hi,math.log(qhi_b)],float)
        def unpack_pair(x):
            trial=list(core)
            trial[ia]=AutoEQBand('P',2**float(x[0]),float(x[1]),math.exp(float(x[2])))
            trial[ib]=AutoEQBand('P',2**float(x[3]),float(x[4]),math.exp(float(x[5])))
            return tuple(trial)
        # Search objective: retain the global robust fit, but explicitly expose
        # the local residual shared by this pair. This prevents a narrow 120-130 Hz
        # error from being numerically drowned by hundreds of remote bins.
        pair_fc=math.sqrt(float(a.f_hz)*float(b.f_hz))
        local_mask=np.abs(np.log2(np.asarray(data.grid_hz,float)/max(pair_fc,1e-9)))<=0.42
        def fun(x):
            trial=unpack_pair(x)
            global_r=solver_residual(data,target,trial,p)
            lpred=_predicted_mag_only(data,trial)
            le=(np.asarray(target,float)-np.asarray(lpred,float))*np.sqrt(np.maximum(np.asarray(data.weights,float),1e-9))
            return np.r_[global_r,2.5*le[local_mask]]
        try:
            res=least_squares(fun,x0,bounds=(lo,hi),loss=p.robust_loss,f_scale=p.f_scale_db,
                              max_nfev=max(35,p.max_solver_nfev),xtol=1e-6,ftol=1e-6,gtol=1e-6)
            trial=unpack_pair(res.x)
        except Exception:
            continue
        # The unconstrained local optimum can over-correct a shoulder. Walk
        # conservatively from the original pair toward that optimum and keep the
        # strongest safe point that still improves all three global metrics.
        best_safe=None
        for alpha in (1.0,.90,.80,.70,.60,.55,.50,.48,.46,.45,.42,.40,.35,.30,.25,.20,.15):
            mixed=list(base_bands)
            for idx,src,dst in ((ia,a,trial[ia]),(ib,b,trial[ib])):
                lf=(1.0-alpha)*math.log2(float(src.f_hz))+alpha*math.log2(float(dst.f_hz))
                lg=(1.0-alpha)*float(src.gain_db)+alpha*float(dst.gain_db)
                lq=(1.0-alpha)*math.log(float(src.q))+alpha*math.log(float(dst.q))
                mixed[idx]=AutoEQBand('P',2**lf,lg,math.exp(lq))
            mixed=tuple(mixed)
            mpred=_predicted_mag_only(data,mixed)
            mmet=compute_metrics(data,target,mpred,mixed)
            mspan=_residual_span_db(data,target,mpred)
            mdips=_dangerous_new_dip_count(data,target,mpred)
            if not (mmet.weighted_rms_db < base.weighted_rms_db-0.002
                    and mmet.p90_abs_error_db < base.p90_abs_error_db-0.002
                    and mspan < base_span-0.002
                    and mdips <= base_dips):
                continue
            local_res=np.asarray(mpred,float)-np.asarray(target,float)
            local_abs=float(np.max(np.abs(local_res[local_mask]))) if np.any(local_mask) else float('inf')
            rank=(local_abs,mmet.weighted_rms_db,mmet.p90_abs_error_db,mspan,-alpha)
            if best_safe is None or rank<best_safe[0]:
                best_safe=(rank,mixed)
        if best_safe is not None:
            core=list(best_safe[1])
    return tuple(core)

def _coupled_shoulder_refine(data,target,bands,profile=None):
    """R2.4: refine a close PEQ pair and one existing shoulder band.

    Preserve band count, order and gain signs. Search is local and bounded;
    reject a candidate unless WRMS, P90, span and the local residual improve.
    Fixed per-bin dip protection prevents trading an old dip for a new one.
    """
    p=profile or AutoEQProfile(); core=tuple(bands)
    if len(core)<3:
        return core
    f=np.asarray(data.grid_hz,float); t=np.asarray(target,float)
    weights=np.asarray(data.weights,float)
    trusted=(np.asarray(data.quality)>=p.boost_quality_floor)&(np.asarray(data.reliability)>=p.boost_quality_floor)&(weights>1e-6)
    order=sorted(range(len(core)),key=lambda i:core[i].f_hz)
    groups=[]
    for pos in range(len(order)-1):
        ia,ib=order[pos:pos+2]
        a,b=core[ia],core[ib]
        if a.type!='P' or b.type!='P' or math.log2(b.f_hz/a.f_hz)>0.35:
            continue
        for near in (pos-1,pos+2):
            if not 0<=near<len(order):
                continue
            ic=order[near]; c=core[ic]
            if c.type=='P' and min(abs(math.log2(c.f_hz/a.f_hz)),abs(math.log2(c.f_hz/b.f_hz)))<=1.0:
                groups.append((ia,ib,ic))
    for ia,ib,ic in groups:
        base_bands=core
        bp=_predicted_mag_only(data,core)
        br=np.asarray(bp)-t
        base=compute_metrics(data,t,bp,core)
        span=_residual_span_db(data,t,bp)
        local=(np.abs(np.log2(f/math.sqrt(core[ia].f_hz*core[ib].f_hz)))<=0.42)&trusted
        if np.count_nonzero(local)<5 or np.max(np.abs(br[local]))<1.0:
            continue
        src=np.asarray(data.mag_raw_db)-t
        protect=trusted&(src>-2.0)
        floor=np.minimum(br,-2.95)
        idxs=sorted((ia,ib,ic),key=lambda i:core[i].f_hz)
        x0=[]; lo=[]; hi=[]
        pair_center=math.sqrt(core[ia].f_hz*core[ib].f_hz)
        pair_mid=0.5*(math.log2(core[ia].f_hz)+math.log2(core[ib].f_hz))
        fhi=min(p.f_max_hz,0.45*data.sample_rate)
        for idx in idxs:
            b=core[idx]; center=math.log2(b.f_hz)
            if idx==ic:
                # Shoulder compensator is an existing PEQ, so its DSP order is
                # irrelevant. Allow it to cross Fc with the pair and move into
                # the shoulder region; preserve count, type and gain sign.
                lower=math.log2(max(p.f_min_hz,pair_center*0.94))
                upper=math.log2(min(fhi,max(pair_center*1.60,b.f_hz*1.02)))
            else:
                lower=max(math.log2(p.f_min_hz),center-0.25)
                upper=min(math.log2(fhi),center+0.25)
                # Only preserve ordering inside the coupled cut pair itself.
                if idx==ia: upper=min(upper,pair_mid-1e-5)
                if idx==ib: lower=max(lower,pair_mid+1e-5)
            gl,gh=(p.max_cut_db,-p.min_effective_gain_db) if b.gain_db<0 else (p.min_effective_gain_db,p.max_boost_db)
            qh=p.max_resonance_q if b.gain_db<0 else p.max_q
            x0.extend((center,b.gain_db,math.log(b.q)))
            lo.extend((lower,gl,math.log(p.min_q)))
            hi.extend((upper,gh,math.log(qh)))
        x0=np.asarray(x0); lo=np.asarray(lo); hi=np.asarray(hi)
        if np.any(lo>=hi) or np.any(x0<lo-1e-9) or np.any(x0>hi+1e-9):
            continue
        x0=np.clip(x0,lo,hi)
        def unpack(x):
            trial=list(base_bands)
            for j,idx in enumerate(idxs):
                lf,g,lq=x[3*j:3*j+3]
                trial[idx]=AutoEQBand('P',2**float(lf),float(g),math.exp(float(lq)))
            return tuple(trial)
        best=None
        # Optimize against the actual constraints, rather than hoping that a
        # soft shoulder penalty will happen to yield a feasible solution.
        for local_weight in (1.0,4.0):
            def objective(x):
                trial=unpack(x)
                pred=_predicted_mag_only(data,trial)
                r=np.asarray(pred)-t
                return float(local_weight*np.average(r[local]**2,weights=weights[local])
                             +np.average(r**2,weights=weights))
            def constraints(x):
                trial=unpack(x)
                pred=_predicted_mag_only(data,trial)
                met=compute_metrics(data,t,pred,trial)
                return np.r_[base.weighted_rms_db-met.weighted_rms_db,
                             base.p90_abs_error_db-met.p90_abs_error_db,
                             span-_residual_span_db(data,t,pred),
                             (np.asarray(pred)-t-floor)[protect]]
            try:
                fit=minimize(objective,x0,method='SLSQP',bounds=list(zip(lo,hi)),
                    constraints={'type':'ineq','fun':constraints},
                    options={'maxiter':max(35,p.max_solver_nfev),'ftol':1e-7})
            except (ValueError,FloatingPointError):
                continue
            if not np.all(np.isfinite(fit.x)) or np.any(fit.x<lo) or np.any(fit.x>hi):
                continue
            for alpha in (1.,.9,.8,.7,.6,.5,.4,.3,.2,.1):
                trial=unpack(x0+alpha*(fit.x-x0))
                pred=_predicted_mag_only(data,trial)
                r=np.asarray(pred)-t
                if not np.all(np.isfinite(r)) or np.any(r[protect]<floor[protect]-1e-8):
                    continue
                met=compute_metrics(data,t,pred,trial)
                sp=_residual_span_db(data,t,pred)
                if (met.deep_null_boost_count or met.low_quality_boost_count
                    or met.weighted_rms_db>=base.weighted_rms_db-.002
                    or met.p90_abs_error_db>=base.p90_abs_error_db-.002
                    or sp>=span-.002
                    or _dangerous_new_dip_count(data,t,pred)>_dangerous_new_dip_count(data,t,bp)):
                    continue
                peak=float(np.max(np.abs(r[local])))
                if peak>=float(np.max(np.abs(br[local])))-.002:
                    continue
                rank=(peak,met.weighted_rms_db,met.p90_abs_error_db,sp)
                if best is None or rank<best[0]:best=(rank,trial)
        if best is not None:core=best[1]
    return core


def _dangerous_new_dip_count(data,target,mag_after):
    """Hard do-no-harm guard for newly-created local dips below -3 dB."""
    srcres=np.asarray(data.mag_raw_db,float)-np.asarray(target,float)
    resid=np.asarray(mag_after,float)-np.asarray(target,float)
    trusted=(np.asarray(data.quality)>=0.65)&(np.asarray(data.reliability)>=0.65)&(np.asarray(data.weights)>1e-6)
    mins,_=find_peaks(-resid,prominence=0.40)
    n=0
    for i in mins:
        i=int(i)
        if trusted[i] and srcres[i]>-2.0 and resid[i]<-3.0 and (resid[i]-srcres[i])<-0.75:
            n+=1
    return int(n)

def _salvage_dangerous_new_dips(data,target,bands,profile=None):
    """Preserve useful EQ while removing only cut energy that creates new dips.

    Final safety used to reject the whole plan when one PEQ skirt created a
    trustworthy local dip.  Try gain attenuation first, then drop only the
    offending cut if necessary.  A candidate must strictly reduce dangerous
    dip count; among equally safe candidates choose the lowest WRMS.
    """
    p=profile or AutoEQProfile()
    core=tuple(bands)
    if not core:
        return core,0,0
    pred=_predicted_mag_only(data,core)
    initial=_dangerous_new_dip_count(data,target,pred)
    current=int(initial)
    if current<=0:
        return core,0,0
    max_steps=max(1,len(core)*2)
    for _ in range(max_steps):
        best=None
        for j,b in enumerate(core):
            if b.type!='P' or float(b.gain_db)>=0.0:
                continue
            # Prefer the smallest attenuation that clears/reduces the dip.
            for scale in (0.90,0.85,0.80,0.70,0.60,0.50,0.40):
                gv=float(b.gain_db)*float(scale)
                if abs(gv)<p.min_effective_gain_db:
                    continue
                trial=list(core)
                trial[j]=AutoEQBand(b.type,float(b.f_hz),gv,float(b.q))
                trial=tuple(trial)
                tm=_predicted_mag_only(data,trial)
                nd=_dangerous_new_dip_count(data,target,tm)
                if nd>=current:
                    continue
                met=compute_metrics(data,target,tm,trial)
                rank=(int(nd),float(met.weighted_rms_db),float(met.p90_abs_error_db),-float(scale))
                if best is None or rank<best[0]:
                    best=(rank,trial,int(nd))
            # Last resort: remove only this cut, never zero the whole plan.
            trial=tuple(x for k,x in enumerate(core) if k!=j)
            if trial:
                tm=_predicted_mag_only(data,trial)
                nd=_dangerous_new_dip_count(data,target,tm)
                if nd<current:
                    met=compute_metrics(data,target,tm,trial)
                    rank=(int(nd),float(met.weighted_rms_db),float(met.p90_abs_error_db),1.0)
                    if best is None or rank<best[0]:
                        best=(rank,trial,int(nd))
        if best is None:
            break
        core=best[1]
        current=best[2]
        if current<=0:
            break
    return tuple(core),int(initial),int(current)

def reoptimize_after_prune(data,target,bands,profile=None):
    p=profile or AutoEQProfile()
    base=optimize_joint_bands(data,target,merge_nearby_bands(prune_weak_bands(bands,p),p),p)
    base=stabilize_band_q(base,p)
    base=_optimize_joint_gains_fast(data,target,base,p)

    # Prefer exact residual-peak Fc, but only when snapping does not create new
    # shoulders.  This preserves peak authority on clean captures while falling
    # back to the numerically optimized Fc when a hard snap worsens P90/WRMS.
    snapped=_lock_cut_centers_to_residual_peaks(data,target,base)
    snapped=_optimize_joint_gains_fast(data,target,snapped,p)
    if snapped != base:
        bpred=_predicted_mag_only(data,base)
        spred=_predicted_mag_only(data,snapped)
        good=np.asarray(data.weights)>1e-6
        bwrms=_wrms_from_mag(data,target,bpred); swrms=_wrms_from_mag(data,target,spred)
        bp90=float(np.percentile(np.abs(np.asarray(target)[good]-bpred[good]),90)) if np.any(good) else 0.0
        sp90=float(np.percentile(np.abs(np.asarray(target)[good]-spred[good]),90)) if np.any(good) else 0.0
        if swrms <= bwrms+0.03 and sp90 <= bp90+0.03:
            base=snapped
    base=_refine_narrow_resonance_cuts(data,target,base,p)
    base=_complete_strong_residual_peaks(data,target,base,p,max_extra=3)
    # Final speaker-EQ polish: correct cut-skirt overshoot without moving Fc.
    base=_anti_overshoot_refine(data,target,base,p)
    # R2.3: nearby PEQs can interact strongly. Refine adjacent pairs together,
    # but accept only a strict WRMS + P90 + residual-span win with no new dip.
    base=_coupled_neighbor_band_refine(data,target,base,p)
    base=_coupled_shoulder_refine(data,target,base,p)
    return prune_weak_bands(base,p)

def _nearest_idx(grid,f): return int(np.argmin(np.abs(np.log(np.asarray(grid)/max(f,1e-9)))))
def compute_metrics(data: AnalysisCurves,target,mag_pred,bands=()):
    e=np.asarray(target)-np.asarray(mag_pred); w=np.asarray(data.weights); good=w>1e-6
    wrms=float(np.sqrt(np.sum(w*e*e)/max(np.sum(w),1e-12))); ae=np.abs(e[good]) if np.any(good) else np.abs(e)
    deep=lowq=0
    null_mask=np.asarray(data.deep_null_mask,bool)
    low_mask=np.asarray(data.quality)<0.65
    for b in bands:
        if b.gain_db<=0: continue
        contrib=20*np.log10(np.maximum(np.abs(biquad_response(data.grid_hz,b,data.sample_rate)),_EPS))
        if np.any(null_mask & (contrib>0.25)): deep+=1
        # Low-quality safety is local/energy based: reject a boost centered in
        # unreliable data or one whose positive correction energy is dominated
        # by unreliable bins. A remote skirt barely touching one low-Q bin is
        # not itself a low-quality correction.
        idx=_nearest_idx(data.grid_hz,b.f_hz)
        pos=np.maximum(contrib,0.0); energy=pos*pos
        low_frac=float(np.sum(energy[low_mask])/max(np.sum(energy),1e-12))
        if data.quality[idx] < 0.65 or low_frac > AutoEQProfile().low_quality_energy_fraction_max: lowq+=1
    gains=[b.gain_db for b in bands]; qs=[b.q for b in bands]
    return AutoEQMetrics(wrms,float(np.percentile(ae,90)) if len(ae) else 0.0,float(np.max(ae)) if len(ae) else 0.0,min(gains) if gains else 0.0,max(gains) if gains else 0.0,max(qs) if qs else 0.0,len(bands),sum(max(0,b.gain_db) for b in bands),deep,lowq)
def evaluate_do_no_harm(before,after,bands,profile=None):
    p=profile or AutoEQProfile()
    if after.deep_null_boost_count or after.low_quality_boost_count: return 'NO_SAFE_SOLUTION'
    if any((b.gain_db>p.max_boost_db+1e-9 or b.gain_db<p.max_cut_db-1e-9 or b.q<p.min_q-1e-9
            or (b.gain_db>0 and b.q>p.max_q+1e-9)
            or (b.gain_db<=0 and b.q>p.max_resonance_q+1e-9)) for b in bands): return 'NO_SAFE_SOLUTION'
    imp=before.weighted_rms_db-after.weighted_rms_db; rel=imp/max(before.weighted_rms_db,1e-9)
    if before.weighted_rms_db < 0.20:
        return 'NO_EQ_NEEDED'
    # AEQ-CLOSEOUT-R2: for an already-smooth capture (<1 dB WRMS), the old
    # fixed 0.20 dB absolute-improvement gate can suppress a correction that is
    # still large in relative terms. Admit a Preview only when BOTH a modest
    # absolute gain and a strong relative gain are present; higher-error traces
    # keep the original production thresholds unchanged.
    if before.weighted_rms_db < 1.0:
        if imp < 0.12 or rel < 0.10:
            return 'NO_EQ_NEEDED'
    elif imp < 0.20 or rel < 0.05:
        return 'NO_EQ_NEEDED'
    if after.p90_abs_error_db > before.p90_abs_error_db+0.05:
        # Sparse resonant peaks can occupy <10% of bins, so pre-EQ P90 may be
        # near zero even when worst/WRMS error is severe.  Do not veto a strong,
        # cut-only correction merely because the PEQ skirt becomes visible in P90.
        sparse_cut_win = (
            bool(bands)
            and all(float(b.gain_db) <= 0.0 for b in bands)
            and rel >= 0.25
            and (before.worst_abs_error_db-after.worst_abs_error_db) >= 0.50
        )
        # A locally trusted boost can reduce the dominant dip dramatically while
        # making a previously near-zero P90 shoulder modestly visible. The hard
        # deep-null / low-quality boost checks above remain authoritative, so
        # admit only a strong all-boost improvement with a tightly bounded P90 cost.
        trusted_boost_win = (
            bool(bands)
            and all(float(b.gain_db) > 0.0 for b in bands)
            and rel >= 0.25
            and (before.worst_abs_error_db-after.worst_abs_error_db) >= 0.75
            and after.p90_abs_error_db <= before.p90_abs_error_db + 0.50
        )
        if not (sparse_cut_win or trusted_boost_win):
            return 'NO_SAFE_SOLUTION'
    return 'PREVIEW_READY'

def _practical_boost_conflicts(data, target, bands, profile=None):
    """Boosts on a measured excess must not undo a nearby meaningful cut.

    Use actual biquad overlap, not Fc distance alone: narrow opposing bands
    correcting two separate features are not necessarily redundant.
    """
    if not any(b.gain_db>0 for b in bands): return ()
    p=profile or AutoEQProfile()
    f=np.asarray(data.grid_hz,float)
    original=np.asarray(data.mag_raw_db)-np.asarray(target)
    conflicts=[]
    full=_predicted_mag_only(data,bands)
    full_rms=compute_metrics(data,target,full,bands).weighted_rms_db
    for i,b in enumerate(bands):
        if b.gain_db <= 0: continue
        without=tuple(v for k,v in enumerate(bands) if k!=i)
        bypass=_predicted_mag_only(data,without)
        benefit=compute_metrics(data,target,bypass,without).weighted_rms_db-full_rms
        if benefit < p.practical_boost_benefit_db:
            # A real, localized deficit may occupy too few bins to move global
            # WRMS by 0.1 dB. Require measurable local benefit on trusted source
            # deficits instead; do not justify a boost by cut-created dips.
            contribution=full-bypass
            local=(original<-.5)&(contribution>=.5)&(data.quality>=p.boost_quality_floor)&(data.reliability>=p.boost_quality_floor)&(~data.deep_null_mask)
            local_benefit=0.
            if np.count_nonzero(local)>=3:
                w=np.maximum(data.weights[local],1e-12)
                local_benefit=float(np.sqrt(np.average((bypass[local]-target[local])**2,weights=w))-np.sqrt(np.average((full[local]-target[local])**2,weights=w)))
            if local_benefit<.5:
                conflicts.append(i); continue
        for cut in bands:
            if cut.gain_db >= 0: continue
            j=int(np.argmin(abs(np.log(f/cut.f_hz))))
            boost_at_cut=float(20*np.log10(max(abs(biquad_response(np.array([f[j]]),b,data.sample_rate)[0]),_EPS)))
            if original[j] > .5 and boost_at_cut >= p.practical_overlap_db and cut.gain_db <= -1.5:
                conflicts.append(i); break
    return tuple(conflicts)


def _practical_cut_refine(data,target,bands,profile=None):
    """Drop conflicting boosts, then refit existing cuts with sign locked.

    No new filters or compensating boosts can be introduced here. The final
    production do-no-harm/salvage path still validates the resulting plan.
    """
    p=profile or AutoEQProfile(); bands=tuple(bands)
    conflicts=_practical_boost_conflicts(data,target,bands,p)
    if not conflicts: return bands
    core=tuple(b for i,b in enumerate(bands) if i not in conflicts)
    ids=[i for i,b in enumerate(core) if b.gain_db<0]
    if not ids: return core
    selected=tuple(core[i] for i in ids)
    x0=pack_solver_params(selected); lo=[]; hi=[]
    for b in selected:
        lo.extend([math.log10(max(p.f_min_hz,b.f_hz/2**.25)),math.log(p.min_q),p.max_cut_db])
        hi.extend([math.log10(min(p.f_max_hz,data.sample_rate*.49,b.f_hz*2**.25)),math.log(p.max_resonance_q if b.type=='P' else p.max_q),-p.min_effective_gain_db])
    def unpack(x):
        trial=list(core)
        for i,b in zip(ids,unpack_solver_params(x,[b.type for b in selected],p)): trial[i]=b
        return tuple(trial)
    original=np.asarray(data.mag_raw_db)-target
    protect=(np.asarray(data.quality)>=p.boost_quality_floor)&(np.asarray(data.reliability)>=p.boost_quality_floor)&(original>-2.)
    floor=np.minimum(_predicted_mag_only(data,bands)-target,-2.95)
    def fun(x):
        trial=unpack(x); pred=_predicted_mag_only(data,trial)
        # Strong shoulder penalty discourages deepening protected bins.
        return np.r_[solver_residual(data,target,trial,p),4*np.maximum(0.,target[protect]-2.8-pred[protect])]
    candidates=[core]
    try:
        fit=least_squares(fun,np.clip(x0,lo,hi),bounds=(lo,hi),max_nfev=p.max_solver_nfev,loss=p.robust_loss,f_scale=p.f_scale_db)
        if np.all(np.isfinite(fit.x)):
            candidates.extend(unpack(x0+a*(fit.x-x0)) for a in (1.,.75,.5,.25))
            constrained=minimize(
                lambda x: objective_cost(data,target,unpack(x),p),fit.x,
                method='SLSQP',bounds=list(zip(lo,hi)),
                constraints=[{'type':'ineq','fun':lambda x: (_predicted_mag_only(data,unpack(x))-target-floor-.001)[protect]}],
                options={'maxiter':60,'ftol':1e-7})
            if np.all(np.isfinite(constrained.x)):
                candidates.append(unpack(constrained.x))
    except (ValueError, FloatingPointError):
        pass
    # First prefer no new dangerous dip, then fit quality; never restore the
    # opposing boost just because its old global RMS was slightly smaller.
    def rank(trial):
        pred=_predicted_mag_only(data,trial)
        m=compute_metrics(data,target,pred,trial)
        violation=float(np.max(np.maximum(0.,floor[protect]-(pred-target)[protect]),initial=0.))
        return (violation>1e-7,_dangerous_new_dip_count(data,target,pred),violation if violation>1e-7 else 0.,m.weighted_rms_db,m.p90_abs_error_db)
    best=min(candidates,key=rank)
    if rank(best)[0]:
        # An unsuccessful constrained solve must not exchange an opposing
        # boost for a newly over-cut shoulder. Back off cuts, dropping weak
        # bands, until a feasible candidate exists (empty cuts is the limit).
        for scale in (.98,.95,.9,.8,.65,.5,.35,.2,.1,0.):
            trial=tuple(AutoEQBand(b.type,b.f_hz,b.gain_db*scale,b.q) if b.gain_db<0 else b
                        for b in best if b.gain_db>=0 or abs(b.gain_db*scale)>=p.min_effective_gain_db)
            candidates.append(trial)
        best=min(candidates,key=rank)
    return best


def _salvage_metric_rejection(data,target,bands,profile=None,*,p90_slack=0.):
    """Recover a lighter signed-gain plan without relaxing acceptance gates."""
    p=profile or AutoEQProfile(); bands=tuple(bands)
    if not bands: return bands
    before=compute_metrics(data,target,data.mag_raw_db,())
    span=_residual_span_db(data,target,data.mag_raw_db)
    source=np.asarray(data.mag_raw_db)-target
    protect=(data.quality>=p.boost_quality_floor)&(data.reliability>=p.boost_quality_floor)&(source>-2.)
    def unpack(x):
        return tuple(AutoEQBand(b.type,b.f_hz,float(g),b.q) for b,g in zip(bands,x))
    def constraints(x):
        trial=unpack(x);pred=_predicted_mag_only(data,trial)
        met=compute_metrics(data,target,pred,trial)
        return np.r_[before.p90_abs_error_db+p90_slack-met.p90_abs_error_db-.001,
                     span-_residual_span_db(data,target,pred)-.001,
                     (pred-target+2.949)[protect]]
    def cost(x):
        trial=unpack(x);pred=_predicted_mag_only(data,trial)
        return compute_metrics(data,target,pred,trial).weighted_rms_db**2
    x0=np.array([b.gain_db for b in bands])
    bounds=[(min(g,0.),max(g,0.)) for g in x0]
    candidates=[]
    for scale in (1.,.25):
        try:
            fit=minimize(cost,x0*scale,method='SLSQP',bounds=bounds,
                         constraints=[{'type':'ineq','fun':constraints}],
                         options={'maxiter':70,'ftol':1e-7})
            if np.all(np.isfinite(fit.x)):
                candidates.append(tuple(b for b in unpack(fit.x) if abs(b.gain_db)>=p.min_effective_gain_db))
        except (ValueError,FloatingPointError):
            continue
    safe=[]
    for trial in candidates:
        pred=_predicted_mag_only(data,trial);met=compute_metrics(data,target,pred,trial)
        if (trial and evaluate_do_no_harm(before,met,trial,p)=='PREVIEW_READY'
            and met.p90_abs_error_db<=before.p90_abs_error_db+p90_slack
            and _residual_span_db(data,target,pred)<span
            and not _dangerous_new_dip_count(data,target,pred)
            and np.all((pred-target)[protect]>=-2.95)
            and not _practical_boost_conflicts(data,target,trial,p)):
            safe.append((met.weighted_rms_db,trial))
    if safe: return min(safe,key=lambda x:x[0])[1]
    if p90_slack==0.:
        # Prefer P90 improvement, then use the existing acceptance tolerance
        # (0.05 dB) with margin. Never widen the production safety gate.
        return _salvage_metric_rejection(data,target,bands,p,p90_slack=.04)
    return bands


def _refine_corrected_peaks(data,target,bands,profile=None):
    """Scan reliable residual features; reuse CUTs before spending DSP slots.

    Budgets are relative to the entry plan, never reset after accepted moves.
    Small global RMS tradeoffs require a much larger local improvement; deep
    valleys, unreliable data and original do-no-harm checks remain protected.
    """
    p=profile or AutoEQProfile(); core=tuple(bands); added=0; evaluated=0
    if not core: return core
    f=np.asarray(data.grid_hz); t=np.asarray(target); logf=np.log2(f)
    trusted=(data.quality>=max(.5,p.quality_floor))&(data.reliability>=max(.5,p.quality_floor))&(~data.deep_null_mask)
    protect=(data.quality>=p.quality_floor)&(data.reliability>=p.quality_floor)
    initial_pred=_predicted_mag_only(data,core);initial=initial_pred-t
    entry=compute_metrics(data,t,initial_pred,core)
    original_metrics=compute_metrics(data,t,data.mag_raw_db,())
    # Existing valleys may deepen by at most the shoulder allowance. Bins near
    # target have a separate small allowance; deep-null boosting is never used.
    floor=np.minimum(initial,-3.)-p.residual_shoulder_budget_db
    negative=protect&(initial<0)
    for _ in range(p.residual_max_passes):
        if evaluated>=p.residual_eval_budget: break
        base_pred=_predicted_mag_only(data,core);res=base_pred-t
        base=compute_metrics(data,t,base_pred,core);span=_residual_span_db(data,t,base_pred)
        peaks,props=find_peaks(res,prominence=.6,height=1.2)
        widths=peak_widths(res,peaks,rel_height=.5)[0] if len(peaks) else []
        features=[]
        for k,i in enumerate(peaks):
            if not trusted[i] or f[i]>=p.hf_trend_only_hz: continue
            width=max(float(widths[k]*np.median(np.diff(logf))),.03)
            priority=float(res[i]*props['prominences'][k]*data.reliability[i])
            features.append((priority,int(i),width))
        features.sort(reverse=True)
        accepted=None
        for _,i,width in features[:8]:
            fc=float(f[i]);local=np.abs(logf-logf[i])<=max(1/12,min(1/6,width))
            if np.count_nonzero(local)<3: continue
            def consider(trial,is_new):
                nonlocal accepted,evaluated
                if evaluated>=p.residual_eval_budget: return
                evaluated+=1
                pred=_predicted_mag_only(data,trial);r=pred-t
                energy=(pred-base_pred)**2
                if np.sum(energy[protect])/max(float(np.sum(energy)),1e-12)<.7: return
                gain=float(np.max(res[local])-np.max(r[local]))
                if gain<.6 or np.any(r[protect]<floor[protect]): return
                if np.any(initial[negative]-r[negative]>p.residual_negative_budget_db): return
                # Avoid spending a band simply to exchange one local error for
                # another: positive excess energy must fall on reliable bins.
                excess=lambda x: float(np.sum(np.maximum(x[protect]-.5,0.)**2))
                if excess(r)>=excess(res)-.1: return
                met=compute_metrics(data,t,pred,trial)
                if evaluate_do_no_harm(original_metrics,met,trial,p)=='NO_SAFE_SOLUTION': return
                if met.weighted_rms_db>entry.weighted_rms_db+p.residual_wrms_budget_db: return
                if met.weighted_rms_db-base.weighted_rms_db>gain*.01: return
                if met.p90_abs_error_db>entry.p90_abs_error_db+p.residual_p90_budget_db: return
                if _residual_span_db(data,t,pred)>span+1e-8: return
                if _dangerous_new_dip_count(data,t,pred): return
                if met.deep_null_boost_count or met.low_quality_boost_count: return
                if _practical_boost_conflicts(data,t,trial,p): return
                # Select the strongest useful correction, charging for damage
                # to negative residuals and for extra DSP bands.
                loss=float(np.max(np.maximum(res[negative]-r[negative],0.),initial=0.))
                score=gain-2*loss-20*max(0.,met.weighted_rms_db-base.weighted_rms_db)-.1*is_new
                if score<=.1: return
                rank=(-score,met.weighted_rms_db)
                if accepted is None or rank<accepted[0]: accepted=(rank,trial,is_new)
            nearby=sorted((j for j,b in enumerate(core) if b.type=='P' and b.gain_db<0 and abs(math.log2(b.f_hz/fc))<=.35),key=lambda j:abs(math.log2(core[j].f_hz/fc)))[:2]
            # Infer a bandwidth seed from the measured feature, not a trace ID.
            qseed=float(np.clip(1./(2*np.sinh(np.log(2)*width/2)),p.min_q,p.max_resonance_q))
            for j in nearby:
                b=core[j]
                for freq in sorted(set((fc,b.f_hz))):
                    for qv in sorted(set((qseed,float(np.clip(b.q*.75,p.min_q,p.max_resonance_q)),b.q,p.max_resonance_q))):
                        for scale in (.5,.75,1.):
                            gv=max(p.max_cut_db,b.gain_db-float(res[i])*scale)
                            trial=list(core);trial[j]=AutoEQBand('P',freq,gv,qv)
                            consider(tuple(trial),False)
            if accepted is not None: break
            if added>=p.residual_max_new_bands or len(core)>=p.max_filters or sum(b.type=='P' for b in core)>=p.max_peq: continue
            for qv in sorted(set((qseed,4.,8.,12.,16.))):
                if qv>p.max_resonance_q: continue
                for scale in (.5,.75,1.):
                    consider(core+(AutoEQBand('P',fc,max(p.max_cut_db,-float(res[i])*scale),qv),),True)
            if accepted is not None: break
        if accepted is None: break
        core=accepted[1];added+=int(accepted[2])
    return core


def _design_unified_autoeq_impl(inp: AutoEQInput,profile: AutoEQProfile|None=None):
    p=profile or AutoEQProfile(); data=prepare_analysis_curves(inp,p); target=build_target(data,inp)
    empty=tuple(); one=np.ones_like(data.h_corr); before=compute_metrics(data,target,data.mag_raw_db,empty)
    trusted_coverage=float(np.mean(np.asarray(data.quality)>=p.boost_quality_floor))
    low_global_coverage=trusted_coverage < p.min_trustworthy_coverage
    warnings=[]
    if low_global_coverage:
        warnings.append(f'LOW_QUALITY_COVERAGE_LOCAL_BOOST_ONLY:{trusted_coverage:.3f}')
    seed=seed_greedy_bands(data,target,p); opt=optimize_joint_bands(data,target,seed,p); bands=reoptimize_after_prune(data,target,opt,p)
    # Safety salvage: one unsafe boost must not discard useful peak cuts.
    # Joint optimization may move a boost away from its high-quality seed into
    # a low-quality/null region; prune only those boosts before final verdict.
    if bands:
        _safe=[]
        _safe_boost_seeds=[_s for _s in seed if float(_s.gain_db) > 0.0]
        for _b in bands:
            if float(_b.gain_db) <= 0.0:
                _safe.append(_b); continue
            _sm=compute_metrics(data,target,data.mag_raw_db,(_b,))
            if not _sm.deep_null_boost_count and not _sm.low_quality_boost_count:
                _safe.append(_b); continue
            # Joint optimization can broaden a locally trusted boost until its
            # skirt spills into low-coherence bins. Do not lose the correction:
            # fall back to the nearest original seed, which already passed the
            # local support / coherence / deep-null candidate gates.
            _fallback=None
            if _safe_boost_seeds:
                _fallback=min(
                    _safe_boost_seeds,
                    key=lambda _s: abs(math.log2(max(float(_s.f_hz),1e-9)/max(float(_b.f_hz),1e-9))),
                )
                if abs(math.log2(max(float(_fallback.f_hz),1e-9)/max(float(_b.f_hz),1e-9))) > 0.45:
                    _fallback=None
            if _fallback is not None:
                _fm=compute_metrics(data,target,data.mag_raw_db,(_fallback,))
                if not _fm.deep_null_boost_count and not _fm.low_quality_boost_count:
                    _safe.append(_fallback)
        bands=tuple(_safe)
    # Low global coverage is advisory only. Boost candidates already pass
    # strict local quality/reliability/support/deep-null gates above, so do not
    # discard a locally trustworthy correction merely because remote frequency
    # regions have poor coherence.
    _conflicts=_practical_boost_conflicts(data,target,bands,p)
    while _conflicts:
        bands=_practical_cut_refine(data,target,bands,p)
        warnings.append(f'PRACTICAL_OPPOSING_BOOST_REMOVED:{len(_conflicts)}')
        _conflicts=_practical_boost_conflicts(data,target,bands,p)
    heq,hpred,mp,pp=predict_response(data,bands); after=compute_metrics(data,target,mp,bands); status=evaluate_do_no_harm(before,after,bands,p)
    if status=='NO_SAFE_SOLUTION' and bands:
        recovered=_salvage_metric_rejection(data,target,bands,p)
        if recovered!=bands:
            bands=recovered
            heq,hpred,mp,pp=predict_response(data,bands)
            after=compute_metrics(data,target,mp,bands)
            status=evaluate_do_no_harm(before,after,bands,p)
            warnings.append('METRIC_REJECTION_GAIN_REFIT')
    # AEQ-FLAT-R1: global WRMS can be dominated by cancellation nulls that the
    # safety layer intentionally refuses to boost. Preserve a useful cut-only
    # correction when the trustworthy, non-null region improves materially.
    if (
        status == 'NO_EQ_NEEDED'
        and bands
        and all(float(_b.gain_db) <= 0.0 for _b in bands)
        and before.weighted_rms_db >= 1.0
    ):
        _ab,_aa=_actionable_cut_wrms(data,target,mp,p)
        _aimp=_ab-_aa
        _arel=_aimp/max(_ab,1e-9)
        if _aimp >= 0.15 and _arel >= 0.025:
            status='PREVIEW_READY'
            warnings.append(f'ACTIONABLE_CUT_SALVAGE:{_aimp:.3f}:{_arel:.3f}')
    # Hard speaker-EQ do-no-harm: never accept a correction that creates a
    # trustworthy new local dip below -3 dB from a previously near-target region.
    # AEQ-FLAT-R1: salvage the plan instead of rejecting all PEQ because one cut
    # skirt overshoots. Attenuate/drop only the offending cut, then re-evaluate.
    _dangerous_dips=_dangerous_new_dip_count(data,target,mp) if bands else 0
    if status=='PREVIEW_READY' and _dangerous_dips:
        _salvaged,_dip_before,_dip_after=_salvage_dangerous_new_dips(data,target,bands,p)
        if _salvaged and _salvaged != bands:
            bands=tuple(_salvaged)
            heq,hpred,mp,pp=predict_response(data,bands)
            after=compute_metrics(data,target,mp,bands)
            status=evaluate_do_no_harm(before,after,bands,p)
            # Re-apply the trusted cut-only salvage after gain attenuation.
            # The old order could turn a valid safe plan back into NO_EQ_NEEDED
            # because global WRMS is dominated by nulls we intentionally do not boost.
            if (
                status == 'NO_EQ_NEEDED'
                and bands
                and all(float(_b.gain_db) <= 0.0 for _b in bands)
                and before.weighted_rms_db >= 1.0
            ):
                _sab,_saa=_actionable_cut_wrms(data,target,mp,p)
                _simp=_sab-_saa
                _srel=_simp/max(_sab,1e-9)
                if _simp >= 0.15 and _srel >= 0.025:
                    status='PREVIEW_READY'
                    warnings.append(f'ACTIONABLE_CUT_POST_DIP_SALVAGE:{_simp:.3f}:{_srel:.3f}')
            _dangerous_dips=_dangerous_new_dip_count(data,target,mp)
            warnings.append(f'NEW_TRUSTED_DIP_SALVAGED:{int(_dip_before)}->{int(_dangerous_dips)}')
        if _dangerous_dips:
            status='NO_SAFE_SOLUTION'
            warnings.append(f'NEW_TRUSTED_DIP:{int(_dangerous_dips)}')
    if low_global_coverage and not bands and before.weighted_rms_db >= 0.20:
        status='NO_SAFE_SOLUTION'
    if status=='PREVIEW_READY':
        refined=_refine_corrected_peaks(data,target,bands,p)
        if refined!=bands:
            bands=refined
            heq,hpred,mp,pp=predict_response(data,bands)
            after=compute_metrics(data,target,mp,bands)
            warnings.append('CORRECTED_PEAK_REFINEMENT')
    if status!='PREVIEW_READY':
        bands=tuple(); heq=one; hpred=data.h_corr.copy(); mp=data.mag_raw_db.copy(); pp=np.degrees(np.unwrap(np.angle(hpred))); after=compute_metrics(data,target,mp,bands)
    return AutoEQPlan(status,bands,data.grid_hz.copy(),np.asarray(target).copy(),heq.copy(),hpred.copy(),mp.copy(),pp.copy(),before,after,tuple(warnings))


def design_unified_autoeq(inp: AutoEQInput,profile: AutoEQProfile|None=None):
    # Per-call/thread isolation; exact keys include grid bytes, rate and every
    # coefficient parameter. Never reuse source/plan state between user runs.
    # Reuse only if the enclosing AUTO request explicitly owns the cache.
    # Direct solver calls retain their old per-call isolation.
    if _response_cache.get() is not None:
        return _design_unified_autoeq_impl(inp,profile)
    token=_response_cache.set({'grids':{},'bands':OrderedDict()})
    try:
        return _design_unified_autoeq_impl(inp,profile)
    finally:
        _response_cache.reset(token)
