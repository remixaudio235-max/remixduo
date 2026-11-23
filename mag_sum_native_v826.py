"""Native read-only SUM magnitude Y registration (V8.26 QA).

Match the actual stored TF shape against visible Smaart traces, then use the
native plot's measured pixel scale. Never center by guessed dB, change H, or
imply an API livestream. Unknown source identity fails closed.
"""
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from smaart_native_mag_fit import capture_native_window,fit_native_mag,NativeMagFrame
from smaart_native_y_grid_v839 import fit_native_mag_grid,saved_mag_grid_interval
from tf_display_smoothing import smooth_log_octaves

@dataclass(frozen=True)
class SumMagAxis:
    accepted: bool
    y_min: float = 0.0
    y_max: float = 0.0
    score: float = 0.0
    source_index: int = -1
    color: str = ""
    reason: str = ""
    bins: int = 0
    x_min: float = 20.0
    x_max: float = 20000.0


def smaart8_raster_candidates(rect):
    """Strict inner-raster candidates ordered for responsive Smaart 8.

    The role detector returns the full chart box, including symmetric axis
    gutters.  Try the geometry-scaled gutter first, then the proven legacy
    widths.  Stop at the first independently verified source match.
    """
    x,y,w,h=map(int,rect)
    result=[]
    for inset in (0,int(round(w*.0225)),20,27,30,35):
        candidate=(x+inset,y,w-2*inset,h)
        if candidate in result or candidate[2]<320:
            continue
        result.append(candidate)
    return tuple(result)

def axis_from_native_image(image, plot_rect, window_rect, traces,
                           *, minimum_score=.82, minimum_source_margin=.08):
    """Pure matching: returns a relative, source-registered display transform."""
    height=float(plot_rect[3])
    if not (height >= 200 and len(traces)==2):
        return SumMagAxis(False,reason="Invalid plot or TF pair")
    # Smaart displays optional fractional-octave-smoothed traces. Raw TRF
    # must never be compared to a smoothed native line as if identical.
    # Sample only colors actually present in the Magnitude image.
    x,y,w,h=map(int,plot_rect)
    l,t,_,_=map(int,window_rect)
    frame=NativeMagFrame(image,plot_rect,window_rect)
    palette=("magenta","gold","cyan","blue","red")
    colors=frame.visible_colors(palette)
    if not colors:
        return SumMagAxis(False,reason="No recognized native MAG trace pixels")
    candidates=[]
    for index,trace in enumerate(traces):
        f=np.asarray(trace.hz,float)
        raw_db=20*np.log10(np.maximum(np.abs(trace.h),1e-15))
        best_source=None
        # The common 1/6-Oct Smaart setting is checked first. A confident
        # fit is verified across both source identities before acceptance.
        for width in (1/6,0.,1/12,1/3):
            db=smooth_log_octaves(f,raw_db,width) if width else raw_db
            for color in colors:
                fit=fit_native_mag(image,plot_rect,window_rect,
                                   f,db,trace.coherence,trace_color=color,
                                   frame=frame)
                if not fit.accepted or fit.score<minimum_score:
                    continue
                if not (np.isfinite(fit.center_px) and
                        np.isfinite(fit.px_per_db) and fit.px_per_db>0):
                    continue
                y_max=float(fit.source_median_db+fit.center_px/fit.px_per_db)
                y_min=float(y_max-height/fit.px_per_db)
                if not (np.isfinite(y_min) and np.isfinite(y_max) and
                        8.<y_max-y_min<150.):
                    continue
                candidate=(fit.score,index,color,fit,y_min,y_max,width)
                if best_source is None or candidate[0]>best_source[0]:
                    best_source=candidate
            if best_source is not None and best_source[0]>=.98:
                break
        if best_source is not None:
            candidates.append(best_source)
    if not candidates:
        return SumMagAxis(False,reason="No verified native MAG source match")
    candidates.sort(key=lambda a:a[0],reverse=True)
    if (len(candidates)>1 and
        candidates[0][0]-candidates[1][0]<minimum_source_margin):
        return SumMagAxis(False,reason="Ambiguous native trace identity")
    score,index,color,fit,lo,hi,width=candidates[0]
    return SumMagAxis(True,lo,hi,float(score),index,color,
                      f"Verified native TF pixels, smoothing={width:g} Oct",
                      fit.bins)

