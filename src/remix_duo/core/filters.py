"""RemiX Signal V8.13: offline PEQ preview and FIR design using Smaart TRF data.

Read-only with respect to Smaart and sound hardware. The exported filters
are suggested designs; no sound card/FFT realtime capture/production DSP write.
"""
from dataclasses import dataclass
from pathlib import Path
import struct
import numpy as np
from .traces import matched,TFTrace

@dataclass(frozen=True)
class PEQ:
    freq_hz:float
    gain_db:float
    q:float

@dataclass(frozen=True)
class EQResult:
    hz:np.ndarray
    before_db:np.ndarray
    correction_db:np.ndarray
    after_db:np.ndarray
    peqs:tuple[PEQ,...]
    rms_before:float
    rms_after:float
    bins:int

@dataclass(frozen=True)
class FIRResult:
    taps:np.ndarray
    fs:int
    hz:np.ndarray
    target_db:np.ndarray
    actual_db:np.ndarray
    latency_ms:float
    source:str
    mode:str="mag"
    # FIR Phase only: lowest frequency where phase is actually corrected.
    phase_lf_hz:float|None=None
    # V8.125: non-strict designs never HOLD; every relaxed safety/quality
    # condition is reported here so the UI can show it.
    warnings:tuple=()
    correction_strength:float=1.0
    phase_target_rad:np.ndarray|None=None


# V8.125 (user 2026-11-12: "luôn tạo FIR, giảm bớt các điều kiện"):
# coherence thresholds tried in order when strict=False and data is sparse.
_RELAXED_COHERENCE=(.5,.3,0.)
# V8.132 (user decision "Đặt thiết kế = 0", 2026-11-12): the Duo panel
# (strict=False) designs with coherence gate 0; coherence then only weights
# the bulk-delay fit. strict=True keeps .75 / .6. Measured cost on 18 real
# TRFs: mean PHA gain 30.2% -> 15.2%, 10/70 worse, ripple>1.5 dB 10 -> 22/108.
PANEL_COHERENCE_FLOOR=0.


def _relaxed_valid(make_mask,base,minimum,strict,label,warnings):
    """Coherent-bin mask; non-strict mode lowers the coherence floor
    step by step instead of refusing. Returns (mask, used_threshold)."""
    valid=make_mask(base)
    if not strict and base<=0.:
        # V8.132: gate 0 never refuses; still tell the user when much of the
        # band is untrusted (coherence <0.6), since the FIR follows it there.
        finite=make_mask(-1.)
        low=finite&~make_mask(.6)
        if finite.any() and low.sum()>.3*finite.sum():
            warnings.append(f"{label}: Coherence thấp ở {100*low.sum()/finite.sum():.0f}% "
                            "dải LF–HF (<0.6) → kéo LF/HF sang vùng Coherence cao "
                            "(đường đỏ trên Mag gần 100%)")
    if int(valid.sum())>=minimum or strict:
        return valid,base
    for floor in _RELAXED_COHERENCE:
        valid=make_mask(floor)
        if int(valid.sum())>=minimum:
            warnings.append(f"{label}: Coherence thấp, dùng ngưỡng {floor:.2f} "
                            f"thay vì {base:.2f}")
            return valid,floor
    return valid,None

def source_arrays(engine,source):
    if not engine.current_traces:
        raise ValueError("Chưa có 2 Trace hợp lệ được đọc từ Smaart")
    a,b=engine.current_traces
    if source==0:return a.hz.copy(),a.h.copy(),a.coherence.copy(),a.path.stem
    if source==1:return b.hz.copy(),b.h.copy(),b.coherence.copy(),b.path.stem
    if source!=2:raise ValueError("Invalid source selection")
    pair=engine._ordered_traces()
    if pair is None:raise ValueError("Missing TF pair")
    f,h1,h2,coh=matched(*pair)
    h=h1+h2*np.exp(-2j*np.pi*f*engine.delay.value()/1000.)*(
        -1 if engine.invert.isChecked() else 1)
    return f,h,coh,"SUM (TF Model)"

