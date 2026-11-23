"""V8.114: measure Smaart's per-trace dB offset from native pixels (read-only).

Smaart keeps the trace "dB +/-" offset only in memory: it is not written to the
.trf and the API cannot read it back. The on-screen curve is the stored TF
shifted by that offset, so fitting the stored shape to the native pixels of
its colour, then mapping the fitted centre through the VERIFIED native dB axis
(the same axis SUM Mag is drawn on), gives offset = displayed - stored.

Fail closed: no fit, ambiguous colour, both traces on one colour, or a pixel
scale that disagrees with the verified axis -> offset None (caller keeps its
current value and shows the reason). Never guesses.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from smaart_eq_color_select import choose_color_fit
from smaart_native_mag_fit import NativeMagFrame
from tf_display_smoothing import SMOOTH_OPTIONS, smooth_log_octaves

SCALE_TOLERANCE=.10   # fitted px/dB vs verified axis px/dB


@dataclass(frozen=True)
class TraceOffset:
    offset_db:float|None
    color:str|None
    reason:str


def _clipped_grid_recovery(image,plot_rect,window_rect,traces,
                           y_min,y_max,smoothing_oct,frame,
                           visible_colors,results):
    """Use strict verified native 0-dB grid to recover an occluded TF.

    Zero dependence on a guessed Y viewport, stale frame or lowered legacy
    thresholds. Recover only missing sources and prove color + source
    distinctness. The native axis is rechecked on THIS screenshot.
    """
    if (len(traces)!=2 or smoothing_oct!=1/6 or not frame.valid or
            all(o.offset_db is not None for o in results)):
        return results
    from smaart_native_y_grid_v839 import (
        fit_native_mag_grid,saved_mag_grid_interval)
    from native_clipped_grid_v8165 import fit_clipped_grid
    step=saved_mag_grid_interval()
    if step is None:
        step=saved_mag_grid_interval(allow_inactive_consensus=True)
    if step is None:
        return results
    grid=fit_native_mag_grid(image,plot_rect,window_rect,step)
    if not grid.accepted or not np.isfinite(grid.px_per_db):
        return results
    h=float(plot_rect[3])
    scale=h/(float(y_max)-float(y_min))
    # The currently displayed SUM transform must be the independently
    # VERIFIED grid, not a relative transform fitted to a single source.
    if (abs(grid.y_min-y_min)>.30 or abs(grid.y_max-y_max)>.30 or
            abs(grid.px_per_db-scale)/scale>.08):
        return results
    claimed={o.color for o in results if o.offset_db is not None}
    remaining=[c for c in visible_colors if c not in claimed]
    if not remaining:
        return results
    smoothed=[]
    for trace in traces:
        db=20*np.log10(np.maximum(np.abs(np.asarray(trace.h)),1e-12))
        smoothed.append(smooth_log_octaves(trace.hz,db,smoothing_oct))
    for i,trace in enumerate(traces):
        if results[i].offset_db is not None:
            continue
        candidates=[]
        for color in remaining:
            proof=fit_clipped_grid(
                image,plot_rect,window_rect,trace.hz,smoothed[i],
                trace.coherence,y_min=grid.y_min,y_max=grid.y_max,
                color=color,frame=frame)
            # floating-point epsilon for a fitted sample exactly on 4% bound
            if proof.accepted and abs(proof.px_per_db-scale)/scale<=.0400001:
                candidates.append((proof.score,color,proof))
        candidates.sort(key=lambda item:item[0],reverse=True)
        if not candidates:
            continue
        if (len(candidates)>1 and
                candidates[0][0]-candidates[1][0]<.055):
            continue
        score,color,fit=candidates[0]
        # A second, distinct source must NOT also fit the same green/magenta
        # pixels within the native source identity margin of 0.08.
        other=1-i
        other_fit=fit_clipped_grid(
            image,plot_rect,window_rect,traces[other].hz,smoothed[other],
            traces[other].coherence,y_min=grid.y_min,y_max=grid.y_max,
            color=color,frame=frame)
        if other_fit.accepted and other_fit.score>=score-.08:
            continue
        display=float(grid.y_max)-fit.center_px/scale
        recovered=round(display-fit.source_median_db,1)
        if not np.isfinite(recovered):
            continue
        results[i]=TraceOffset(recovered,color,
                              "native GRID: clipped visible trace verified")
        claimed.add(color)
        remaining.remove(color)
    return results


def measure_trace_offsets(image,plot_rect,window_rect,traces,y_min,y_max,
                          *,smoothing_oct=0.):
    """Fit stored TF to native pixels with the VERIFIED live MAG smoothing.

    This smooths only display data for matching; raw complex TF is untouched.
    No guessed smoothing; unsupported values fail closed.
    """
    allowed={float(value) for _name,value in SMOOTH_OPTIONS}
    if smoothing_oct not in allowed:
        return [TraceOffset(None,None,"Smoothing Mag chưa xác minh")]*len(traces)
    h=float(plot_rect[3])
    span=float(y_max)-float(y_min)
    if not(np.isfinite(span) and span>0 and h>0):
        return [TraceOffset(None,None,"trục dB chưa xác minh")]*len(traces)
    axis_px_per_db=h/span
    # Compute visible colors ONCE per native frame, using the same exact
    # mask and >=250 pixel minimum as fit_native_mag. No trust relaxation.
    frame=NativeMagFrame(image,plot_rect,window_rect)
    palette=("cyan","teal","blue","red","green","magenta","gold")
    visible_colors=frame.visible_colors(palette)
    out=[]
    for trace in traces:
        db=20*np.log10(np.maximum(np.abs(np.asarray(trace.h)),1e-12))
        if smoothing_oct:
            db=smooth_log_octaves(trace.hz,db,smoothing_oct)
        choice=choose_color_fit(image,plot_rect,window_rect,trace.hz,db,
                                trace.coherence,visible_colors=visible_colors,
                                frame=frame)
        if choice is None:
            out.append(TraceOffset(None,None,"không thấy đường Trace trên Smaart"))
            continue
        if not choice.accepted:
            out.append(TraceOffset(None,choice.color,"màu Trace không rõ ràng"))
            continue
        fit=choice.fit
        if abs(fit.px_per_db-axis_px_per_db)/axis_px_per_db>SCALE_TOLERANCE:
            out.append(TraceOffset(None,choice.color,"tỉ lệ dB không khớp trục"))
            continue
        displayed=float(y_max)-fit.center_px/axis_px_per_db
        out.append(TraceOffset(round(displayed-fit.source_median_db,1),
                               choice.color,"đo từ pixel Smaart"))
    # Recover an off-viewport native curve ONLY if this very screenshot
    # proves the 0 dB grid and exact current SUM Y axis. Legacy confident
    # matches are never replaced by the clipped matcher.
    if any(item.offset_db is None for item in out):
        out=_clipped_grid_recovery(image,plot_rect,window_rect,traces,
                                   y_min,y_max,smoothing_oct,frame,
                                   visible_colors,out)
    colors=[o.color for o in out if o.offset_db is not None]
    if len(colors)!=len(set(colors)):
        out=[TraceOffset(None,o.color,"hai Trace cùng màu — không phân biệt được")
             if o.offset_db is not None else o for o in out]
    return out
