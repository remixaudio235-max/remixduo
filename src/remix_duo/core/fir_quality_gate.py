"""QA: quality gate on the *actual physical FIR taps* before GUI export.

Static original Smaart TRF is immutable, no GUI/audio or DSP writes.
The target response alone is NEVER an acceptance proof.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.signal import freqz
from scipy.ndimage import gaussian_filter1d

@dataclass(frozen=True)
class FIRQuality:
    accepted:bool
    reasons:tuple[str,...]
    mag_rms_before_db:float|None
    mag_rms_after_db:float|None
    max_filter_boost_db:float
    max_filter_cut_db:float
    phase_before_deg:float|None
    phase_after_deg:float|None
    phase_coverage_octaves:float

def evaluate_fir_quality(preview,result,lf,hf,*,max_boost_db=6.0,
                         max_cut_db=-12.0,epsilon_db=.5):
    """Quality gate in log-frequency with the physically realized kernel.

    Dynamic native pixel registration is NOT used for physical quality.
    This gate follows source bytes and the filter actually exported.
    """
    freqs=np.asarray(preview.freqs,float)
    raw=np.asarray(preview.original_db,float)
    kernel=np.asarray(result.taps,float)
    fs=int(result.fs);lf=float(lf);hf=float(hf)
    if (freqs.ndim!=1 or len(freqs)<35 or np.any(np.diff(freqs)<=0)
            or kernel.ndim!=1 or len(kernel)<64
            or not np.all(np.isfinite(kernel))
            or not (freqs[0]<=lf<hf<=min(freqs[-1],fs*.49))):
        return FIRQuality(False,("FIR input/ROI không hợp lệ",),None,None,
                          float("nan"),float("nan"),None,None,0.)
    grid=np.geomspace(lf,hf,128)
    _,actual=freqz(kernel,worN=grid,fs=fs)
    filter_db=20*np.log10(np.maximum(np.abs(actual),1e-12))
    before=np.interp(np.log(grid),np.log(freqs),raw)
    after=before+filter_db
    if not (np.isfinite(before).all() and np.isfinite(after).all()):
        return FIRQuality(False,("Dữ liệu thực tế không hữu hạn",),
                          None,None,float("nan"),float("nan"),None,None,0.)
    max_boost=float(np.max(filter_db));max_cut=float(np.min(filter_db))
    # 1/6-octave evaluation domain: avoid rejecting a 1-bin noisy anomaly.
    octstep=float(np.log2(hf/lf)/127)
    sigma=max(.5,(1/6)/2.355/max(octstep,1e-7))
    b=gaussian_filter1d(before,sigma,mode="nearest")
    aft=gaussian_filter1d(after,sigma,mode="nearest")
    reference=float(np.median(b))
    b_err=np.abs(b-reference)
    a_err=np.abs(aft-reference)
    before_rms=float(np.sqrt(np.mean(np.square(b-reference))))
    after_rms=float(np.sqrt(np.mean(np.square(aft-reference))))
    reasons=[]
    if max_boost>max_boost_db+epsilon_db:
        reasons.append(f"Boost FIR thực +{max_boost:.2f} dB > +{max_boost_db+epsilon_db:.1f} dB")
    if max_cut<max_cut_db-epsilon_db:
        reasons.append(f"Cut FIR thực {max_cut:.2f} dB < {max_cut_db-epsilon_db:.1f} dB")
    improvement=before_rms-after_rms
    coverage=0.
    # Even an UNAPPROVED phase design must report trusted-bin physics,
    # never fall back to the legacy all-coherence preview RMS.
    phase_before=None
    phase_after=None
    if result.mode=="mag":
        # A symmetric linear-phase FIR can add known group delay, but must
        # NOT introduce any non-linear phase rotation in the intended ROI.
        # A sign-flipping lobe of its real response would add 180 degrees.
        f=grid
        centered=actual*np.exp(2j*np.pi*f*(len(kernel)-1)/(2*fs))
        if np.any(np.abs(np.angle(centered,deg=True))>1.0):
            reasons.append("FIR MAG tạo xoay Phase ngoài delay tuyến tính")
        # At least 0.2dB or 5% measurable 1/6-octave flattening.
        minimum=max(.2,.05*before_rms)
        if improvement<minimum:
            reasons.append(f"LF–HF RMS MAG chỉ cải thiện {improvement:+.2f} dB; cần >= {minimum:.2f} dB")
        if float(np.quantile(a_err,.95))>float(np.quantile(b_err,.95))+.5:
            reasons.append("P95 sai lệch MAG trong LF–HF tăng")
        if np.any(a_err-b_err>3.0):
            reasons.append("FIR tạo vùng sai lệch MAG mới >3 dB trong LF–HF")
    elif result.mode=="phase":
        phase_lf=float(getattr(result,"phase_lf_hz",lf) or lf)
        coverage=float(np.log2(max(hf,phase_lf)/max(lf,phase_lf))) if phase_lf<hf else 0.
        if coverage<.5:
            reasons.append(f"Không đủ độ phân giải FIR Phase: chỉ sửa {coverage:.2f} octave trong LF–HF; tăng taps")
        # Magnitude must remain effectively transparent for phase-only FIR.
        if max(abs(max_boost),abs(max_cut))>1.5:
            reasons.append(f"FIR Phase làm lệch MAG tới {max(abs(max_boost),abs(max_cut)):.2f} dB >1.5 dB")
        # Safety proof: measure the SAME trusted frequency bins (>=0.65
        # coherence) for original and actual H*FIR. The preview is already
        # trusted, but independent global + TWO LF/HF halves must also pass.
        from .fir_preview import phase_excess_rms
        orig=np.asarray(getattr(preview,"original_complex",None),complex)
        coh=np.asarray(preview.coherence,float)
        if orig.shape!=freqs.shape or coh.shape!=freqs.shape:
            reasons.append("Không có dữ liệu complex/coherence gốc để xác minh pha")
        else:
            mid=float(np.sqrt(lf*hf))
            third1=lf*(hf/lf)**(1./3.)
            third2=lf*(hf/lf)**(2./3.)
            from .fir_preview import (phase_guard_reference,phase_guard_score,
                                      phase_dense_delay_guard)
            fixed_ref=phase_guard_reference(freqs,orig,coh,lf,hf,gate=.65)
            if fixed_ref is None:
                reasons.append("FIR Phase HOLD: no fixed coherent source reference")
            # Dense test runs on actual windowed physical taps, not MTW
            # source bins; reject delay hidden between measured frequencies.
            target=getattr(result,"phase_target_rad",None)
            if target is None:
                reasons.append("FIR Phase HOLD: target phase reference missing")
            else:
                dense_ok,dense_reason,_=phase_dense_delay_guard(
                    kernel,fs,result.hz,target)
                if not dense_ok:
                    reasons.append("FIR Phase HOLD: "+dense_reason)
            regional=[]
            # Two resolutions: halves protect crossover boundaries; thirds
            # expose localized deterioration masked by a global phase win.
            for lo,hi,label in ((lf,hf,"TOTAL"),
                                (lf,mid,"LF"),(mid,hf,"HF"),
                                (lf,third1,"LF_THIRD"),
                                (third1,third2,"MID_THIRD"),
                                (third2,hf,"HF_THIRD")):
                roi=(freqs>=lo)&(freqs<=hi)
                trusted=roi&np.isfinite(coh)&(coh>=.65)&(
                    np.isfinite(orig.real)&np.isfinite(orig.imag))&(
                    np.abs(orig)>1e-8)
                total=int(np.count_nonzero(roi))
                good=int(np.count_nonzero(trusted))
                # Unknown Phase is NOT evidence of improvement. Prevent
                # design from chasing an unreliable section of LF–HF.
                minimum=25 if label in ("TOTAL","LF","HF") else 20
                if good<minimum or total==0:
                    reasons.append(
                        f"{label}: chỉ {good}/{total} bin coherence≥0.65; "
                        "không đủ chứng cứ pha")
                    continue
                if good/total<.65:
                    # A measured subset may still show a real regression,
                    # but low coverage NEVER authorizes export. Keep the
                    # diagnostic numbers to explain the HOLD to the user.
                    reasons.append(
                        f"{label}: chỉ {good}/{total} bin coherence≥0.65; "
                        "độ phủ dưới 65% — FIR HOLD")
                b,a,_,n=phase_guard_score(
                    fixed_ref,kernel,fs,lo,hi,min_bins=minimum)
                if (b is None or a is None or
                        not np.isfinite([b,a]).all()):
                    reasons.append(f"{label}: không đo được Excess Phase RMS")
                    continue
                regional.append((label,float(b),float(a)))
                # An independent conservative check preserves the V8.179/V8.180
                # low-frequency crossover non-regression contract. Sparse HF
                # unwrap is not reliable: use only bins up to 1 kHz here.
                if label!="TOTAL" and hi<=1000:
                    old_b,old_a,_,_=phase_excess_rms(
                        freqs,orig,coh,kernel,fs,lo,hi,
                        coherence_floor=.65,min_bins=minimum)
                    if old_b is not None and old_a is not None:
                        old_tol=max(.40,float(old_b)*.01)
                        if old_a>old_b+old_tol:
                            reasons.append(
                                f"{label}: Phase tệ hơn (kiểm tra LF độc lập): "
                                f"{old_b:.2f} -> {old_a:.2f} deg; FIR HOLD")
                if label=="TOTAL":
                    phase_before,phase_after=float(b),float(a)
            if len(regional)==6:
                _,phase_before,phase_after=regional[0]
                min_deg=max(.05,phase_before*.05)
                if phase_before-phase_after<min_deg:
                    reasons.append(
                        f"TOTAL: Excess Phase {phase_before:.2f}°→"
                        f"{phase_after:.2f}°; cải thiện <5%")
                for label,b,a in regional[1:]:
                    tol=max(.40,b*.01)  # sub-degree numerical/window noise
                    if a>b+tol:
                        reasons.append(
                            f"{label}: Phase tệ hơn {b:.2f}°→{a:.2f}° "
                            f"(+{a-b:.2f}° > {tol:.2f}°)")
    else:
        reasons.append("FIR mode không hợp lệ")
    return FIRQuality(not reasons,tuple(reasons),before_rms,after_rms,
                      max_boost,max_cut,phase_before,phase_after,coverage)