def _smoothed_db(hz,values,octave=1/6):
    hz=np.asarray(hz,dtype=float)
    values=np.asarray(values,dtype=float)
    if len(hz)!=len(values):raise ValueError("Mismatched freq/magnitude")
    # 1/6-octave support, Gaussian FWHM; use dense enough points for
    # honest broad-feature PEQ fitting, not notches at one isolated bin.
    x=np.log2(hz)
    sig=octave/2.355
    out=np.empty_like(values)
    for i in range(len(values)):
        delta=(x-x[i])/sig
        m=np.abs(delta)<=3
        weight=np.exp(-0.5*delta[m]*delta[m])
        out[i]=float(weight@values[m]/weight.sum())
    return out

def peq_mag_db(freq_hz,peq:PEQ,fs=48000):
    """RBJ Audio EQ Cookbook peaking biquad digital response."""
    f=np.asarray(freq_hz,dtype=float)
    center=np.clip(float(peq.freq_hz),20,0.47*fs)
    q=np.clip(float(peq.q),.3,20)
    a=np.power(10.,float(peq.gain_db)/40.)
    w0=2*np.pi*center/fs
    alpha=np.sin(w0)/(2*q)
    b0=1+alpha*a
    b1=-2*np.cos(w0)
    b2=1-alpha*a
    a0=1+alpha/a
    a1=-2*np.cos(w0)
    a2=1-alpha/a
    z=np.exp(-2j*np.pi*f/fs)
    num=b0+b1*z+b2*z*z
    den=a0+a1*z+a2*z*z
    return 20*np.log10(np.maximum(np.abs(num/den),1e-12))

def auto_peq(hz,h,coherence,target_db=0.0,max_filters=8,
             lf=35,hf=16000,fs=48000):
    hz=np.asarray(hz,dtype=float)
    h=np.asarray(h,dtype=complex)
    coh=np.asarray(coherence,dtype=float)
    if hz.ndim!=1 or len(hz)!=len(h) or len(hz)!=len(coh):
        raise ValueError("Invalid TF arrays")
    mask=(np.isfinite(hz)&np.isfinite(h.real)&np.isfinite(h.imag)&
          np.isfinite(coh)&(coh>=.6)&(hz>=lf)&(hz<=min(hf,.45*fs)))
    if mask.sum()<20:raise ValueError("Không đủ bins có Coherence ≥ 0.60")
    freqs=hz[mask]
    mag_raw=20*np.log10(np.maximum(np.abs(h[mask]),1e-12))
    # Work at 96 sampled logarithmic points to avoid over-fitting the
    # graph's most narrowly-spaced bins.
    ctrl=np.geomspace(max(lf,float(freqs[0])),min(hf,float(freqs[-1])),96)
    observed=np.interp(np.log(ctrl),np.log(freqs),mag_raw)
    smoothed=_smoothed_db(ctrl,observed)
    correction=np.zeros_like(ctrl)
    peqs=[]
    occupied=[]
    for _ in range(min(12,max(1,int(max_filters)))):
        residual=target_db-smoothed-correction
        # Ignore <.7 dB remaining error; don't stack filters at same spot.
        candidates=np.argsort(np.abs(residual))[::-1]
        index=None
        for i in candidates:
            f0=ctrl[i]
            if all(abs(np.log2(f0/old))>.20 for old in occupied):
                index=int(i)
                break
        if index is None or abs(residual[index])<.7:break
        f0=float(ctrl[index])
        gain=float(np.clip(residual[index],-12.,+6.))
        # Wider filters at LF, narrower across MF/HF.
        q=2.0 if f0<180 else (3.2 if f0<2000 else 4.)
        peq=PEQ(round(f0,1),round(gain,2),q)
        response=peq_mag_db(ctrl,peq,fs)
        correction+=response
        occupied.append(f0)
        peqs.append(peq)
    full_corr=np.zeros_like(hz)
    for peq in peqs:
        full_corr+=peq_mag_db(hz,peq,fs)
    before=20*np.log10(np.maximum(np.abs(h),1e-12))
    after=before+full_corr
    valid=(mask)&np.isfinite(before)&np.isfinite(after)
    rms_before=float(np.sqrt(np.mean((smoothed-target_db)**2)))
    rms_after=float(np.sqrt(np.mean((smoothed+correction-target_db)**2)))
    return EQResult(hz,before,full_corr,after,tuple(peqs),
                    rms_before,rms_after,int(valid.sum()))

