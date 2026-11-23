"""Physical FIR preview, independent of native overlay calibration."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import freqz
from .smoothing import smooth_phase_unit_phasor

def cascade_magnitude(freq, h, kernel, fs):
    """Physical source and source×FIR magnitudes on measured bins."""
    f=np.asarray(freq,dtype=float)
    h=np.asarray(h,dtype=complex)
    _,response=freqz(kernel,worN=f,fs=fs)
    before=20*np.log10(np.maximum(abs(h),1e-12))
    after=20*np.log10(np.maximum(abs(h*response),1e-12))
    return before,after,response

@dataclass(frozen=True)
class FIRSource:
    revision:int
    source_name:str
    identity:str
    freqs:np.ndarray
    original_db:np.ndarray
    after_db:np.ndarray
    coherence:np.ndarray
    original_phase:np.ndarray
    after_phase:np.ndarray
    phase_valid:np.ndarray
    fs:int
    taps:int
    range_lf:float=30.
    range_hf:float=16000.
    mode:str="mag"
    delay_ms:float=0.
    display_phase:np.ndarray|None=None
    phase_rms_before:float|None=None
    phase_rms_after:float|None=None
    phase_improvement_pct:float|None=None
    phase_quality_bins:int=0
    # V8.134: Smaart Phase smoothing the display model was built with.
    phase_smooth_oct:float=1/6
    # Raw display inputs retained so changing Smaart smoothing can reraster
    # the preview without redesigning or altering the exported FIR taps.
    original_complex:np.ndarray|None=None
    compensated_response:np.ndarray|None=None


def phase_guard_reference(freq, h, coh, lf, hf, *, gate=.75):
    """Create ONE immutable phase/delay reference over the complete band.

    MTW source frequencies can be too sparse to unwrap independently at HF.
    Bulk delay and circular phase origin are therefore estimated ONCE on the
    reliable original source, not re-fit in each sub-band or FIR candidate.
    This measures principal excess-phase error: a bounded diagnostic, not an
    assertion about absolute, unwrapped propagation phase.
    """
    f=np.asarray(freq,float)
    h=np.asarray(h,complex)
    c=np.asarray(coh,float)
    if (f.ndim!=1 or h.shape!=f.shape or c.shape!=f.shape or
            not (np.isfinite([lf,hf,gate]).all() and 0<lf<hf)):
        return None
    valid=((f>=lf)&(f<=hf)&(c>=gate)&np.isfinite(c)&
           np.isfinite(f)&np.isfinite(h.real)&np.isfinite(h.imag)&
           (np.abs(h)>1e-8))
    if np.count_nonzero(valid)<35:
        return None
    x=f[valid]
    c0=c[valid]
    z=h[valid]/np.abs(h[valid])
    from .phase_tools import remove_bulk_delay
    _,tau=remove_bulk_delay(x,h[valid],np.maximum(c0,.05)**2)
    if not np.isfinite(tau):
        return None
    z=z*np.exp(2j*np.pi*x*tau)
    origin=np.angle(np.sum(np.maximum(c0,.05)**2*z))
    if not np.isfinite(origin):
        return None
    z=z*np.exp(-1j*origin)
    return x,z,np.rad2deg(np.angle(z))


def phase_guard_score(reference, kernel, fs, lf, hf, *, min_bins=35):
    """Same bins/delay/phase origin before and after real FIR convolution."""
    if reference is None:
        return None,None,None,0
    x,z,before_deg=reference
    region=(x>=lf)&(x<=hf)
    count=int(np.count_nonzero(region))
    if count<min_bins:
        return None,None,None,count
    kernel=np.asarray(kernel,float)
    if kernel.ndim!=1 or kernel.size<2 or not np.isfinite(kernel).all():
        return None,None,None,count
    from scipy.signal import freqz
    _,resp=freqz(kernel,worN=x[region],fs=fs)
    if (not np.isfinite(resp.real).all() or
            not np.isfinite(resp.imag).all() or np.any(np.abs(resp)<1e-5)):
        return None,None,None,count
    delay=(len(kernel)-1)/(2*fs)
    before=before_deg[region]
    # The known causal FIR delay is explicitly removed in both measurement
    # and GUI compensated preview; it is NOT removed from exported taps.
    after=np.rad2deg(np.angle(z[region]*resp*
                              np.exp(2j*np.pi*x[region]*delay)))
    rms=lambda v:float(np.sqrt(np.mean(np.square(v))))
    pre,post=rms(before),rms(after)
    if not np.isfinite([pre,post]).all():
        return None,None,None,count
    return pre,post,float(100*(1-post/max(pre,1e-10))),count


def fir_response_on_grid(kernel, fs, freq):
    """Evaluate the FIR exactly on an FFT grid; otherwise use scipy.freqz.

    A float-frequency vector passed to freqz disables its FFT fast path.
    This helper recognizes the actual nonnegative RFFT bin grid, preventing
    tens of millions of needless matrix operations for 4096 taps.
    """
    kernel=np.asarray(kernel,dtype=float)
    f=np.asarray(freq,dtype=float)
    fft_n=2*(f.size-1)
    if (f.ndim==1 and f.size>=3 and kernel.ndim==1 and
            kernel.size<=fft_n and np.isfinite(f).all() and
            np.isfinite(kernel).all() and
            np.allclose(f,np.linspace(0,fs*.5,f.size),
                        rtol=0,atol=max(1e-8,abs(fs)*1e-12))):
        return np.fft.rfft(kernel,n=fft_n)
    _,response=freqz(kernel,worN=f,fs=fs)
    return response


def phase_dense_delay_guard(kernel, fs, freq_grid, intended_phase,
                            max_delay_error_ms=0.5):
    """Check unintended physical excess delay using DENSE FIR response.

    Coarse/MTW phase samples cannot identify propagation delays differing by
    integer multiples of 1/delta_f. Instead evaluate the *actual windowed
    kernel* at its full design FFT spacing against the *design phase*, after
    removing only the intended causal midpoint latency. The signed residual
    slope is a delay in seconds; a broadband 10-ms shift MUST fail.
    This check is complementary to the independent source circular RMS.
    """
    taps=np.asarray(kernel,dtype=np.float64)
    f=np.asarray(freq_grid,dtype=np.float64)
    target=np.asarray(intended_phase,dtype=np.float64)
    if (taps.ndim!=1 or taps.size<2 or not np.isfinite(taps).all() or
            f.ndim!=1 or f.size<256 or target.shape!=f.shape or
            not np.isfinite(f).all() or not np.isfinite(target).all() or
            not (np.isfinite(fs) and fs>0 and np.isfinite(max_delay_error_ms)
                 and max_delay_error_ms>0) or
            not np.all(np.diff(f)>0)):
        return False,"invalid dense-delay inputs",None
    usable=(f>=20)&(f<=min(20000,fs*.45))
    if np.count_nonzero(usable)<256:
        return False,"not enough dense frequency bins",None
    fx=f[usable]
    resp=fir_response_on_grid(taps,fs,f)[usable]
    if (not np.isfinite(resp.real).all() or
            not np.isfinite(resp.imag).all() or
            np.min(np.abs(resp))<.15):
        return False,"unreliable dense FIR response",None
    delay=(len(taps)-1)/(2*fs)
    # The target is a smooth bounded correction (not the original TRF);
    # compare against it at ALL frequency bins, not only sparse source bins.
    error=np.unwrap(np.angle(resp*np.exp(2j*np.pi*fx*delay)*
                                np.exp(-1j*target[usable])))
    # Linear least-squares slope of error = -2*pi*f*tau_extra.
    # Unwrap is safe here because the design FFT grid is dense.
    slope=np.polyfit(fx,error,1)[0]
    extra_ms=float(-slope/(2*np.pi)*1000)
    if not np.isfinite(extra_ms):
        return False,"nonfinite residual group delay",None
    if abs(extra_ms)>max_delay_error_ms:
        return False,(f"unintended dense FIR delay {extra_ms:+.3f} ms "
                      f"(limit ±{max_delay_error_ms:.3f} ms)"),extra_ms
    return True,"PASS",extra_ms


def phase_excess_rms(freq,h,coh,kernel,fs,lf,hf,*,coherence_floor=0.,
                     min_bins=35):
    """TF-valid RMS after independently removing each bulk phase slope.

    This diagnostic measures *excess* phase; never promises an absolutely
    horizontal physical phase curve or modifies the FIR/exported coefficients.
    """
    f=np.asarray(freq,float)
    h=np.asarray(h,complex)
    c=np.asarray(coh,float)
    mask=((f>=lf)&(f<=hf)&np.isfinite(h.real)&np.isfinite(h.imag)&
          (np.abs(h)>1e-8))
    # Backward-compatible core preview: coherence=0 mode includes ALL
    # physically valid TF bins, even if source coherence is missing.
    # Only the independent export-quality verdict opts into >=.65.
    if coherence_floor>0.:
        mask&=np.isfinite(c)&(c>=coherence_floor)
    if np.count_nonzero(mask)<min_bins:
        return None,None,None,int(np.count_nonzero(mask))
    good_f=f[mask]
    # V8.136: coherence is reference-only; every valid TF bin contributes
    # equally to the physical before/after quality measurement.
    weights=np.ones(int(np.count_nonzero(mask)),dtype=float)
    # V8.105: de-rotate the bulk delay before unwrapping (sparse MTW grids
    # alias np.unwrap). The detrend below removes the same linear phase.
    from .phase_tools import remove_bulk_delay
    _,bulk=remove_bulk_delay(good_f,h[mask],weights**2)
    measured=(np.unwrap(np.angle(h[mask]*np.exp(2j*np.pi*good_f*bulk)))
              -2*np.pi*good_f*bulk)
    _,filter_response=freqz(kernel,worN=good_f,fs=fs)
    if not (np.isfinite(filter_response.real).all() and
            np.isfinite(filter_response.imag).all()):
        return None,None,None,int(np.count_nonzero(mask))
    delay=(len(kernel)-1)/(2*fs)
    correction=np.unwrap(np.angle(
        filter_response*np.exp(2j*np.pi*good_f*delay)))
    after=measured+correction
    def rms_detrended(phase):
        line=np.polyfit(good_f,phase,1,w=weights)
        return float(np.sqrt(np.mean(np.square(
            np.rad2deg(phase-np.polyval(line,good_f))))))
    before_rms=rms_detrended(measured)
    after_rms=rms_detrended(after)
    reduction=100*(1-after_rms/max(before_rms,1e-10))
    return before_rms,after_rms,float(reduction),int(np.count_nonzero(mask))


# V8.131 (user: "gate coherence=0 để phase không bị đứt nét"): the preview
# line is drawn for every valid TF bin like Smaart's own trace. V8.136 also
# makes quality metrics coherence-independent.
PREVIEW_COHERENCE_GATE=0.


def make_source(freq,h,coh,kernel,fs,source_name,identity,revision,lf=30.,hf=16000.,mode="mag",
                phase_smooth_oct=1/6):
    """Complex H_after=H_source*H_FIR, including linear-phase group delay."""
    f=np.asarray(freq,dtype=float)
    h=np.asarray(h,dtype=complex)
    c=np.asarray(coh,dtype=float)
    kernel=np.asarray(kernel,dtype=float)
    if (f.ndim!=1 or f.size<60 or np.any(np.diff(f)<=0) or
            np.any(f<=0) or f[-1]>=fs*.5 or
            h.shape!=f.shape or c.shape!=f.shape or
            not np.isfinite(h.real).all() or
            not np.isfinite(h.imag).all() or
            not np.isfinite(kernel).all() or
            (mode=="mag" and not np.allclose(kernel,kernel[::-1],rtol=0,atol=1e-9)) or
            mode not in ("mag","phase")):
        raise ValueError("Invalid original TRF or FIR complex source")
    mag,after,resp=cascade_magnitude(f,h,kernel,fs)
    orig_phase,valid,_=smooth_phase_unit_phasor(f,h,np.ones_like(c),phase_smooth_oct or None,
                                                PREVIEW_COHERENCE_GATE)
    # Smooth source-display phase ONLY; add the exact complex FIR phase.
    # Smoothing the delayed FIR output would erase its linear group delay
    # through circular cancellation at medium/high frequencies.
    delay=(len(kernel)-1)/(2*fs)
    # Display-only reference removes the *known* FIR group delay.
    # The physical/exported kernel still includes this latency.
    comp=resp*np.exp(2j*np.pi*f*delay)
    phase=np.rad2deg(np.angle(np.exp(1j*np.deg2rad(orig_phase))*comp))
    physical_phase=np.rad2deg(np.angle(np.exp(1j*np.deg2rad(orig_phase))*resp))
    post_valid=valid & (abs(resp)>1e-5)
    # Keep the V8.136 core preview contract: visible Phase and the
    # unfiltered diagnostic include all valid TF bins. The separate
    # V8.180 physical/export gate uses coherence>=.65, and the GUI worker
    # explicitly labels its trusted-bin approval metrics.
    quality=(phase_excess_rms(f,h,c,kernel,fs,lf,hf) if mode=="phase"
             else (None,None,None,0))
    return FIRSource(int(revision),str(source_name),str(identity),f,
                     mag,after,c,orig_phase,physical_phase,post_valid,
                     int(fs),len(kernel),float(lf),float(hf),str(mode),delay*1000,
                     phase,*quality,phase_smooth_oct=float(phase_smooth_oct),
                     original_complex=h.copy(),compensated_response=comp.copy())