def _quick_independent_source_axis(image,plot_rect,window_rect,traces):
    """Common 1/6-Oct proof against visible native source colors only.

    This is a fast positive-only probe. All its accepted points still pass
    fit_native_mag's full score/margin/three-band requirements. If ambiguous,
    the original exhaustive source matcher must decide (fail-closed).
    """
    x,y,w,h=map(int,plot_rect)
    l,t,_,_=map(int,window_rect)
    frame=NativeMagFrame(image,plot_rect,window_rect)
    colors=frame.visible_colors(("magenta","gold","cyan","blue","red"))
    if len(traces)!=2 or not colors:
        return None
    options=[]
    for index,trace in enumerate(traces):
        hz=np.asarray(trace.hz,float)
        raw=20*np.log10(np.maximum(np.abs(trace.h),1e-15))
        db=smooth_log_octaves(hz,raw,1/6)
        for color in colors:
            proof=fit_native_mag(image,plot_rect,window_rect,hz,db,
                                 trace.coherence,trace_color=color,
                                 frame=frame)
            if proof.accepted and proof.score>=.98 and np.isfinite(proof.px_per_db) and proof.px_per_db>0:
                # Only the best observed color per unique source may claim
                # native identity; no virtual second source inferred.
                options.append((float(proof.score),index,color,proof))
    if not options:
        return None
    distinct=[]
    for item in sorted(options,key=lambda v:v[0],reverse=True):
        if all(other[1]!=item[1] for other in distinct):
            distinct.append(item)
    if len(distinct)>1 and distinct[0][0]-distinct[1][0]<.08:
        return None
    score,index,color,fit=distinct[0]
    ymax=float(fit.source_median_db+fit.center_px/fit.px_per_db)
    ymin=float(ymax-float(h)/fit.px_per_db)
    if not(np.isfinite(ymin) and np.isfinite(ymax) and 8.<ymax-ymin<150.):
        return None
    return SumMagAxis(True,ymin,ymax,score,index,color,
                      "Native 1/6 Oct source identity independently verified",
                      fit.bins)



def _smaart8_native_source_axis(image,plot_rect,window_rect,traces):
    """Independently verify visible TRF identity and actual 10–10k/20–20k X.

    Native source matched to SAME screenshot; no predicted or synthetic
    SUM normalization is authorized by this read-only helper.
    """
    from smaart8_native_xaxis_v8172 import select_smaart8_native_axis
    if len(traces)!=2:
        return SumMagAxis(False,reason="Smaart8 requires exactly two TRFs")
    successes=[]
    for index,trace in enumerate(traces):
        hz=np.asarray(trace.hz,float)
        raw=20*np.log10(np.maximum(np.abs(trace.h),1e-15))
        accepted=[]
        for smooth in (0.,1/6,1/12,1/3):
            db=smooth_log_octaves(hz,raw,smooth) if smooth else raw
            choice=select_smaart8_native_axis(
                image,plot_rect,window_rect,hz,db,trace.coherence)
            if choice is None:
                continue
            fit=choice.colorfit.fit
            if (not fit.accepted or fit.score<.82 or fit.px_per_db<=0
                or not np.isfinite(fit.center_px)):
                continue
            height=float(plot_rect[3])
            y_max=float(fit.source_median_db+fit.center_px/fit.px_per_db)
            y_min=float(y_max-height/fit.px_per_db)
            if not(np.isfinite(y_min) and np.isfinite(y_max)
                   and 8.<y_max-y_min<150.):
                continue
            accepted.append((fit.score,index,choice.colorfit.color,
                             y_min,y_max,fit.bins,choice.xmin,choice.xmax,smooth))
            if fit.score>=.98:break
        if accepted:
            accepted.sort(reverse=True)
            successes.append(accepted[0])
    if not successes:
        return SumMagAxis(False,reason="Smaart8 native X/source pixel fit missing")
    successes.sort(reverse=True)
    if len(successes)>1 and successes[0][0]-successes[1][0]<.08:
        return SumMagAxis(False,reason="Smaart8 ambiguous two-trace native identity")
    score,index,color,lo,hi,bins,xmin,xmax,width=successes[0]
    return SumMagAxis(True,lo,hi,score,index,color,
                 f"Smaart8 independently verified X={xmin:g}..{xmax:g}Hz smoothing={width:g}",
                 bins,xmin,xmax)