def design_linear_phase_fir(hz,h,coh,taps=1024,fs=48000,
                            max_boost=6.,max_cut=-12.,lf=30,hf=16000,
                            source="Trace",strict=True):
    taps=int(taps)
    if taps not in (512,1024,2048,4096):
        raise ValueError("Unsupported taps")
    hz=np.asarray(hz,dtype=float)
    mag=20*np.log10(np.maximum(np.abs(h),1e-12))
    coh=np.asarray(coh,dtype=float)
    warnings=[]
    # V8.136: coherence is reference-only for Auto FIR. Design from every
    # finite TF magnitude bin in the requested band for strict and relaxed
    # callers alike; report low coherence without changing the taps.
    valid=(hz>=lf)&(hz<=hf)&np.isfinite(mag)
    reference=valid&(~np.isfinite(coh)|(coh<.60))
    if np.any(reference):
        warnings.append(f"FIR MAG: Coherence thấp (tham khảo) ở "
                        f"{100*reference.sum()/max(valid.sum(),1):.0f}% dải LF–HF")
    if int(valid.sum())<25:
        if strict:
            raise ValueError("FIR: thiếu dữ liệu TF hợp lệ trong LF–HF")
        valid=None
    if valid is None:
        # V8.125: nothing usable in LF-HF -> transparent FIR (delay only).
        warnings.append("FIR MAG: không có dữ liệu trong LF–HF, FIR chỉ là trễ (không sửa)")
        controls=np.geomspace(lf,hf,192)
        correction=np.zeros_like(controls)
    else:
        f=hz[valid]
        db=mag[valid]
        controls=np.geomspace(max(lf,f[0]),min(hf,f[-1]),192)
        smooth=_smoothed_db(controls,np.interp(np.log(controls),np.log(f),db))
        # V8.133: flatten around the trace's OWN level in LF..HF (median of
        # the log-spaced smoothed curve), not absolute 0 dB of the stored TRF.
        # Live TUNNINNGGG-13-1 403-1420 Hz: stored ~+14 dB (Smaart showed +4
        # with a -10 dB trace offset) -> the old target cut 8-12 dB and the
        # whole band sank to -8..-10 dB on screen.
        reference=float(np.median(smooth))
        correction=np.clip(-(smooth-reference),max_cut,max_boost)
    nfft=2**int(np.ceil(np.log2(taps*8)))
    freq=np.fft.rfftfreq(nfft,1/fs)
    # No aggressive equalization outside measured region. Blend in
    # one sixth octave at both edges so finite FIR has no abrupt steps.
    safe=np.clip(freq,1e-9,None)
    gain_db=np.interp(np.log(safe),np.log(controls),correction)
    taper_lo=np.clip(np.log2(safe/lf)/(1/6),0,1)
    taper_hi=np.clip(np.log2(hf/safe)/(1/6),0,1)
    weight=taper_lo*taper_hi
    gain_db*=weight
    gain_db[0]=0
    gain=np.power(10.,gain_db/20.)
    # Center the desired response at the half-sample delay of an even FIR.
    # Averaging an integer-centered impulse with its reverse would instead
    # multiply EVERY design by cos(pi*f/fs), cutting a flat input by 6dB/16k.
    delay=(taps-1)/(2*fs)
    spectrum=gain*np.exp(-2j*np.pi*freq*delay)
    # An even symmetric (Type II) FIR necessarily has zero at Nyquist.
    spectrum[-1]=0.
    kernel=np.fft.irfft(spectrum,nfft)[:taps].copy()
    kernel*=np.kaiser(taps,6)
    # Remove numerical roundoff only; centering was already done spectrally.
    kernel=.5*(kernel+kernel[::-1])
    response=np.fft.rfft(kernel,nfft)
    actual_db=20*np.log10(np.maximum(np.abs(response),1e-12))
    return FIRResult(kernel,fs,freq,gain_db,actual_db,
                     (taps-1)/(2*fs)*1000,source,warnings=tuple(warnings))

