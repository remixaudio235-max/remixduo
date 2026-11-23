# -*- coding: utf-8 -*-
"""Find Smaart native MAG by matching its visible heading, not plot order.

Template glyph masks were collected from user-controlled Smaart 9.6.4;
they do NOT OCR protected program text or alter Smaart state.
Unknown changed UI/DPI/layout fails closed.
"""
from pathlib import Path
import numpy as np
TITLE=Path(__file__).resolve().parent/"smaart_title_signatures_v03.npz"

def _signature(image,rect,window_rect):
    x,y,w,h=map(int,rect)
    l,t,r,b=map(int,window_rect)
    if not(x>=l and y>=t and x+110<=r and y+24<=b):return None
    a=np.asarray(image.crop((x-l,y-t,x-l+110,y-t+24)).convert("RGB"),dtype=np.uint8)
    mn=a.min(axis=2).astype(np.int16);mx=a.max(axis=2).astype(np.int16)
    # The original MAG/PHASE signatures are binary glyph shapes collected
    # on dark Smaart Suite. Their *shape* is invariant, but glyph polarity
    # reverses on Suite light theme (dark ink on near-white background).
    # Detect polarity only from the local ORIGINAL native header pixels.
    # This does NOT relax the independent score/margin proof in the caller.
    background=float(np.median(mn))
    neutral=(mx-mn)
    if background>=175.:
        return (mx<135)&(neutral<65)
    if background<=125.:
        return (mn>128)&(neutral<50)  # exact legacy dark contract
    return np.zeros(mn.shape,dtype=bool)  # unknown theme: HOLD

def _f1(a,b):
    count=int(a.sum())+int(b.sum())
    return 2*float(np.logical_and(a,b).sum())/count if count else 0.0

def detect_magnitude_rect(original_image,window_rect,positions,
                          *,signatures=TITLE):
    """Return (rectangle, mag_confidence) only when MAG != PHASE unambiguous."""
    if len(positions)!=2:return None
    with np.load(signatures,allow_pickle=False) as item:
        ref_mag=item["mag"].astype(bool)
        ref_phase=item["phase"].astype(bool)
    records=[]
    for rect in positions:
        sig=_signature(original_image,rect,window_rect)
        if sig is None:return None
        records.append((rect,_f1(sig,ref_mag),_f1(sig,ref_phase)))
    good=[x for x in records if x[1]>=.76 and x[1]-x[2]>=.25]
    others=[x for x in records if x[2]>=.70 and x[2]-x[1]>=.18]
    if len(good)!=1 or len(others)!=1 or good[0][0]==others[0][0]:return None
    return (tuple(good[0][0]),float(good[0][1]))