def capture_sum_mag_axis(hwnd,mag_rect,traces):
    image,window_rect=capture_native_window(hwnd)
    # Primary: Smaart's own horizontal 0 dB baseline and native dB grid.
    # This avoids trace-color/smoothing/coherence mismatches and works when
    # the source curve is partly offscreen. Still strictly fail-closed.
    interval=saved_mag_grid_interval()
    grid=fit_native_mag_grid(image,mag_rect,window_rect,interval)
    from smaart8_api3_readonly_v868 import process_smaart_major
    if process_smaart_major(hwnd)==8:
        # The Smaart8 native TF window can span 10–10k, NOT the 20–20k
        # assumed in the old SUM Mag matcher (and model overlay).
        # Some responsive Smaart 8 layouts report the whole plot role box,
        # including its left/right axis gutters.  Source X registration must
        # use the inner raster.  Keep the original first, then test only small
        # symmetric gutter insets and require the same strict trace match.
        source=None
        source_rect=None
        for candidate in smaart8_raster_candidates(mag_rect):
            fit=_smaart8_native_source_axis(image,candidate,window_rect,traces)
            if fit.accepted:
                source=fit
                source_rect=candidate
                break
        if source is None:
            return fit
        if source_rect!=mag_rect:
            grid=fit_native_mag_grid(image,source_rect,window_rect,interval)
        if grid.accepted:
            span=source.y_max-source.y_min
            measured=float(source_rect[3])/span
            if (grid.px_per_db<=0 or
                 abs(measured-grid.px_per_db)/grid.px_per_db>.12):
                return SumMagAxis(False,reason="Smaart8 source/grid Y scales conflict")
            # Native 0-dB baseline takes precedence over per-trace offsets.
            return SumMagAxis(True,grid.y_min,grid.y_max,
                              min(grid.confidence,source.score),-1,
                              "GRID", "Smaart8 native X + trace and grid Y corroborated",
                              source.bins,source.x_min,source.x_max)
        # Native grid unavailable: use source-registered Y only if the
        # original Smaart trace matches unambiguously; never center SUM.
        return source
    if grid.accepted:
        return SumMagAxis(True,grid.y_min,grid.y_max,grid.confidence,
                          -1,"GRID",grid.reason,0)
    # A saved Smaart XML can mark ALL MAG plots invisible, while the current
    # unsaved live workspace still draws a well-defined 0 dB native lattice.
    # In that case the stored 3 dB interval is NOT sufficient alone. Require
    # a strong source-identity native fit whose slope independently proves
    # the native grid pixel pitch. The source's arbitrary dB offset affects
    # only its center, never its pixels/dB. Prefer the TRUE zero baseline
    # rather than treating one offset source as the absolute Y origin.
    source=None
    if interval is None:
        candidate_step=saved_mag_grid_interval(allow_inactive_consensus=True)
        if candidate_step is not None:
            candidate=fit_native_mag_grid(image,mag_rect,window_rect,
                                          candidate_step)
            if candidate.accepted:
                # The common live 1/6-Oct source can prove the pixel slope
                # without expensive 4x smoothing / 7x color brute force.
                # A negative/ambiguous quick proof falls back to the original
                # robust exhaustive matcher, never silently PASS.
                source=_quick_independent_source_axis(
                    image,mag_rect,window_rect,traces)
                if source is None:
                    source=axis_from_native_image(
                        image,mag_rect,window_rect,traces)
                span=float(source.y_max)-float(source.y_min)
                if source.accepted and source.source_index>=0 and span>0:
                    source_scale=float(mag_rect[3])/span
                    agreement=abs(source_scale-candidate.px_per_db)/candidate.px_per_db
                    if agreement<=.08:
                        return SumMagAxis(
                            True,candidate.y_min,candidate.y_max,
                            min(candidate.confidence,source.score),
                            -1,"GRID",
                            "Native 0 dB grid corroborated by independent "
                            "source pixels/dB and stored grid consensus",source.bins)
                # Native baseline contradicts the stored candidate or the
                # trace can't be independently verified. FAIL CLOSED.
                return SumMagAxis(False,reason=
                                 "Native grid/source dB scale not corroborated")
    # Legacy non-grid themes retain strict source-relative fitting; caller
    # must still independently verify each source level and identity.
    if source is None:
        source=axis_from_native_image(image,mag_rect,window_rect,traces)
    return source
