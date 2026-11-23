"""V8.59: match the *shape* of a coherent peak, not just its apex.

Do not broaden an EQ by simply lowering Q. Re-evaluate Frequency,
Gain and Q together against the measured shoulder and guard WRMS,
other bins, deep dips, source Q limits, spacing and filter count.
"""
from __future__ import annotations
import numpy as np
from .autoeq_engine import (
    AutoEQBand, biquad_response, compute_metrics,
)
from .spacing import close_pairs, MIN_SPACING_OCT


def refine_cut_peak_shoulder(data, target, previous_mag, new_band,
                             existing_bands, profile):
    """Return (safe_band, predicted_mag, note) for one *new* PEQ.

    This does not modify the original measured TF, earlier filters or
    render/export identity. Local windows are only high-coherence bins
    that were positive residual BEFORE adding the new cut.
    """
    freq=np.asarray(data.grid_hz,float)
    target=np.asarray(target,float)
    previous=np.asarray(previous_mag,float)
    oldbands=tuple(existing_bands)
    sample_rate=float(data.sample_rate)
    def predict(band):
        return previous+20*np.log10(np.maximum(
            abs(biquad_response(freq,band,sample_rate)),1e-15))
    original=predict(new_band)
    if (new_band.type!="P" or new_band.gain_db>=0 or
            len(freq)!=len(previous) or len(freq)!=len(target) or
            not np.isfinite(previous).all()):
        return new_band,original,""
    center=float(new_band.f_hz)
    trust=((freq>=profile.f_min_hz)&(freq<=profile.f_max_hz)&
           (data.quality>=.80)&(data.reliability>=.70)&
           (~data.deep_null_mask)&(data.weights>1e-5))
    # Local peak island: avoid treating a neighboring deep dip as
    # another "shoulder" that should be cut more.
    local=(trust&(abs(np.log2(freq/center))<=.30)&
           (previous-target>=.7))
    if np.count_nonzero(local)<6:
        return new_band,original,""
    base_res=original-target
    base_max=float(np.max(base_res[local]))
    if base_max<2.0:  # No meaningful remaining positive shoulder.
        return new_band,original,""
    oldmetrics=compute_metrics(data,target,original,oldbands+(new_band,))
    protected=trust&(base_res<=-1.5)
    best=None
    min_q=max(3.,float(profile.min_q))
    max_q=min(8.,float(profile.max_resonance_q))
    cut_limit=float(profile.max_cut_db)
    for factor in (.94,.955,.97,.985,1.,1.015):
        fc=center*factor
        if not profile.f_min_hz<=fc<=profile.f_max_hz:
            continue
        if any(abs(np.log2(fc/x.f_hz))<MIN_SPACING_OCT for x in oldbands):
            continue
        for q in np.arange(3.,8.01,.5):
            if q<min_q or q>max_q:continue
            for gain in np.arange(max(-9.,cut_limit),-.49,.5):
                band=AutoEQBand("P",float(fc),float(gain),float(q))
                pred=predict(band)
                residual=pred-target
                local_max=float(np.max(residual[local]))
                local_min=float(np.min(residual[local]))
                if (local_max>base_max-.70 or local_min<-1.5):
                    continue
                if protected.any() and float(np.min(
                        (pred-original)[protected]))<-.65:
                    continue
                metrics=compute_metrics(data,target,pred,oldbands+(band,))
                if (metrics.weighted_rms_db >
                        oldmetrics.weighted_rms_db+.08 or
                    metrics.p90_abs_error_db >
                        oldmetrics.p90_abs_error_db+.25 or
                    metrics.worst_abs_error_db >
                        oldmetrics.worst_abs_error_db+.25):
                    continue
                score=(max(abs(local_max),abs(local_min))+
                       .3*max(metrics.weighted_rms_db-
                              oldmetrics.weighted_rms_db,0))
                if best is None or score<best[0]:
                    best=(score,band,pred,local_max,metrics.weighted_rms_db)
    if best is None:
        return new_band,original,""
    _,band,pred,local_max,new_wrms=best
    if close_pairs(oldbands+(band,)):
        raise ValueError("Shoulder refinement violated PEQ spacing")
    note=(f"PEAK_SHOULDER_REFINED {center:.0f}->{band.f_hz:.0f}Hz "
          f"Q {new_band.q:.1f}->{band.q:.1f}, "
          f"residual +{base_max:.2f}->+{local_max:.2f}dB, "
          f"weighted RMS delta {new_wrms-oldmetrics.weighted_rms_db:+.3f}dB")
    return band,pred,note
