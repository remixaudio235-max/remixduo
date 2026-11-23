"""Read an icon within its UIA-correlated native Data Bar row.

The UIA row index + index.xml identify which TRF the glyph belongs to;
the pixel search only recovers minor x/y offsets caused by Win32 DPI
virtualization and Smaart Suite theme/layout differences.

Never infer ON from plotted curves, cached state, text, or an unknown icon.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from selection_v7 import scan_icon_white_cross


def classify_uia_row_gutter(image, row_y:int, expected_x:int,
                            row_pitch:int=22)->str:
    """Return 'on'/'off' only for a single, intact colored file glyph.

    All coordinates are PrintWindow *image-relative* pixels. The ROI is
    bounded to the first ~70px of the host, near the provided UIA icon x
    and to this row's height. No global Data Bar image search.
    """
    if image is None or not hasattr(image, "size"):
        return "unknown"
    width,height=image.size
    if not (0 <= row_y < height and 0 <= expected_x < width):
        return "unknown"
    # Scale is derived from native UIA row pitch, not screen resolution.
    # Old 74px x and 30px y clamps crop 175-200% DPI glyphs.
    if not 12 <= row_pitch <= 100:
        return "unknown"
    scale=max(.60,min(3.0,float(row_pitch)/22.))
    lo=max(0,int(round(expected_x-22*scale)))
    hi=min(width,int(round(expected_x+26*scale)),
           int(round(100*scale)))
    top=max(0,int(round(row_y-2*scale)))
    bottom=min(height,int(round(row_y+max(18*scale,row_pitch))))
    if hi-lo<max(8,int(round(12*scale))) or bottom-top<max(8,int(round(12*scale))):
        return "unknown"
    rgba=np.asarray(image.crop((lo,top,hi,bottom)).convert("RGB"),
                    dtype=np.int16)
    mx=rgba.max(axis=2);mn=rgba.min(axis=2)
    colorful=((mx-mn)>32)&(mx>60)
    # A colored selected-row BACKGROUND occupying the gutter does not
    # establish which pixels are a document icon; fail closed.
    if colorful.mean()>.8:
        return "unknown"
    visible=np.flatnonzero(colorful.sum(axis=0)>=max(5,int(.30*(bottom-top))))
    groups=[]
    if len(visible):
        start=prev=int(visible[0])
        for v in visible[1:]:
            v=int(v)
            if v>prev+1:
                groups.append((start,prev+1))
                start=v
            prev=v
        groups.append((start,prev+1))
    found=[]
    for start,end in groups:
        if not 10*scale <= end-start <= 23*scale:
            continue
        native_x0=lo+start
        native_x1=lo+end
        ys=np.flatnonzero(colorful[:,start:end].sum(axis=1)>=max(5,(end-start)//3))
        if not len(ys):
            continue
        y0=top+int(ys[0])
        y1=top+int(ys[-1])+1
        if not 12*scale <= y1-y0 <= 25*scale:
            continue
        # Include the entire colored glyph; clipping its X can turn OFF
        # into a false ON. Padding 1px is deliberately bounded to this row.
        pad=max(1,int(round(scale)))
        rect=(max(0,native_x0-pad),max(0,y0-pad),
              min(width,native_x1+pad),min(height,y1+pad))
        state=scan_icon_white_cross(image,rect)
        if state in ("on","off"):
            found.append((native_x0,native_x1,state))
    # If a highlighted row or a low-saturation/anti-aliased icon defeated
    # connected-component detection, normalize bounded crops to one physical
    # glyph size. Search only INSIDE the correlated UIA row, never globally.
    # Do not trust a plain colored selection background: a native document
    # icon has both a saturated lower-left BODY and a white folded corner.
    if len(found)==1:
        return found[0][2]
    if len(found)>1:
        return "unknown"
    width_native=max(10,int(round(14*scale)))
    height_native=max(12,int(round(18*scale)))
    candidates=[]
    for delta in (-10,-8,-6,-4,-2,0,2,4):
        x0=int(round(expected_x+delta*scale))
        for dy in (1,2,3):
            y0=int(round(row_y+dy*scale))
            if (x0<0 or y0<0 or x0+width_native>width or
                    y0+height_native>height or
                    y0+height_native>row_y+row_pitch+max(1,round(scale))):
                continue
            sample=image.crop((x0,y0,x0+width_native,y0+height_native))
            canonical=np.asarray(sample.resize((14,18),Image.Resampling.BICUBIC).convert("RGB"),
                                 dtype=np.int16)
            mx=canonical.max(axis=2);mn=canonical.min(axis=2)
            body=((mx-mn)>12)&(mx>35)
            # Dim/desaturated Smaart trace file: its folded page corner
            # may be 135-165 (not near-white), especially at 150% DPI.
            # Keep the body+fold proof and the independent white-X
            # classifier; no fold or ambiguous interior -> UNKNOWN.
            corner=(mn[:6,10:]>130)&((mx-mn)[:6,10:]<55)
            # Folded page: white triangle in upper right and colored body
            # in lower left. Both must exist in the same glyph candidate.
            if (float(body[8:16,1:6].mean())<.50 or
                int(corner.sum())<1 or float(body.mean())>.93):
                continue
            state=scan_icon_white_cross(sample.resize((14,18),Image.Resampling.BICUBIC),
                                        (0,0,14,18))
            if state in ("on","off"):
                candidates.append((delta,dy,state))
    states={x[2] for x in candidates}
    if len(states)!=1:
        return "unknown"
    distinct_x=len({x[0] for x in candidates})
    distinct_y=len({x[1] for x in candidates})
    # A desaturated OFF document with a small bright white X can expose
    # only two valid anti-aliased crops under NEAREST at fractional DPI.
    # Permit a 2-crop OFF proof at different y offsets, but keep ON
    # stricter (3 crops at >=2 x offsets). Never infer a state from 1 crop.
    off_cross_proof=(states=={"off"} and len(candidates)>=2 and distinct_y>=2)
    normal_proof=(len(candidates)>=3 and distinct_x>=2)
    if not (off_cross_proof or normal_proof):
        return "unknown"
    return candidates[0][2]
