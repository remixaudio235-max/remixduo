# -*- coding: utf-8 -*-
"""MagEq V13: source-backed PEQ markers + correction gradients on SUM Mag plot.

No extra QWidget. Uses the SAME native Smaart REF fit and MagEq source.
Pure geometry preparation is separated from Qt painting for regression QA.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from functools import lru_cache
from io import BytesIO
import numpy as np
from PyQt6.QtCore import Qt,QPointF,QRectF
from PyQt6.QtGui import (QColor,QBrush,QFont,QFontMetrics,QPainterPath,
                         QPen,QLinearGradient,QImage)
from smaart_native_mag_fit import native_points

BOOST="#4BE6CB"
CUT="#BA89FF"
MARKER="#FFCC6E"
MAGEQ_LINE="#FFE45C"
MAGEQ_LINE_WIDTH=4.2
MAGEQ_HALO_WIDTH=7.0
@dataclass(frozen=True)
class PEQMarker:
    number:int
    frequency:float
    gain:float
    q:float
    x:float
    y:float
    visible:bool
    reliable:bool

@dataclass(frozen=True)
class CorrectionSpan:
    indices:tuple[int,...]
    boost:bool

@dataclass(frozen=True)
class MagEqGeometry:
    after:np.ndarray
    original:np.ndarray
    reliable:np.ndarray
    spans:tuple[CorrectionSpan,...]
    markers:tuple[PEQMarker,...]
    rect:tuple[int,int,int,int]
    source_revision:int

def build_geometry(source,frame):
    """Ground every pixel in current native TF fit; no fabricated axis."""
    x,y,w,h=frame.plot
    if frame.revision!=source.revision or not frame.fit.accepted:
        raise ValueError("MagEq revision/viewport untrusted")
    from tf_display_smoothing import smooth_log_octaves
    width=float(getattr(source,"display_smooth_oct",0.) or 0.)
    after_db=(smooth_log_octaves(source.freqs,source.after_db,width)
              if width else source.after_db)
    original_db=(smooth_log_octaves(source.freqs,source.original_db,width)
                 if width else source.original_db)
    axis={"expect_x_min":getattr(frame,"x_min",20.),
          "expect_x_max":getattr(frame,"x_max",20000.)}
    after,quality=native_points(frame.plot,frame.fit,
                  source.freqs,after_db,source.coh,**axis)
    original,q2=native_points(frame.plot,frame.fit,
                  source.freqs,original_db,source.coh,**axis)
    if (len(after)<2 or len(after)!=len(original) or
         not np.array_equal(quality,q2) or
         not np.allclose(after[:,0],original[:,0],atol=.001)):
        raise ValueError("Original/MagEq native X geometry mismatch")
    # Convert to local QWidget coordinates once, without mutating source.
    a=after.copy()
    b=original.copy()
    a[:,0]-=x;a[:,1]-=y;b[:,0]-=x;b[:,1]-=y
    reliable=np.asarray(quality,bool)
    finite=np.isfinite(a).all(axis=1)&np.isfinite(b).all(axis=1)
    in_clip=((a[:,1]>=-12)&(a[:,1]<=h+12)&
             (b[:,1]>=-12)&(b[:,1]<=h+12)&
             (a[:,0]>=0)&(a[:,0]<=w))
    mask=reliable&finite&in_clip
    delta=b[:,1]-a[:,1]  # boost -> after above original -> delta positive
    signs=np.where(delta>.18,1,np.where(delta<-.18,-1,0))
    spans=[]
    active=[];direction=0
    def flush():
        nonlocal active,direction
        if len(active)>=2:spans.append(CorrectionSpan(tuple(active),direction>0))
        active=[];direction=0
    max_gap=max(12.,w/55.)
    for i in range(len(a)):
        good=bool(mask[i] and signs[i])
        if not good:
            flush()
            continue
        sign=int(signs[i])
        if active and (sign!=direction or a[i,0]-a[active[-1],0]>max_gap):
            flush()
        if not active:direction=sign
        active.append(i)
    flush()
    markers=[]
    logs=np.log(np.asarray(source.freqs,float))
    for i,band in enumerate(source.peqs,1):
        fc=float(band.f_hz)
        gain=float(band.gain_db)
        q=float(band.q)
        if not (np.isfinite([fc,gain,q]).all() and fc>0):
            markers.append(PEQMarker(i,fc,gain,q,float("nan"),
                                    float("nan"),False,False))
            continue
        px=w*math.log(fc/20.)/math.log(1000.)
        # Exact predicted MagEq at Fc; not a cursor snapped to source bins.
        mag=float(np.interp(math.log(fc),logs,source.after_db))
        py=float(frame.fit.y(mag))
        idx=int(np.argmin(np.abs(logs-math.log(fc))))
        reliable_fc=bool(source.coh[idx]>=.60)
        visible=bool(3<=px<=w-3 and 8<=py<=h-8 and 20<=fc<=20000)
        markers.append(PEQMarker(i,fc,gain,q,px,py,visible,reliable_fc))
    return MagEqGeometry(a,b,reliable,tuple(spans),tuple(markers),
                         tuple(frame.plot),int(source.revision))

def draw_gradient(painter,geo):
    """V8.67 Amber Glass: correction-aware, contour-following soft fill.

    Every ribbon is interpolated between the ACTUAL pixel geometries of the
    native Mag and MagEQ traces. Unlike a screen-vertical QLinearGradient,
    opacity stays attached to the MagEQ line even as both traces bend.
    Trusted spans and the user's native viewport are never extended.
    This renders only; no DSP/PEQ calculation or state mutation.
    """
    if not geo.spans:
        return 0
    painter.save()
    painted=0
    painter.setPen(Qt.PenStyle.NoPen)
    # Closest ribbon is brightest. Lower alpha approaches the original trace.
    # Four contour ribbons keep the accepted soft amber falloff while
    # reducing cold-frame QPainter path/fill work by 20% on release hardware.
    alphas=(67,40,20,6)
    ribbons=len(alphas)
    for span in geo.spans:
        ix=np.asarray(span.indices,dtype=int)
        eq=geo.after[ix]
        original=geo.original[ix]
        if len(eq)<2:
            continue
        # Avoid redundant subpixel path vertices in the high-density log axis.
        xs=eq[:,0]
        grid=np.arange(xs[0],xs[-1],5.0)
        selected=np.unique(np.r_[0,np.searchsorted(xs,grid),len(eq)-1])
        selected=np.clip(selected,0,len(eq)-1)
        eq=eq[selected]
        original=original[selected]
        if len(eq)<2:
            continue
        delta=original-eq
        distance=np.abs(delta[:,1])
        median_distance=float(np.median(distance))
        if median_distance<0.20:
            continue
        # Gentle adaptive contrast: subtle for minor correction, vivid for
        # larger differences; no hard color discontinuity at 0 dB.
        strength=max(.42,min(1.0,median_distance/23.0))
        rgb=(255,194,100) if span.boost else (250,169,104)
        # The contour-following ribbons approximate a feathered
        # gradient without QLinearGradient misalignment on curved traces.
        for band,opacity in enumerate(alphas):
            t0=band/ribbons
            t1=(band+1)/ribbons
            upper=eq+delta*t0
            lower=eq+delta*t1
            area=QPainterPath()
            area.moveTo(float(upper[0,0]),float(upper[0,1]))
            for xx,yy in upper[1:]:
                area.lineTo(float(xx),float(yy))
            for xx,yy in lower[::-1]:
                area.lineTo(float(xx),float(yy))
            area.closeSubpath()
            painter.fillPath(area,QColor(*rgb,round(opacity*strength)))
        # Underpaint a discreet illuminated edge; overlay's trusted amber
        # MagEQ stroke is drawn on top and keeps its established identity.
        edge=QPainterPath()
        edge.moveTo(float(eq[0,0]),float(eq[0,1]))
        for xx,yy in eq[1:]:
            edge.lineTo(float(xx),float(yy))
        painter.setPen(QPen(QColor(255,210,133,35),5.0,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painted+=1
    painter.restore()
    return painted


@lru_cache(maxsize=96)
def _raster_text(text,px,color):
    """Use Windows fonts directly: stable Vietnamese/number chips in offscreen Qt."""
    from PIL import Image,ImageDraw,ImageFont
    fontfile="C:/Windows/Fonts/arialbd.ttf"
    font=ImageFont.truetype(fontfile,int(px))
    bounds=font.getbbox(text)
    ww=max(1,bounds[2]-bounds[0]+2)
    hh=max(1,bounds[3]-bounds[1]+2)
    im=Image.new("RGBA",(ww,hh),(0,0,0,0))
    ImageDraw.Draw(im).text((1-bounds[0],1-bounds[1]),text,font=font,fill=color)
    stream=BytesIO()
    im.save(stream,format="PNG")
    return QImage.fromData(stream.getvalue(),"PNG")

def marker_hover_at(markers,x,y,*,max_dx=19.,max_dy=17.):
    """Nearest visible PEQ only, in local native Magnitude pixel coords.

    This is passive hit-testing from cursor position; no mouse input
    interception is ever enabled on the Smaart plot overlay.
    """
    chosen=None
    distance=float("inf")
    for marker in markers:
        if not marker.visible:
            continue
        dx=abs(float(x)-marker.x)
        dy=abs(float(y)-marker.y)
        if dx>max_dx or dy>max_dy:
            continue
        d=(dx/max_dx)**2+(dy/max_dy)**2
        if d<distance:
            chosen=marker.number
            distance=d
    return chosen


def draw_markers(painter,geo,*,hover_number=None):
    """Compact EQ1/EQ2 chips; only the hovered marker shows F/G/Q.

    The marker remains on the exact predicted MagEQ center, and at most
    one F/G/Q popup is rendered. Tooling and input remain click-through.
    """
    painter.save()
    _,_,w,h=geo.rect
    count=0
    selected=None
    for marker in geo.markers:
        if not marker.visible:
            continue
        x,y=marker.x,marker.y
        active=marker.number==hover_number
        base=QColor(MARKER if marker.reliable else "#9A927D")
        if active:
            glow=QColor(base)
            glow.setAlpha(60)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(x,y),18.,15.)
        # Small label only: no F/G/Q panel until explicit hover.
        tag=f"EQ{marker.number}"
        textimg=_raster_text(tag,10,(15,27,37,255))
        bw=float(max(28,textimg.width()+10))
        bh=float(max(18,textimg.height()+6))
        chip=QRectF(x-bw/2,y-bh/2,bw,bh)
        painter.setPen(QPen(QColor("#263747"),.8))
        painter.setBrush(base)
        painter.drawRoundedRect(chip,5.,5.)
        painter.drawImage(QPointF(chip.left()+(bw-textimg.width())/2,
                                  chip.top()+(bh-textimg.height())/2),textimg)
        count+=1
        if active:
            selected=marker
    labels=0
    if selected is not None:
        marker=selected
        f=(f"{marker.frequency:.0f} Hz" if marker.frequency<1000
           else f"{marker.frequency/1000:.2f} kHz")
        pretty=(f"EQ{marker.number}  |  F {f}  |  "
                f"G {marker.gain:+.1f} dB  |  Q {marker.q:g}")
        img=_raster_text(pretty,12,(255,236,205,255))
        chipw=float(min(w-8,img.width()+14))
        chiph=float(max(23,img.height()+10))
        # Favor above/right, clamp within Mag; never draw a stack of chips.
        candidates=((marker.x+20,marker.y-39),
                    (marker.x-chipw-20,marker.y-39),
                    (marker.x+20,marker.y+17),
                    (marker.x-chipw-20,marker.y+17))
        x0,y0=next(((xx,yy) for xx,yy in candidates
                     if 4<=xx<=w-chipw-4 and 4<=yy<=h-chiph-4),
                    (max(4,min(w-chipw-4,marker.x+20)),
                     max(4,min(h-chiph-4,marker.y-39))))
        rect=QRectF(float(x0),float(y0),chipw,chiph)
        painter.setBrush(QColor(19,38,54,243))
        painter.setPen(QPen(QColor("#E5AF55"),1.))
        painter.drawRoundedRect(rect,5.,5.)
        painter.drawImage(QPointF(rect.left()+7,
                                  rect.top()+(rect.height()-img.height())/2),img)
        labels=1
    painter.restore()
    return count,labels


def draw_mageq_details(painter,source,frame,geometry=None):
    geo=geometry or build_geometry(source,frame)
    painter.save()
    _,_,w,h=geo.rect
    painter.setClipRect(QRectF(0,0,w,h))
    count=draw_gradient(painter,geo)
    markers,labels=draw_markers(painter,geo)
    painter.restore()
    return {"gradient_spans":count,"markers":markers,"labels":labels,
            "peqs":len(source.peqs),"revision":source.revision}
