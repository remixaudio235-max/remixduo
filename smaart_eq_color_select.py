"""Color-aware Smaart Mag REF match, with source identity fail-closed.

A blue, cyan, or red native TF can change with the active Smaart trace.
Only a strongly scored and unambiguous color fit can place the EQ curve.
"""
from dataclasses import dataclass
from smaart_native_mag_fit import fit_native_mag,NativeMagFit

@dataclass(frozen=True)
class ColorFit:
    color:str
    fit:NativeMagFit
    second_score:float
    accepted:bool

def choose_color_fit(image,plot_rect,window_rect,frequencies,source_db,coherence,
                     *,minimum_margin=.055,hint=None,visible_colors=None,
                     frame=None,expect_x_min=20.,expect_x_max=20000.):
    # V8.130: the trace's own Data Bar colour identifies it; if its curve
    # fits, trust that identity instead of guessing among named colours
    # (a pink trace tied "red" and "magenta"; slate blue matched none).
    def fitted(color):
        kw={"trace_color":color,"expect_x_min":expect_x_min,
            "expect_x_max":expect_x_max}
        if frame is not None: kw["frame"]=frame
        return fit_native_mag(image,plot_rect,window_rect,frequencies,
                              source_db,coherence,**kw)
    if hint:
        f=fitted(hint)
        if f.accepted:
            return ColorFit(hint,f,0.,True)
    candidates=[]
    # V8.163: a color with fewer than 250 native plot pixels is guaranteed
    # to fail inside fit_native_mag. The caller may prefilter such colors
    # once per screenshot to avoid repeated expensive fine matching.
    palette=("cyan","teal","blue","red","green","magenta","gold")
    candidate_colors=(palette if visible_colors is None else
                      tuple(c for c in palette if c in visible_colors))
    for color in candidate_colors:
        f=fitted(color)
        if f.accepted:
            candidates.append((f.score,color,f))
    if not candidates:return None
    candidates.sort(key=lambda t:t[0],reverse=True)
    best,c,fit=candidates[0]
    nextscore=float(candidates[1][0]) if len(candidates)>1 else 0.
    if len(candidates)>1 and best-nextscore<minimum_margin:
        return ColorFit(c,fit,nextscore,False)
    return ColorFit(c,fit,nextscore,True)
