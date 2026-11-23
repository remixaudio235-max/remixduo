"""V8.122: 3-tier automatic dock layout when Smaart has many TF engines.

User-approved 2026-11-12 (free height = space below the LAST TF engine box):
  1. >= 400 px  -> "dock":    dock below the last engine (V8.120 behaviour);
  2. 200..400   -> "compact": same place, compact Auto Phase page
                              (button, 2 trace rows, Top 3 on one row);
  3. < 200 px   -> "overlap": dock may cover engines 2..N, starting right
                              after TF engine 1 ("bắt đầu từ sau TF 1").

Engine boxes are found from pixels on both editions (Smaart 8 has no UIA
tree; Smaart 9/Suite UIA exposes no engine-box rectangles): each engine is
a block with a saturated coloured border line at its top and bottom
(Smaart 8: 2 px, Suite: 1 px), stacked with ~6-8 px gaps. Pure numpy/PIL,
no native OS imports, read-only.
"""
from __future__ import annotations
from dataclasses import dataclass

TIER_DOCK_MIN=400
TIER_COMPACT_MIN=200
# Full Auto Phase page (400) + dock heading bar (24). Below this the dock
# switches its Auto Phase page to the compact layout instead of cutting Top 3.
FULL_PAGE_H=424


def choose_dock_tier(free_h)->str:
    if free_h>=TIER_DOCK_MIN:
        return "dock"
    if free_h>=TIER_COMPACT_MIN:
        return "compact"
    return "overlap"


@dataclass(frozen=True)
class EngineBox:
    """Rows are image coordinates (inclusive border rows)."""
    top:int
    bottom:int
    color:tuple


def _border_lines(arr):
    import numpy as np
    sat=(arr.max(axis=2)-arr.min(axis=2))>60
    cov=sat.mean(axis=1)
    lines=[]
    for i in np.flatnonzero(cov>=0.6):
        color=arr[i][sat[i]].mean(axis=0)
        if (lines and i==lines[-1][1]+1 and
                np.abs(color-lines[-1][2]).max()<60):
            lines[-1][1]=int(i)
        else:
            lines.append([int(i),int(i),color])
    return lines


def detect_engine_boxes(image,x0,x1,y0,y1,scale=1.0):
    """Coloured-border engine boxes in image columns x0..x1, rows y0..y1.

    A box = a top border line and the next border line of the same colour,
    36..90 px (x scale) apart. Returns boxes in image row coordinates.
    """
    import numpy as np
    arr=np.asarray(image.convert("RGB"),dtype=np.int16)
    h,w=arr.shape[:2]
    x0,x1=max(0,int(x0)),min(w,int(x1))
    y0,y1=max(0,int(y0)),min(h,int(y1))
    if x1-x0<40 or y1-y0<30:
        return []
    lines=_border_lines(arr[y0:y1,x0:x1])
    min_h,max_h=36*scale,90*scale
    boxes=[];i=0
    while i<len(lines)-1:
        top,bottom=lines[i],lines[i+1]
        height=bottom[1]-top[0]+1
        if (min_h<=height<=max_h and
                np.abs(top[2]-bottom[2]).max()<80):
            boxes.append(EngineBox(y0+top[0],y0+bottom[1],
                                   tuple(int(c) for c in top[2])))
            i+=2
        else:
            i+=1
    return boxes


def leading_chain(boxes,max_gap):
    """First box plus each following box that starts <= max_gap below."""
    chain=[]
    for box in boxes:
        if chain and box.top-chain[-1].bottom-1>max_gap:
            break
        chain.append(box)
    return chain


def trailing_chain(boxes,end_y,max_gap):
    """Boxes stacked directly above end_y (e.g. Suite "+ TF Engine")."""
    chain=[]
    limit=end_y
    for box in reversed(boxes):
        if box.bottom>=limit or limit-box.bottom-1>max_gap:
            if chain:
                break
            continue
        chain.insert(0,box)
        limit=box.top
    return chain
