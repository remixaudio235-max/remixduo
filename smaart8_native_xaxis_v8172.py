"""V8.172 Smaart 8 native MAG X-axis selection from current pixels.

Only two opt-in, independently QA-proven Smaart8 axis geometries.
Every hypothesis uses the SAME freshly captured Smaart native image.
Ambiguous or unknown axis -> HOLD. Never reuses an old visual fit or
grants EQ export itself: the existing strict 3/3, HWND, Fs and frame
freshness checks remain the sole authorization.
"""
from dataclasses import dataclass
from smaart_native_mag_fit import NativeMagFrame,fit_native_mag
from smaart_eq_color_select import choose_color_fit,ColorFit

V8_AXIS_HYPOTHESES=((20.,20000.),(10.,10000.))
PALETTE=("cyan","teal","blue","red","green","magenta","gold")

@dataclass(frozen=True)
class AxisColorFit:
    xmin:float
    xmax:float
    colorfit:ColorFit

def select_smaart8_native_axis(native,mag,winrect,frequencies,db,coherence,
                              *,preferred_color=None):
    """Do not choose a different x-axis unless it strongly wins native pixels."""
    frame=NativeMagFrame(native,mag,winrect)
    if not frame.valid:return None
    visible=frame.visible_colors(PALETTE,minimum_pixels=250)
    if preferred_color is not None and preferred_color not in visible:
        return None
    candidates=[]
    for xmin,xmax in V8_AXIS_HYPOTHESES:
        if preferred_color:
            fit=fit_native_mag(native,mag,winrect,frequencies,db,coherence,
                trace_color=preferred_color,frame=frame,
                expect_x_min=xmin,expect_x_max=xmax)
            cf=ColorFit(preferred_color,fit,0.,bool(fit.accepted))
        else:
            cf=choose_color_fit(native,mag,winrect,frequencies,db,coherence,
                visible_colors=visible,frame=frame,
                expect_x_min=xmin,expect_x_max=xmax)
        if (cf is not None and cf.accepted and cf.fit.accepted and
                cf.fit.score>=.78 and cf.fit.bins>=55):
            candidates.append(AxisColorFit(xmin,xmax,cf))
    if not candidates:return None
    candidates.sort(key=lambda c:c.colorfit.fit.score,reverse=True)
    if len(candidates)>1 and (
       candidates[0].colorfit.fit.score-candidates[1].colorfit.fit.score<.12):
        return None
    return candidates[0]