# V8.105: a taps-long Kaiser FIR cannot rotate phase below ~N*fs/taps without
# changing magnitude. Empirical N from 12 real Smaart Suite TRFs + synthetic
# crossover all-pass at the default 30-16000 Hz range (QA_V8104 section 5e).
PHASE_RESOLVE_CYCLES=12
# V8.110: absolute tolerance for the never-worse excess-phase gate. Below the
# 0.1 deg display resolution; absorbs platform floating-point noise (Mac arm64
# pure delay measured 1.68e-12 -> 2.30e-12 deg and was wrongly held).
FIR_PHASE_WORSE_TOL_DEG=.05

def design_phase_only_fir(hz,h,coh,taps=1024,fs=48000,lf=30,hf=16000,
                          source="Trace",max_correction_deg=75.,
                          phase_plus=False,strict=True,
                          correction_strength=1.0):
    """Bounded excess-phase FIR. No claim of perfect all-pass behavior.

    Remove the fitted bulk propagation slope from the correction target.
    Apply an exact causal centering delay to the desired complex response.
    Magnitude transparency is checked on the actual windowed taps; reject
    results with >1.5 dB distortion instead of silently changing Mag.
    """
    taps=int(taps)
    if taps not in (512,1024,2048,4096):
        raise ValueError("Unsupported taps")
    correction_strength=float(correction_strength)
    if not 0.<correction_strength<=1.:
        raise ValueError("Invalid FIR Phase correction strength")
    if not 20<=lf<hf<fs*.5 or hf/lf<2:
        raise ValueError("Invalid FIR Phase working range")
    hz=np.asarray(hz,float)
    h=np.asarray(h,complex)
    coh=np.asarray(coh,float)
    if (hz.ndim!=1 or h.shape!=hz.shape or coh.shape!=hz.shape or
            not np.all(np.diff(hz)>0)):
        raise ValueError("Invalid TF array shapes/order")
    warnings=[]
    # V8.136: coherence is diagnostic metadata, never a phase-design mask.
    valid=((hz>=lf)&(hz<=hf)&np.isfinite(h.real)&np.isfinite(h.imag)&
           (abs(h)>1e-8))
    reference=valid&(~np.isfinite(coh)|(coh<.60))
    if np.any(reference):
        warnings.append(f"FIR PHA: Coherence thấp (tham khảo) ở "
                        f"{100*reference.sum()/max(valid.sum(),1):.0f}% dải LF–HF")
    if valid.sum()<35 and strict:
        raise ValueError("FIR Phase: insufficient valid TF bins")
    # Phase is only corrected where this tap count can resolve it; the
    # magnitude gate below still checks the user's full LF..HF range.
    phase_lf=float(max(lf,PHASE_RESOLVE_CYCLES*fs/taps))
    if not strict and phase_lf*1.26>=hf:
        warnings.append(f"FIR PHA: {taps} taps chỉ sửa pha từ {phase_lf:.0f} Hz; "
                        f"dải tới {hf:.0f} Hz cần nhiều taps hơn")
    if valid.sum()<35:
        # V8.125 non-strict: no usable phase data -> transparent FIR.
        warnings.append("FIR PHA: không có dữ liệu pha trong LF–HF, FIR chỉ là trễ (không sửa)")
        controls=np.geomspace(lf,hf,192)
        raw=np.zeros_like(controls)
        smooth=raw
        desired=raw.copy()
    else:
        f=hz[valid]
        # Remove bulk delay (linear phase) without unwrap aliasing on sparse
        # MTW grids; correction targets only excess-phase, never time-advance.
        from .phase_tools import remove_bulk_delay
        weights=np.ones(int(valid.sum()),dtype=float)
        excess,_bulk_delay_s=remove_bulk_delay(f,h[valid],weights)
        controls=np.geomspace(max(lf,f[0]),min(hf,f[-1]),192)
        raw=np.interp(np.log(controls),np.log(f),excess)
        smooth=_smoothed_db(controls,raw,octave=1/3)
        # Use a conservative bounded correction. Never chase phase jumps
        # across a deep null or coherence-failed region.
        desired=np.clip(-smooth,-np.deg2rad(max_correction_deg),
                        np.deg2rad(max_correction_deg))*correction_strength
    if correction_strength<.999:
        warnings.append(f"FIR Phase adaptive correction strength {correction_strength:.2f}")
    nfft=2**int(np.ceil(np.log2(taps*8)))
    freq=np.fft.rfftfreq(nfft,1/fs)
    safe=np.maximum(freq,1e-9)
    phase=np.interp(np.log(safe),np.log(controls),desired)
    # Fade over one third octave to avoid sharp frequency discontinuity.
    weight=np.clip(np.log2(safe/phase_lf)/(1/3),0,1)*np.clip(
        np.log2(hf/safe)/(1/3),0,1)
    phase*=weight
    phase[0]=0.
    phase[-1]=0.
    selected_target_phase=phase.copy()
    delay=(taps-1)/(2*fs)
    desired_spec=np.exp(1j*(phase-2*np.pi*freq*delay))
    desired_spec[0]=desired_spec[0].real
    desired_spec[-1]=desired_spec[-1].real
    # Causal, real impulse, centered around the chosen half-sample delay.
    impulse=np.fft.irfft(desired_spec,nfft)
    kernel=impulse[:taps].copy()
    kernel*=np.kaiser(taps,7.)
    if not np.all(np.isfinite(kernel)):
        raise ValueError("Invalid FIR Phase kernel")
    from scipy.signal import freqz
    from .fir_preview import fir_response_on_grid
    actual=fir_response_on_grid(kernel,fs,freq)
    actual_db=20*np.log10(np.maximum(np.abs(actual),1e-12))
    active=(freq>=lf)&(freq<=hf)
    if not np.any(active) or np.max(np.abs(actual_db[active]))>1.5:
        if strict:
            raise ValueError("FIR Phase HOLD: actual magnitude ripple >1.5 dB")
        ripple=float(np.max(np.abs(actual_db[active]))) if np.any(active) else 0.
        warnings.append(f"FIR PHA: biên độ lệch {ripple:.1f} dB (>1.5 dB)")
    # V8.105: never export a "phase correction" that worsens excess phase
    # where the FIR actually acts. Unverifiable (<35 bins) keeps the prior
    # behaviour; the GUI reports its own excess-RMS diagnostics then.
    from .fir_preview import phase_excess_rms
    acted_before,acted_after,_,_=phase_excess_rms(hz,h,coh,kernel,fs,phase_lf,hf)
    if (acted_before is not None and acted_after is not None and
            acted_after>acted_before+FIR_PHASE_WORSE_TOL_DEG):
        message=(f"Excess Phase tệ hơn ({acted_before:.1f}° → "
                 f"{acted_after:.1f}° từ {phase_lf:.0f} Hz)")
        if strict:
            raise ValueError(f"FIR Phase HOLD: {message}; thử nhiều taps hơn hoặc đổi LF/HF")
        warnings.append("FIR PHA: "+message)
    if phase_plus:
      try:
          # Phase+ is opt-in and uses the requested tap count. Short kernels
          # are allowed to be ATTEMPTED but must pass identical real-response
          # magnitude, early-energy and excess-phase improvement safeguards.
          # Insufficient length fails closed instead of silently selecting 4096.
          if int(valid.sum())<55:
              raise ValueError("FIR Phase+ HOLD: fewer than 55 valid TF bins")
          fine=_smoothed_db(controls,raw,octave=1/12)
          correction=np.clip(-fine,-np.deg2rad(max_correction_deg),
                             np.deg2rad(max_correction_deg))*correction_strength
          new_phase=np.interp(np.log(safe),np.log(controls),correction)
          narrow=1/24
          edge=np.clip(np.log2(safe/phase_lf)/narrow,0,1)*np.clip(
              np.log2(hf/safe)/narrow,0,1)
          new_phase*=edge
          new_phase[0]=0.
          new_phase[-1]=0.
          spec=np.exp(1j*(new_phase-2*np.pi*freq*delay))
          spec[0]=spec[0].real
          spec[-1]=spec[-1].real
          alt=np.fft.irfft(spec,nfft)[:taps].copy()*np.kaiser(taps,3.)
          if not np.isfinite(alt).all():
              raise ValueError("FIR Phase+ HOLD: invalid coefficients")
          alt_db=20*np.log10(np.maximum(abs(np.fft.rfft(alt,nfft)),1e-12))
          full=(freq>=20)&(freq<=min(20000,fs*.45))
          if (np.max(abs(alt_db[full]))>1.5 or
                  np.max(abs(alt_db[active]))>1.5):
              raise ValueError("FIR Phase+ HOLD: magnitude change >1.5 dB")
          mid=taps//2
          early_energy=(np.sum(alt[:mid-int(fs*.005)]**2)/
                        max(np.sum(alt**2),1e-12))
          if early_energy>.002:
              raise ValueError("FIR Phase+ HOLD: early pre-ringing energy >0.2%")
          # Evaluate against the same physical complex input and real FIR taps.
          # Excess phase has the fitted bulk slope removed; it is not raw phase.
          from .fir_preview import phase_excess_rms
          before,old_after,_,_ = phase_excess_rms(hz,h,coh,kernel,fs,lf,hf)
          _,new_after,_,_ = phase_excess_rms(hz,h,coh,alt,fs,lf,hf)
          if (before is None or new_after is None or
                  new_after>=min(before*.95,old_after*.85)):
              raise ValueError(
                  "FIR Phase+ HOLD: safe improvement <15% vs regular FIR")
          kernel=alt
          actual_db=alt_db
          selected_target_phase=new_phase.copy()
      except ValueError as exc:
        if strict:
            raise
        # V8.125: Phase+ failed its gates -> keep the regular FIR PHA.
        warnings.append(f"Phase+ không đạt ({exc}); dùng FIR PHA thường")
    return FIRResult(kernel,int(fs),freq,np.zeros_like(freq),actual_db,
                     delay*1000,source,"phase",phase_lf,
                     warnings=tuple(warnings),
                     correction_strength=correction_strength,
                     phase_target_rad=selected_target_phase)

def save_peq_text(path,result:EQResult):
    path=Path(path)
    lines=["# RemiX Signal EQ QA - Offline PEQ Preview",
           "# Filter,Frequency_Hz,Gain_dB,Q"]
    lines.extend(f"{i},{p.freq_hz:.1f},{p.gain_db:+.2f},{p.q:.2f}"
                 for i,p in enumerate(result.peqs,1))
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def save_fir_txt(path,result:FIRResult):
    path=Path(path)
    lines=[f"# RemiX Signal FIR QA fs={result.fs} taps={len(result.taps)}",
           "# One floating-point coefficient per line"]
    lines.extend(f"{float(x):.12g}" for x in result.taps)
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def save_fir_wav_float(path,result:FIRResult):
    # Portable mono IEEE float32 RIFF, for compatible DSP importers.
    data=np.asarray(result.taps,dtype="<f4").tobytes()
    fmt=struct.pack("<HHIIHH",3,1,result.fs,result.fs*4,4,32)
    chunks=b"fmt "+struct.pack("<I",len(fmt))+fmt
    chunks+=b"data"+struct.pack("<I",len(data))+data
    with open(path,"wb") as out:
        out.write(b"RIFF"+struct.pack("<I",4+len(chunks))+b"WAVE"+chunks)
