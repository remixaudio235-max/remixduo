# -*- coding: utf-8 -*-
"""AutoEQ -> actual Smaart MAG plot, click-through in the same Qt process.

V0.6 independent QA copy. Only a high-confidence native pixel registration
allows the corrected Mag preview to be painted. No Smaart API writes, no audio.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass,replace
import os,time
from pathlib import Path
import numpy as np
import win32gui,win32con,win32process
from PyQt6.QtCore import Qt,QTimer,QPointF,QRectF
from PyQt6.QtGui import QPainter,QPen,QColor,QPainterPath,QFont
from PyQt6.QtWidgets import QWidget,QApplication
from plot_role_v812 import locate_role_plots
from smaart_mag_plot_detector import detect_magnitude_rect
from smaart_native_mag_fit import capture_native_window,native_points,NativeMagFit,fit_native_mag,trace_color_mask,expand
from smaart_native_y_grid_v839 import fit_native_mag_grid,saved_mag_grid_interval,saved_mag_grid_interval_major
from smaart_eq_color_select import choose_color_fit,ColorFit
from tf_display_smoothing import smooth_log_octaves
from autoeq_core import cascade_biquads
from mageq_trace_v07 import create_mageq_trace
from worker_lifecycle_v8142 import bounded_shutdown

@dataclass(frozen=True)
class MagSource:
    revision:int
    source_index:int
    freqs:np.ndarray
    original_db:np.ndarray
    after_db:np.ndarray
    coh:np.ndarray
    peqs:tuple
    source_name:str
    name:str
    source_identity:str
    fs:int
    display_smooth_oct:float=0.

@dataclass(frozen=True)
class FitFrame:
    revision:int
    plot:tuple[int,int,int,int]
    fit:object
    color:str
    created:float
    hwnd:int|None=None
    window_rect:tuple[int,int,int,int]|None=None
    source_identity:str|None=None
    identity_verified:bool=False
    grid_agrees:bool=False
    phase_plot:tuple[int,int,int,int]|None=None  # V8.53 cached role geometry
    x_min:float=20.
    x_max:float=20000.

# A pan/zoom changes native *pixels* without changing the HWND rectangle.
# Never reuse its Y transform for seconds after a native viewport mutation.
NATIVE_FRAME_MAX_AGE_S=.45

def frame_is_fresh_for_window(frame,hwnd,*,now=None,max_age_s=NATIVE_FRAME_MAX_AGE_S):
    """Reject a stale native fit after Smaart moves, resizes, or restarts."""
    if frame is None or frame.hwnd!=hwnd or frame.window_rect is None:
        return False
    if now is None:now=time.monotonic()
    age=now-frame.created
    if age<0 or age>max_age_s:return False
    try:
        return (win32gui.IsWindow(hwnd) and not win32gui.IsIconic(hwnd)
                and tuple(win32gui.GetWindowRect(hwnd))==frame.window_rect)
    except Exception:
        return False

# V8.106: one native verification measures ~0.3-0.4 s on a 1920x1040 Smaart
# window (PrintWindow 155 ms + Mag grid 134 ms + fit). With 90/120 ms ticks a
# frame often expired before its successor landed and the model curve
# blinked. DISPLAY ONLY (never export, drag or calculate): keep the last
# verified frame while a newer verification of the SAME unmoved window is in
# flight and the previous verification did not fail, up to this hard cap.
NATIVE_DISPLAY_GRACE_S=1.50

SEED_DROP_AFTER_FAILURES=3  # e.g. trace recolored in Smaart: rescan fully

def verified_smaart_host(hub):
    """Bound HWND for native MagEQ; never find a Smaart edition by title.

    Both Smaart 8 and Suite may run at once. An old frame must never
    paint/export against the other host just because it has foreground.
    """
    observer=getattr(getattr(hub,"engine",None),"observer",None)
    hwnd=int(getattr(observer,"hwnd",0) or 0)
    active=int(getattr(hub,"_last_hwnd",0) or 0)
    try:
        if (not hwnd or hwnd!=active or not win32gui.IsWindow(hwnd)
                or not win32gui.IsWindowVisible(hwnd)
                or win32gui.IsIconic(hwnd)):
            return 0
    except (OSError,ValueError,TypeError):
        return 0
    return hwnd

def verification_in_flight(owner):
    return (getattr(owner,"future",None) is not None and
            not getattr(owner,"_verify_failed",False))

def verification_recoverable(owner):
    """Display-only bridge across bounded native capture failures."""
    failures=int(getattr(owner,"_verify_failures",0))
    return bool(failures<SEED_DROP_AFTER_FAILURES and
                (getattr(owner,"future",None) is not None or failures>0))

def frame_presentable(frame,hwnd,*,verifying,now=None):
    kw={} if now is None else {"now":now}
    if frame_is_fresh_for_window(frame,hwnd,**kw):
        return True
    return bool(verifying) and frame_is_fresh_for_window(
        frame,hwnd,max_age_s=NATIVE_DISPLAY_GRACE_S,**kw)

def build_state(freq,h,coh,peqs,*,fs,source_index,source_name,revision,
                allow_bypass=False,display_smooth_oct=0.):
    """New immutable MagEq line, original Smaart TF is strictly read-only."""
    trace=create_mageq_trace(freq,h,coh,peqs,fs=fs,
             source_index=source_index,source_name=source_name,revision=revision,
             allow_bypass=allow_bypass)
    return MagSource(trace.revision,trace.source_index,trace.freq_hz,
                     trace.original_mag_db,trace.mageq_mag_db,
                     trace.coherence,trace.bands,trace.source_name,
                     trace.name,trace.source_identity,trace.fs,
                     float(display_smooth_oct or 0.))

def _display_db(source,values):
    width=float(getattr(source,"display_smooth_oct",0.) or 0.)
    return smooth_log_octaves(source.freqs,values,width) if width else values

def _fast_refit_same_source(native,mag,winrect,source,grid,prior):
    """Fast read-only MATCH against NEW native pixels from the SAME image.

    Prior verified source/Y is only a starting guess, never published
    without a fresh color, confidence and native grid measurement.
    """
    if (prior is None or not prior.identity_verified or
            prior.source_identity!=source.source_identity or
            prior.plot!=tuple(mag) or prior.window_rect!=tuple(winrect) or
            prior.color not in ("cyan","blue","red","green","magenta","gold") or
            not (grid.accepted and grid.confidence>=.90)):
        return None
    old=prior.fit
    if old.px_per_db<=0 or abs(old.px_per_db-grid.px_per_db)/grid.px_per_db>.08:
        return None
    x,y,w,h=map(int,mag)
    l,t,_,_=map(int,winrect)
    crop=native.crop((x-l,y-t,x-l+w,y-t+h))
    mask=trace_color_mask(crop,prior.color)
    if int(mask.sum())<250:return None
    hit=expand(mask,3)
    f=source.freqs
    db=_display_db(source,source.original_db)
    coh=source.coh
    xmin=float(getattr(prior,"x_min",20.))
    xmax=float(getattr(prior,"x_max",20000.))
    xx=np.rint(w*np.log(np.maximum(f,1e-10)/xmin)/np.log(xmax/xmin)).astype(int)
    # V8.135: coherence is reference-only; native trace continuity is
    # grounded by the visible Mag curve itself.
    valid=(f>=60)&(f<=1800)&(xx>46)&(xx<w-320)&np.isfinite(db)
    ids=np.flatnonzero(valid)
    if len(ids)<80:return None
    if len(ids)>240:
        ids=ids[np.rint(np.linspace(0,len(ids)-1,240)).astype(int)]
    xs=xx[ids]
    delta_db=db[ids]-old.source_median_db
    centers=old.center_px+np.arange(-40.,41.,2.)
    scales=np.array([old.px_per_db*.975,old.px_per_db,
                     old.px_per_db*1.025,grid.px_per_db])
    # Score plateaus occur on thick Smaart strokes. Without a
    # continuity prior, repeated still images choose a different, equally
    # good edge each refresh and gradually drift off the source curve.
    best=(-1.,None,None,None)
    for scale in scales:
        yy=np.rint(centers[:,None]-delta_db[None,:]*scale).astype(int)
        inside=(yy>=4)&(yy<h-5)
        clipped=np.clip(yy,3,h-4)
        bits=hit[clipped,xs[None,:]]&inside
        # Direct native colored pixels resolve several-pixel ambiguities
        # created by the 3px dilated stroke hit mask.
        raw=(mask[clipped,xs[None,:]]&inside).mean(axis=1)
        scores=0.65*bits.mean(axis=1)+0.35*raw
        continuous=scores-0.0015*np.abs(centers-old.center_px)
        continuous-=0.01*abs(scale-old.px_per_db)/old.px_per_db
        k=int(continuous.argmax())
        if continuous[k]>best[0]:
            best=(float(continuous[k]),float(centers[k]),float(scale),bits[k])
    _,center,scale,bits=best
    score=float(bits.mean())
    thirds=[float(z.mean()) for z in np.array_split(bits,3)]
    if (score<.86 or min(thirds)<.55 or
            abs(scale-grid.px_per_db)/grid.px_per_db>.08):
        return None
    fit=replace(old,center_px=center,px_per_db=scale,
                score=score,alternative_score=0.,bins=len(xs),
                accepted=True,reason="fresh pixel+grid verified same source")
    return FitFrame(source.revision,tuple(mag),fit,prior.color,
                    time.monotonic(),prior.hwnd,tuple(winrect),
                    source_identity=source.source_identity,
                    identity_verified=True,grid_agrees=True,
                    phase_plot=prior.phase_plot,
                    x_min=getattr(prior,"x_min",20.),
                    x_max=getattr(prior,"x_max",20000.))


def native_fit_worker(hwnd,source,preferred_color=None,prior=None,role_hint=None):
    """Off Qt thread, read the ORIGINAL Smaart window, never our overlay."""
    if not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):return None
    # V8.53 fast lane: skip expensive UIA + duplicate PrintWindow when
    # a previous *independently verified* frame already knows BOTH role
    # rectangles. Recheck Mag/Phase titles against NEW native pixels,
    # then refit source Mag/Y against this SAME image. Never reuse Y.
    # A changed window, layout or title fails to the full scan.
    # V8.106: an Auto EQ recompute of the SAME original measurement only
    # bumps the model revision; its role rectangles/color stay valid seeds
    # (still re-proven on this fresh capture). A different trace never
    # inherits the old cache or color (V8.53 contract).
    native=winrect=mag=phase_plot=None
    if prior is not None and prior.source_identity!=source.source_identity:
        preferred_color=None
    from smaart8_api3_readonly_v868 import process_smaart_major
    edition=process_smaart_major(hwnd)
    if edition==8:
        # V8.157: v9 native title signatures are NOT Smaart 8 signatures.
        # Verify BOTH plot roles against independent v8 native glyph masks,
        # from the very SAME freshly captured Smaart 8 window pixels that
        # will be used for grid and original-source color matching below.
        try:
            from smaart8_plot_profile_v868 import detect_v8_profile
            native,winrect=capture_native_window(hwnd)
            verified=detect_v8_profile(native)
            if verified is None:return None
            local_phase,local_mag=verified
            def to_screen(rect):
                return (int(rect[0]+winrect[0]),int(rect[1]+winrect[1]),
                        int(rect[2]),int(rect[3]))
            mag=to_screen(local_mag)
            phase_plot=to_screen(local_phase)
        except (OSError,RuntimeError,ValueError,TypeError,IndexError):
            return None
    elif edition not in (9,None):
        # Unknown explicit edition remains unsupported. A None probe may
        # come from a mocked/non-process HWND in offline QA; the legacy
        # Suite path still demands independent V9 title/pixel verification.
        return None
    if (edition!=8 and prior is not None and prior.identity_verified and
            prior.source_identity==source.source_identity and
            prior.hwnd==hwnd and
            prior.phase_plot is not None and prior.window_rect is not None):
        try:
            if tuple(win32gui.GetWindowRect(hwnd))==prior.window_rect:
                native,winrect=capture_native_window(hwnd)
                cached=detect_magnitude_rect(native,winrect,
                                              (prior.phase_plot,prior.plot))
                if cached is not None and tuple(cached[0])==prior.plot:
                    mag=tuple(prior.plot)
                    phase_plot=tuple(prior.phase_plot)
        except (OSError,RuntimeError,ValueError,TypeError):
            pass
    # The main overlay already owns a verified Phase/Mag role layout for the
    # same Smaart HWND. Reuse it only as a geometry hint, then prove it again
    # against a NEW native PrintWindow frame. This skips a multi-second UIA
    # walk without weakening source/color/Y identity gates below.
    if edition!=8 and mag is None and role_hint is not None:
        try:
            hinted_phase,hinted_mag=map(tuple,role_hint)
            if (len(hinted_phase)==4 and len(hinted_mag)==4 and
                    tuple(win32gui.GetWindowRect(hwnd))):
                native,winrect=capture_native_window(hwnd)
                detected=detect_magnitude_rect(
                    native,winrect,(hinted_phase,hinted_mag))
                if detected is not None and tuple(detected[0])==hinted_mag:
                    mag=hinted_mag
                    phase_plot=hinted_phase
        except (OSError,RuntimeError,ValueError,TypeError):
            native=winrect=mag=phase_plot=None
    if edition!=8 and mag is None:
        # Full fallback obtains fresh UIA geometry and role evidence.
        geo=locate_role_plots(hwnd)
        if geo is None:return None
        native,winrect=capture_native_window(hwnd)
        detected=detect_magnitude_rect(native,winrect,(geo.phase,geo.mag))
        if not detected or tuple(detected[0])!=tuple(geo.mag):
            return None
        mag=tuple(geo.mag)
        phase_plot=tuple(geo.phase)
    # P0: GRID measures pixels/dB, NOT selected TRF identity. The
    # ORIGINAL trace must match independently in the same captured frame.
    # Native color correlation also estimates the on-screen dB offset,
    # preserving Smaart's display Mag offset during pan/zoom.
    grid=fit_native_mag_grid(native,mag,winrect,saved_mag_grid_interval_major(edition))
    if edition==8:
        # Two independently tested Smaart8 log-axis modes, resolved ONLY
        # by a new native colored-curve fit on this original HWND capture.
        # The exporter still requires current 3/3 tick and 450-ms frame.
        from smaart8_native_xaxis_v8172 import select_smaart8_native_axis
        choice=select_smaart8_native_axis(
            native,mag,winrect,source.freqs,
            _display_db(source,source.original_db),source.coh,
            preferred_color=preferred_color)
        if choice is None:return None
        fit=choice.colorfit.fit
        agrees=bool(grid.accepted and grid.confidence>=.80 and
                    abs(grid.px_per_db-fit.px_per_db)/fit.px_per_db<=.12)
        return FitFrame(source.revision,mag,fit,choice.colorfit.color,
                        time.monotonic(),hwnd,tuple(winrect),
                        source_identity=source.source_identity,
                        identity_verified=True,grid_agrees=agrees,
                        phase_plot=phase_plot,x_min=choice.xmin,x_max=choice.xmax)
    if (prior is not None and prior.hwnd==hwnd and
            prior.color==preferred_color):
        tracked=_fast_refit_same_source(native,mag,winrect,source,grid,prior)
        if tracked is not None:return tracked
    # Once a color was verified for this immutable source, refit that
    # color only on the next native frames. New source still scans all
    # colors; this fast lane prevents frame expiry while repainting.
    if preferred_color in ("cyan","blue","red","green","magenta","gold"):
        known=fit_native_mag(native,mag,winrect,source.freqs,
                            _display_db(source,source.original_db),source.coh,
                            trace_color=preferred_color)
        if known.accepted:
            color_fit=ColorFit(preferred_color,known,0.,True)
        elif (grid.accepted and grid.confidence>=.95 and
              known.bins>=100 and known.score>=.95 and
              known.alternative_score<=.87 and
              known.score-known.alternative_score>=.10 and
              known.px_per_db>0 and
              abs(known.px_per_db-grid.px_per_db)/grid.px_per_db<=.08):
            color_fit=ColorFit(preferred_color,replace(known,accepted=True,
                      reason="previously verified color; grid corroborated"),
                      0.,True)
        else:
            return None
    else:
        color_fit=choose_color_fit(native,mag,winrect,
                                  source.freqs,_display_db(source,source.original_db),source.coh)
    if color_fit is None or not color_fit.accepted:
        # A very strong source curve can fall just short of the legacy
        # competing Y-fit margin. Recheck ONLY when independently
        # verified native-grid pixels corroborate the same Y scale.
        if not (grid.accepted and grid.confidence>=.95):
            return None
        matched=[]
        for col in ("cyan","blue","red","green","magenta","gold"):
            candidate=fit_native_mag(native,mag,winrect,source.freqs,
                      _display_db(source,source.original_db),source.coh,trace_color=col)
            if (candidate.bins>=100 and candidate.score>=.95 and
                    candidate.alternative_score<=.87 and
                    candidate.score-candidate.alternative_score>=.10 and
                    candidate.px_per_db>0 and
                    abs(candidate.px_per_db-grid.px_per_db)/
                      grid.px_per_db<=.08):
                matched.append((col,candidate))
        if len(matched)!=1:return None
        name,fit=matched[0]
        color_fit=ColorFit(name,replace(fit,accepted=True,
                        reason="strong original source pixels and verified Y grid"),
                        0.,True)
    fit=color_fit.fit
    if not fit.accepted or fit.score<.78 or fit.bins<55:
        return None
    agrees=bool(grid.accepted and grid.confidence>=.80 and
                abs(grid.px_per_db-fit.px_per_db)/fit.px_per_db<=.12)
    # Do NOT substitute the grid's zero line for the source-fitted offset.
    # Saved grid step may be stale when Smaart changes dB/div without save.
    # Pixel correlation wins; grid is an additional cross-check/diagnostic.
    return FitFrame(source.revision,mag,fit,color_fit.color,
                    time.monotonic(),hwnd,tuple(winrect),
                    source_identity=source.source_identity,
                    identity_verified=True,grid_agrees=agrees,
                    phase_plot=phase_plot)

def stroke_segments(painter,pts,coh):
    from mageq_visual_v13 import MAGEQ_LINE,MAGEQ_LINE_WIDTH,MAGEQ_HALO_WIDTH
    if len(pts)<2:return
    for trusted in (True,False):
        path=QPainterPath()
        active=False;last_x=None
        for (x,y),quality in zip(pts,coh):
            x=float(x);y=float(y)
            keep=(bool(quality)==trusted and np.isfinite(x) and np.isfinite(y))
            if not keep:
                active=False;last_x=None;continue
            if not active or (last_x is not None and x-last_x>23):
                path.moveTo(x,y)
            else:path.lineTo(x,y)
            active=True;last_x=x
        if trusted:
            painter.setPen(QPen(QColor(3,8,12,205),MAGEQ_HALO_WIDTH,
                                Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
        color=QColor(MAGEQ_LINE if trusted else "#D9C96A")
        if not trusted:color.setAlpha(135)
        pen=QPen(color,MAGEQ_LINE_WIDTH if trusted else 2.0)
        if not trusted:pen.setStyle(Qt.PenStyle.DotLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

class NativeAutoEQMag(QWidget):
    """One transparent full-MAG window belonging to the *QA* unified hub."""
    def __init__(self,hub):
        super().__init__(None)
        self.hub=hub
        flags=(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
               Qt.WindowType.WindowStaysOnTopHint|
               Qt.WindowType.WindowDoesNotAcceptFocus|
               Qt.WindowType.WindowTransparentForInput)
        self.setWindowFlags(flags)
        for att in (Qt.WidgetAttribute.WA_TranslucentBackground,
                    Qt.WidgetAttribute.WA_ShowWithoutActivating,
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents):
            self.setAttribute(att,True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.enabled=True  # Only controls MagEq; NEVER Smaart original Mag
        self.source=None;self.frame=None;self.future=None
        self.mageq_history=[]  # QA audit only; current view retains exactly one
        self.revision=0;self.last_submit=0
        self.approved_token=None
        self._last_verified_color=None
        self._last_verified_frame=None
        self._verify_failed=False
        self._verify_failures=0
        self.last_native_drop=""
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="eq_mag_native")
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(90)
        self.hide()

    def showEvent(self,event):
        super().showEvent(event)
        try:
            hwnd=int(self.winId())
            old=win32gui.GetWindowLong(hwnd,win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd,win32con.GWL_EXSTYLE,old|
              win32con.WS_EX_TRANSPARENT|win32con.WS_EX_NOACTIVATE|
              win32con.WS_EX_LAYERED|win32con.WS_EX_TOOLWINDOW)
        except Exception:pass

    def set_enabled(self,enabled):
        self.enabled=bool(enabled)
        self._sync_sum_renderer()
        self.hide()
        self.update()

    def clear(self):
        self.revision+=1
        self.approved_token=None
        # V8.106: keep _last_verified_frame/_color as re-verified SEEDS only
        # (window geometry; color/Y only for the same original identity).
        # Dropping them forced a full UIA rescan on every Auto EQ recompute.
        self.source=None
        self.frame=None
        self._ready_logged=None  # reset transition-only diagnostics
        self._sync_sum_renderer()
        self.hide()
        self.update()

    def _source_binding_ok(self,*,presentation=False):
        """Strict export source token; separate bounded presentation-only gate.

        Native source and current window still need independent proof.
        Never use presentation=True for Export, calculate or drag start.
        """
        src=self.source
        eq=getattr(self.hub,"eq",None)
        token=getattr(eq,"_export_source_token",None)
        if src is None or not token or self.approved_token!=token:
            return False
        if (Path(token[0]).stem!=src.source_name or
                getattr(eq,"result",None) is None):
            return False
        getter=getattr(eq,"_verified_single",None)
        if not callable(getter):
            return False
        if getter()!=token:
            if not (presentation and self.hub._eq_tick_safe()):
                return False
        try:
            stat=Path(token[0]).stat()
            return (stat.st_mtime_ns,stat.st_size)==(token[1],token[2])
        except OSError:
            return False

    def _presentable(self,frame,hwnd):
        """Display-only freshness (V8.106 grace); export/drag stay strict."""
        return frame_presentable(frame,hwnd,
                                 verifying=verification_recoverable(self))

    def _sync_sum_renderer(self):
        """Drive original AutoPhase Mag QWidget; never show a second window."""
        graph=self.hub.engine.graph_mag
        active=(self.source is not None and self.frame is not None and
                self._source_binding_ok(presentation=True) and
                bool(getattr(self.frame,"identity_verified",False)) and
                self.frame.source_identity==getattr(self.source,"source_identity",None) and
                frame_presentable(self.frame,self.frame.hwnd,
                                  verifying=verification_recoverable(self)) and
                self.enabled and self.hub.active=="eq" and
                self.hub.isVisible() and self.hub.workspace_visible and
                self.hub._eq_tick_safe())
        if active:
            changed=(graph.mageq_source is not self.source or
                     graph.mageq_frame is not self.frame or
                     graph.geometry().getRect()!=self.frame.plot)
            if not changed:
                # Regression V18: MagEq data/frame can remain cached while
                # the native QWidget was hidden during a UI mode transition.
                # Always re-arm *visibility* without recalculating/repainting.
                if not graph.isVisible():
                    self.hub.engine.refresh_visibility()
                return
            if graph.geometry().getRect()!=self.frame.plot:
                graph.setGeometry(*self.frame.plot)
            graph.set_mageq(self.source,self.frame)
        else:
            if graph.mageq_source is None and graph.mageq_frame is None:
                return
            graph.set_mageq()
        self.hub.engine.refresh_visibility()

    def set_data(self,freq,h,coh,proposal,source_index,source_name):
        self.clear()
        # Presentation is broader than authorization: an unsafe/no-solution
        # result may show the original bypass curve, but EQ export remains
        # restricted to PREVIEW_READY by EQDialog's snapshot/native gate.
        approved=(proposal is not None and
                  np.isfinite(proposal.before_db).all() and
                  np.isfinite(proposal.after_db).all())
        if not approved:return
        try:
            self.source=build_state(freq,h,coh,proposal.peqs,
                 fs=proposal.fs,source_index=int(source_index),
                 source_name=source_name,revision=self.revision,
                 allow_bypass=not bool(proposal.peqs),
                 display_smooth_oct=float(
                     self.hub.engine.mag_smooth.currentData() or 0.))
            eq=getattr(self.hub,"eq",None)
            token=getattr(eq,"_export_source_token",None)
            # Only a stable, verified Data Bar token may bind this data.
            if (token and Path(token[0]).stem==source_name and
                    getattr(eq,"result",None) is proposal):
                self.approved_token=token
            # Replace, never stack, previous MagEq layers. Smaart originals
            # stay in their native graph, untouched by this Qt overlay.
            self.mageq_history=[(self.source.name,self.source.source_identity)]
            # Start registration immediately after PEQ is approved. A delay
            # until the periodic 150ms worker can leave PREVIEW_READY but
            # no MagEq until a later UI interaction.
            self.last_submit=0.
            print("V8152_AUTOEQ_PREVIEW_READY",source_name,
                  len(proposal.peqs),proposal.status,flush=True)
            QTimer.singleShot(0,self.tick)

        except (ValueError,TypeError):
            self.source=None
            return

    def tick(self):
        # Timer exists for fast activation, but a tool with no source and
        # no in-flight verification must not do any native/UIA work.
        # A new approved source calls QTimer.singleShot(0,self.tick).
        if self.source is None and self.future is None and self.frame is None:
            return
        source=self.source
        if source is not None:
            control=getattr(getattr(self.hub,"engine",None),"mag_smooth",None)
            current=(float(control.currentData() or 0.) if control is not None
                     else float(getattr(source,"display_smooth_oct",0.) or 0.))
            # V8.170 QA: Smaart 8 has no verified UIA Mag Smooth selector.
            # Use unsmoothed original as an initial CANDIDATE, not proof.
            # The native fit still must independently accept the current
            # colored MAG pixels for the SAME trace/window; other live
            # smoothing modes remain strict HOLD rather than guessed.
            try:
                v8_host=verified_smaart_host(self.hub)
                if v8_host:
                    from smaart8_api3_readonly_v868 import process_smaart_major
                    if process_smaart_major(v8_host)==8:
                        current=0.0
            except (OSError,ValueError,TypeError):
                pass
            if (control is not None and
                    abs(current-float(getattr(source,"display_smooth_oct",0.) or 0.))>1e-12):
                source=replace(source,display_smooth_oct=current)
                self.source=source
                self.frame=None
        if os.environ.get("REMIX_QA_TRACE_MAGEQ")=="1":
            try:
                from qa_v18_runtime_diagnostics import record
                record(self)
            except Exception:pass
        basic=(source is not None and self.enabled and
               self.hub.active=="eq" and self.hub.isVisible() and
               self.hub.workspace_visible)
        # Preserve the original short-circuit semantics of the UI guard.
        gate_safe=self.hub._eq_tick_safe() if basic else False
        binding_ok=self._source_binding_ok(presentation=True) if gate_safe else False
        checks=(source is not None,bool(self.enabled),self.hub.active=="eq",
                bool(self.hub.isVisible()),bool(self.hub.workspace_visible),
                bool(gate_safe),bool(binding_ok))
        if os.environ.get("REMIX_QA_TRACE_EQ_TRANSITIONS")=="1":
            now=time.monotonic()
            label=("source","enabled","eq_active","hub_visible","workspace",
                   "tick_safe","binding_ok")
            signature=(checks, self.last_native_drop, bool(self.future),
                       getattr(self,"_verify_failures",0))
            if signature!=getattr(self,"_qa_last_sig",None) or (
                    now-getattr(self,"_qa_last_sig_at",0)>1.):
                self._qa_last_sig=signature
                self._qa_last_sig_at=now
                print("V8171_EQ_NATIVE_GATE",
                      dict(zip(label,checks)),"future_running",
                      bool(self.future and not self.future.done()),
                      "frame",bool(self.frame),"drop",self.last_native_drop,
                      flush=True)
        if not all(checks):
            self.frame=None
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        # V8.157: bind to the observer's VERIFIED Smaart host, not the
        # edition-specific window title. Smaart 8 is titled "Smaart",
        # while Suite is titled "Smaart Suite"; FindWindow("Smaart Suite")
        # silently prevented every Smaart 8 MagEQ native registration.
        # Never discover a different edition by window z-order here.
        hwnd=verified_smaart_host(self.hub)
        if not hwnd:
            # No SAME verified viewport -> cached fit not authorized.
            self.frame=None
            self.last_native_drop="Smaart source host missing, switched or minimized"
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        front=win32gui.GetForegroundWindow()
        try:
            active_pid=win32process.GetWindowThreadProcessId(front)[1]
            smaart_pid=win32process.GetWindowThreadProcessId(hwnd)[1]
        except Exception:active_pid=smaart_pid=0
        if active_pid not in (smaart_pid,os.getpid()) or not active_pid:
            self.frame=None
            self.last_native_drop="Smaart/RemiX lost foreground"
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        if self.future is not None and self.future.done():
            f=self.future
            self.future=None
            try:frame=f.result()
            except Exception as exc:
                frame=None
                self.last_native_drop="native_fit_worker_error: "+repr(exc)[:160]
                if os.environ.get("REMIX_QA_TRACE_EQ_TRANSITIONS")=="1":
                    print("V8171_EQ_NATIVE_FUTURE_ERROR",repr(exc),flush=True)
            if (frame is not None and frame.revision==source.revision
                    and frame.identity_verified and
                    frame.source_identity==getattr(source,"source_identity",None) and
                    frame_is_fresh_for_window(frame,hwnd)):
                self.frame=frame
                self._last_verified_color=frame.color
                self._last_verified_frame=frame
                self._verify_failed=False
                self._verify_failures=0
                self.last_native_drop=""
                # V8.160: the native GUI-thread pixel proof has just arrived.
                # Refresh strict Export immediately rather than waiting for
                # the separate 175-ms ToolHub poll (frame TTL is only 450 ms).
                # This does NOT grant Export: _native_export_ok still verifies
                # tick, source identity, current frame/viewport, Fs and TRF.
                self.hub.eq._refresh_export_gate()
                status_label=getattr(self.hub.eq,"native_state",None)
                if status_label is not None:
                    status_label.setText(
                        "DSP READY | Native READY (fresh-pixel verified)"
                        + (" | Export READY" if self.hub.eq._native_export_ok()
                           else " | Export HOLD: tick/Fs/source"))
                # A verified static TRF does not need an identical READY log
                # on every tick; preserve transition diagnostics only.
                signature=(frame.revision,frame.color,
                           round(frame.fit.score,3),frame.fit.bins)
                if signature!=getattr(self,"_ready_logged",None):
                    print("V8152_MAGEQ_NATIVE_READY",frame.color,
                          round(frame.fit.score,3),frame.fit.bins,flush=True)
                    self._ready_logged=signature
            else:
                # One failed PrintWindow/UIA capture must not flash MagEq
                # off if the last verified fit still matches this window,
                # but it ends the V8.106 in-flight grace (strict TTL now).
                self._verify_failed=True
                self._verify_failures=getattr(self,"_verify_failures",0)+1
                if self._verify_failures>=SEED_DROP_AFTER_FAILURES:
                    # Seeds survive recompute (V8.106); never let a stale
                    # color/geometry seed block a fresh independent scan.
                    self._last_verified_color=None
                    self._last_verified_frame=None
                    self.frame=None
                self.last_native_drop="Transient native fit failure"
        if self.frame is not None and (
                self.frame.revision!=source.revision or
                not self._presentable(self.frame,hwnd)):
            self.frame=None
            self.last_native_drop="Native frame expired or viewport changed"
        now=time.monotonic()
        # V8.155: throttle redundant native pixel-fit capture. The .22s
        # interval stays below the strict .45s native-frame freshness TTL.
        if self.future is None and now-self.last_submit>.22:
            self.last_submit=now
            role_hint=None
            layout=getattr(self.hub.engine,"plot_layout",None)
            plot_hwnd=getattr(self.hub.engine,"plot_hwnd",None)
            if (layout is not None and plot_hwnd==hwnd and
                    getattr(layout,"phase",None) is not None and
                    getattr(layout,"mag",None) is not None):
                role_hint=(tuple(layout.phase),tuple(layout.mag))
            self.future=self.pool.submit(native_fit_worker,hwnd,source,
                                         self._last_verified_color,
                                         self._last_verified_frame,role_hint)
        frame=self.frame
        if frame is None:
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        x,y,w,h=frame.plot
        if w<820 or h<210:
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        # Single model renderer: no .show() here. Render in engine.graph_mag.
        self._sync_sum_renderer()
        if self.isVisible():self.hide()

    def paintEvent(self,event):
        src,frame=self.source,self.frame
        if src is None or frame is None:return
        x,y,w,h=frame.plot
        pts,trust=native_points(frame.plot,frame.fit,
                                 src.freqs,_display_db(src,src.after_db),src.coh,
                                 expect_x_min=frame.x_min,expect_x_max=frame.x_max)
        if len(pts)<2:return
        pts[:,0]-=x;pts[:,1]-=y
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.save();p.setClipRect(QRectF(0,0,w,h))
        stroke_segments(p,pts,trust)
        for i,band in enumerate(src.peqs):
            hz=float(band.f_hz)
            if not 20<hz<20000:continue
            mx=w*np.log(hz/20)/np.log(1000)
            k=int(np.argmin(np.abs(pts[:,0]-mx)))
            px,py=pts[k]
            if not 4<px<w-12 or not 17<py<h-12:continue
            p.setBrush(QColor("#4b3317"))
            p.setPen(QPen(QColor("#ffc174"),1.5))
            p.drawEllipse(QPointF(float(px),float(py)),5,5)
            p.setPen(QColor("#ffd29b"))
            p.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
            p.drawText(QPointF(float(px+7),float(py-8)),f"EQ{i+1}")
        p.restore()
        p.setPen(QColor("#A9FF70"))
        p.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
        p.drawText(QPointF(125,19),
                   f"MagEq [{src.source_name}]   {len(src.peqs)} PEQ   "
                   f"REF {frame.color.upper()} {frame.fit.score*100:.0f}%")
        p.setFont(QFont("Segoe UI",8))
        p.setPen(QColor("#d6e0e7"))
        p.drawText(QPointF(125,36),
                   "Mag gốc: Smaart không đổi  |  MagEq: đường dự đoán mới  |  KHÔNG GHI DSP")
        p.end()

    def stop(self):
        self.clear()
        self.timer.stop()
        bounded_shutdown(self.pool)
        self.close()
