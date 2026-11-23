"""Smaart 8 native TF-safe right sidebar placement.

Smaart 8's Transfer Function controls occupy upper right panel while
Generator/bottom controls occupy lower right. RemiX Duo must stay in the
unused center segment, never cover native TF controls or plot canvases.

Values reflect a 100%-DPI Smaart 8 desktop and use fail-closed bounds for
smaller viewports; this is NOT an API-reported geometry.
"""
from __future__ import annotations

def safe_v8_panel(host,screen,*,lane_width=162):
    """Return (x,y,w,h) safe secondary panel or None if no safe slot."""
    l,t,r,b=map(int,host)
    sl,st,sr,sb=map(int,screen)
    width,height=r-l,b-t
    if width<1000 or height<590 or r>sr+5 or b>sb+45 or l<sl-5:
        return None
    # Rightmost 162 px is the Smaart 8 native control lane on desktop.
    # Do not intrude into chart x<r-173 or cover the TF panel at y<300.
    lane_x=r-lane_width-7
    x=max(lane_x,sl+3)
    w=min(lane_width,sr-x-3,r-x-3)
    if w<148 or x<r-173:
        return None
    # TF native controls typically end by 299 px below title top;
    # Smaart 8 Generator controls begin ~700 px below top on 900px host.
    # Keep >=10px guard on both ends, and never cross host footer.
    top=max(t+310,st+4)
    bottom=min(b-204,sb-5)
    available=bottom-top
    if available<104:return None
    return (int(x),int(top),int(w),int(min(388,available)))
