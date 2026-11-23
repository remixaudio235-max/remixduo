"""V8.46: read-only native FIR Mag/Phase overlay calibration.

Single captured Smaart frame, independently validated original TRF Mag and
Phase pixels. No fallback to stored axes, guessed Y, or stale GRID.
Rendering uses existing SUM Mag and Phase QWidgets, never separate windows.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import numpy as np
import win32gui,win32process,os
from scipy.signal import freqz
from PIL import Image,ImageDraw
from PyQt6.QtCore import QTimer
from native_eq_mag_v06 import (frame_is_fresh_for_window,
    NATIVE_DISPLAY_GRACE_S,SEED_DROP_AFTER_FAILURES,verification_recoverable,
    verified_smaart_host)
from smaart_native_mag_fit import (
    capture_native_window,trace_color_mask,NativeMagFit,fit_native_mag)
from smaart_eq_color_select import choose_color_fit,ColorFit
from smaart_native_y_grid_v839 import fit_native_mag_grid,saved_mag_grid_interval,saved_mag_grid_interval_major
from plot_role_v812 import locate_role_plots
from smaart_mag_plot_detector import detect_magnitude_rect
from phase_axis_absolute_v79 import _dilate_9
from tf_display_smoothing import smooth_phase_unit_phasor,smooth_log_octaves
from smaart_smooth_sync_v811 import read_saved_smooth
from mag_sum_native_v826 import smaart8_raster_candidates

from remix_duo.core.fir_preview import FIRSource, make_source, PREVIEW_COHERENCE_GATE
from worker_lifecycle_v8142 import bounded_shutdown

MAX_AGE=.45
FIR_DISPLAY_GRACE_S=3.0  # native Suite fit is ~1.77 s; display-only bridge
FIR_TRANSIENT_BLOCKS=frozenset((
    "tool_inactive","workspace_hidden","hub_hidden","smaart_hidden",
    "foreground_changed"))
COLORS=("cyan","blue","red","green","magenta","gold")




@dataclass(frozen=True)
class FIRFrame:
    revision:int
    source_identity:str
    hwnd:int
    window_rect:tuple
    mag:tuple
    phase:tuple
    mag_fit:NativeMagFit
    phase_top:float
    phase_span:float
    phase_score:float
    mag_color:str
    created:float
    phase_verified:bool
    mag_raster:bytes|None=None
    phase_raster:bytes|None=None
    mag_smooth_oct:float=0.
    phase_smooth_oct:float=0.




def phase_native_fit(image,phase_rect,winrect,src,color,center_top=180.):
    """Native Phase pixel-fit for THIS source and THIS Mag-match color.

    Returns a validated top-of-chart angle (360-degree phase only).
    Unsupported Y zoom/missing native curve => None (PhaseFIR HOLD).
    """
    x,y,w,h=map(int,phase_rect)
    wl,wt,_,_=map(int,winrect)
    if w<700 or h<200:return None
    crop=image.crop((x-wl,y-wt,x-wl+w,y-wt+h))
    mask=trace_color_mask(crop,color)
    if int(mask.sum())<150:return None
    hits=_dilate_9(mask,4)
    hz=src.freqs
    xpos=np.rint(w*np.log(np.maximum(hz,1e-6)/20.)/
                   np.log(1000.)).astype(int)
    good=(src.phase_valid&np.isfinite(src.original_phase)&
          (hz>=60.)&(hz<=3500.)&(xpos>45)&(xpos<w-335))
    xs=xpos[good]
    phase=src.original_phase[good]
    # Thin dense bins to avoid over-weighting a small frequency region.
    if xs.size<65:return None
    chosen=np.unique(xs,return_index=True)[1]
    xs=xs[chosen]
    phase=phase[chosen]
    if len(xs)<65:return None
    candidates=np.arange(int(round(center_top))-180,
                         int(round(center_top))+181,dtype=float)
    yp=np.rint(((candidates[:,None]-phase[None,:])%360.)*h/360.).astype(int)
    yp=np.clip(yp,1,h-2)
    quality=hits[yp,xs[None,:]].mean(axis=1)
    best_i=int(np.argmax(quality))
    top=float(candidates[best_i])
    quality_best=float(quality[best_i])
    circular=np.abs((candidates-top+180)%360-180)
    alt=float(quality[circular>=35].max())
    if quality_best<.78 or quality_best-alt<.20:
        return None
    return (top,quality_best)


# V8.134: why the last native_fir_frame call could not draw (worker is a
# single thread; read by NativeFIROverlay to toast the reason on the plot).
LAST_HOLD_REASON=[None]


def _hold(reason):
    LAST_HOLD_REASON[0]=reason
    return None


def native_trace_hold_reason():
    """Actionable fail-closed guidance when the source has no native fit."""
    return ("Không đủ phần đường Trace nhìn thấy trên plot Mag — đổi vùng LF/HF "
            "sang đoạn Trace đang hiện hoặc zoom trục dB, rồi bấm TẠO FIR lại")


def native_fir_frame(hwnd,src,center_phase_top=180.,prior=None,hint_color=None,
                     role_hint=None,smooth_hint=None):
    """Independent native source registration from ONE FRESH PrintWindow.

    A prior valid frame may seed only prior rectangles and original-trace
    color. Both native titles and source magnitude must STILL match fresh
    pixels. Prior phase/Y fits and old raster are never reused for output.
    """
    LAST_HOLD_REASON[0]=None
    if not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):return None
    img=window=mag=phase=None
    from smaart8_api3_readonly_v868 import process_smaart_major
    edition=process_smaart_major(hwnd)
    if edition==8:
        # V8.158: only Smaart 8-specific Phase/Mag title glyphs may
        # approve a native FIR render on Smaart 8. Capture once and
        # independently match original trace Mag AND Phase pixels below.
        try:
            from smaart8_plot_profile_v868 import detect_v8_profile
            img,window=capture_native_window(hwnd)
            verified=detect_v8_profile(img)
            if verified is None:
                return _hold("Không xác minh được Phase/Magnitude Smaart 8")
            local_phase,local_mag=verified
            def screen_rect(r):
                return (int(r[0]+window[0]),int(r[1]+window[1]),
                        int(r[2]),int(r[3]))
            phase=screen_rect(local_phase)
            mag=screen_rect(local_mag)
        except (OSError,RuntimeError,ValueError,TypeError,IndexError) as exc:
            return _hold("Smaart 8 native capture thất bại: "+type(exc).__name__)
    elif edition not in (9,None):
        return _hold("Smaart edition chưa được hỗ trợ cho Native FIR")
    # V8.106: a FIR recompute of the SAME original measurement only bumps
    # the revision; its rectangles/color stay seeds re-proven below. A
    # different trace never inherits the old cache (V8.60 contract).
    cached=(edition!=8 and prior is not None and prior.source_identity==src.identity and
            prior.hwnd==int(hwnd) and
            tuple(win32gui.GetWindowRect(hwnd))==prior.window_rect)
    same_source=cached
    if cached:
        img,window=capture_native_window(hwnd)
        detected=detect_magnitude_rect(img,window,
                                       (prior.phase,prior.mag))
        if detected is not None and tuple(detected[0])==prior.mag:
            mag=tuple(prior.mag)
            phase=tuple(prior.phase)
    # The overlay already owns a verified Phase/Mag layout. Use it only as a
    # geometry hint and re-prove the Mag title on a fresh PrintWindow frame.
    # This avoids a multi-second UIA walk that can outlive the bounded tick
    # presentation proof; source/color/Y/phase identity gates below remain.
    if edition!=8 and mag is None and role_hint is not None:
        try:
            hinted_phase,hinted_mag=map(tuple,role_hint)
            if len(hinted_phase)==4 and len(hinted_mag)==4:
                img,window=capture_native_window(hwnd)
                detected=detect_magnitude_rect(
                    img,window,(hinted_phase,hinted_mag))
                if detected is not None and tuple(detected[0])==hinted_mag:
                    mag=hinted_mag
                    phase=hinted_phase
        except (OSError,RuntimeError,ValueError,TypeError):
            img=window=mag=phase=None
    if edition!=8 and mag is None:
        # First frame, changed layout, or changed title: use full UIA.
        layout=locate_role_plots(hwnd)
        if layout is None:
            return _hold("Không thấy plot Phase/Mag của Smaart — mở TF View, đừng che Smaart")
        img,window=capture_native_window(hwnd)
        detected=detect_magnitude_rect(img,window,
                                       (layout.phase,layout.mag))
        if detected is None or tuple(detected[0])!=tuple(layout.mag):
            return _hold("Không nhận ra plot Mag của Smaart — mở TF View, đừng che Smaart")
        mag=tuple(layout.mag)
        phase=tuple(layout.phase)
    # The native Smaart plot displays a SMOOTHED measurement, while the
    # original stored TRF and FIR design must remain unsmoothed.
    # V8.60: independently verify the saved visible smoothing setting
    # and apply it ONLY to source/prediction raster registration.
    if smooth_hint is not None:
        from types import SimpleNamespace
        smooth=SimpleNamespace(mag_oct=float(smooth_hint[0]),
                               phase_oct=float(smooth_hint[1]),
                               mag_verified=True,phase_verified=True)
    else:
        smooth=read_saved_smooth()
    if smooth is None or not smooth.mag_verified:
        return _hold("Chưa đọc được Smoothing Mag của Smaart")
    source_display=smooth_log_octaves(src.freqs,src.original_db,
                                       smooth.mag_oct)
    choice=None
    if same_source and phase==tuple(prior.phase):
        # Recheck the previously verified original source/color with
        # an entirely new capture: no unproven GRID-only fallback.
        candidate=fit_native_mag(
            img,mag,window,src.freqs,source_display,src.coherence,
            trace_color=prior.mag_color)
        if candidate.accepted:
            choice=ColorFit(prior.mag_color,candidate,0.,True)
    if choice is None:
        extra={"hint":hint_color} if hint_color else {}
        original_mag=tuple(mag)
        candidates=(smaart8_raster_candidates(mag)
                    if edition==8 else (tuple(mag),))
        for candidate in candidates:
            attempted=choose_color_fit(img,candidate,window,src.freqs,
                                       source_display,src.coherence,**extra)
            if attempted is None or not attempted.accepted:
                continue
            choice=attempted
            if candidate!=original_mag:
                inset=int(candidate[0]-original_mag[0])
                mag=tuple(candidate)
                phase=(int(phase[0]+inset),int(phase[1]),
                       int(candidate[2]),int(phase[3]))
            break
    if choice is None or not choice.accepted:
        return _hold(native_trace_hold_reason())
    fit=choice.fit
    if not (fit.accepted and fit.bins>=55 and fit.score>=.78):
        return _hold(f"Đường Trace trên Smaart không khớp dữ liệu ({fit.score:.0%}) — kéo LF/HF "
                     "sang vùng Coherence cao")
    # Grid is only a diagnostic; matched SOURCE offset is authoritative.
    grid=fit_native_mag_grid(img,mag,window,saved_mag_grid_interval_major(edition))
    if (grid.accepted and grid.confidence>=.8 and
            abs(grid.px_per_db-fit.px_per_db)/fit.px_per_db>.20):
        return _hold("Trục dB của Smaart không khớp — đổi zoom dB rồi bấm TẠO FIR lại")
    # V8.134: the display model is built at Smaart's Phase smoothing at
    # design time (src.phase_smooth_oct); it must still match what is shown.
    model_oct=float(getattr(src,"phase_smooth_oct",1/6))
    phase_compatible=bool(smooth.phase_verified and
                          abs(smooth.phase_oct-model_oct)<1e-9)
    pf=(phase_native_fit(img,phase,window,src,choice.color,
                         center_phase_top) if phase_compatible else None)
    if src.mode=="phase" and not phase_compatible:
        LAST_HOLD_REASON[0]=(
            "Smoothing Phase Smaart đã đổi — bấm TẠO FIR lại" if smooth.phase_verified
            else "Chưa đọc được Smoothing Phase của Smaart")
    elif src.mode=="phase" and pf is None:
        LAST_HOLD_REASON[0]=("Không khớp được đường Phase trên Smaart — kéo LF/HF sang "
                             "vùng Coherence cao")
    if smooth_hint is None and read_saved_smooth()!=smooth:
        return None  # saved Smaart display settings changed mid-capture
    frame=FIRFrame(src.revision,src.identity,int(hwnd),tuple(window),
                   mag,phase,fit,pf[0] if pf else 0.,360.,
                   pf[1] if pf else 0.,choice.color,time.monotonic(),
                   pf is not None,mag_smooth_oct=smooth.mag_oct,
                   phase_smooth_oct=smooth.phase_oct)
    return rasterize_fir_frame(src,frame)


def rasterize_fir_frame(src,frame):
    """All high-cost FIR polylines become immutable RGBA rasters in worker.

    QPainter only blits a prepared same-snapshot image, never stroking
    several thousand 360-degree-wrapped segments on the UI thread.
    """
    rasters={}
    for name,coords,rect,enabled,color in (
        ("mag",fir_mag_points(src,frame),frame.mag,True,(73,228,255,255)),
        ("phase",fir_phase_points(src,frame),frame.phase,
         frame.phase_verified,(218,165,255,255))):
        if not enabled:
            rasters[name]=None
            continue
        points,valid=coords
        w,h=int(rect[2]),int(rect[3])
        img=Image.new("RGBA",(w,h),(0,0,0,0))
        dr=ImageDraw.Draw(img)
        previous=None
        for (xx,yy),good in zip(points,valid):
            x=float(xx);y=float(yy)
            if not good or not np.isfinite(x) or not np.isfinite(y) or (
                    x<0 or x>=w or y<0 or y>=h):
                previous=None
                continue
            if previous is not None and x-previous[0]<=20 and not (
                    name=="phase" and abs(y-previous[1])>h*.45):
                dr.line((previous[0],previous[1],x,y),fill=color,width=3)
            previous=(x,y)
        rasters[name]=img.tobytes()
    return replace(frame,mag_raster=rasters["mag"],
                   phase_raster=rasters["phase"])


def native_fir_fresh(frame,src,hwnd,mag_rect=None,phase_rect=None,
                     *,now=None,max_age_s=None):
    if max_age_s is None:max_age_s=MAX_AGE
    if (frame is None or src is None or frame.revision!=src.revision or
            frame.source_identity!=src.identity):
        return False
    if (mag_rect is not None and tuple(mag_rect)!=frame.mag) or (
            phase_rect is not None and tuple(phase_rect)!=frame.phase):
        return False
    return frame_is_fresh_for_window(frame,hwnd,now=now,max_age_s=max_age_s)


def fir_mag_points(src,frame):
    """Magnitude geometry from one immutable source/native frame."""
    x,y,w,h=frame.mag
    xx=w*np.log(src.freqs/20.)/np.log(1000.)
    # Render the predicted filtered MAG in the SAME display smoothing
    # domain as the reference native source. Never smooth FIR taps/FFT.
    display_after=smooth_log_octaves(src.freqs,src.after_db,
                                     frame.mag_smooth_oct)
    yy=frame.mag_fit.y(display_after)
    good=np.isfinite(yy)&np.isfinite(xx)&(src.freqs>=20)&(src.freqs<=20000)
    return np.column_stack((xx,yy)),good


def fir_phase_points(src,frame):
    """360-degree periodic mapping preserving complex FIR delay and wraps."""
    if not frame.phase_verified:return np.empty((0,2)),np.empty(0,dtype=bool)
    x,y,w,h=frame.phase
    xx=w*np.log(src.freqs/20.)/np.log(1000.)
    raw=getattr(src,"original_complex",None)
    comp=getattr(src,"compensated_response",None)
    if raw is not None and comp is not None:
        display,valid,_=smooth_phase_unit_phasor(
            src.freqs,raw,np.ones_like(src.coherence),
            frame.phase_smooth_oct or None,0.)
        display=np.rad2deg(np.angle(
            np.exp(1j*np.deg2rad(display))*comp))
    else:
        display=src.display_phase if src.display_phase is not None else src.after_phase
        valid=src.phase_valid
    yy=((frame.phase_top-display)%frame.phase_span)*h/frame.phase_span
    good=(valid & np.isfinite(xx) & np.isfinite(yy)&
          (src.freqs>=20)&(src.freqs<=20000))
    return np.column_stack((xx,yy)),good


class NativeFIROverlay:
    """Shared native Mag/Phase graph coordinator, no new Qt plot windows."""
    def __init__(self,hub):
        self.hub=hub
        self.source=None
        self.frame=None
        self.last_verified=None  # geometry/color seed; NEVER a stale paint
        self._verify_failed=False
        self._verify_failures=0
        self.future=None
        self.last_submit=0.
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="fir_native")
        self.timer=QTimer(hub)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    # V8.106: clear/accept keep last_verified as a re-verified SEED only
    # (native_fir_frame re-proves titles/color on fresh pixels). Dropping it
    # forced a full UIA rescan (~0.35-0.6 s) on every FIR recompute.
    def clear(self):
        self.source=None
        self.frame=None
        self.future=None  # stale completion is ignored, worker stays isolated
        self._publish()

    def accept(self,src):
        self.source=src
        self.frame=None
        self.future=None
        self._verify_failed=False
        self._verify_failures=0  # new source always gets immediate native proof
        self._last_no_frame_reason=None
        self.last_submit=0.
        self._accepted_at=time.monotonic()
        self._toasted=set()
        self._publish()
        QTimer.singleShot(0,self.tick)

    def _allowed(self):
        reason=None
        if self.hub.active!="fir": reason="tool_inactive"
        elif not self.hub.workspace_visible: reason="workspace_hidden"
        elif not self.hub.isVisible(): reason="hub_hidden"
        elif self.source is None: reason="source_missing"
        elif self.source.identity!=self.hub.fir._approved[1]: reason="source_identity_changed"
        if reason is not None:
            if getattr(self,"_last_allowed_reason",None)!=reason:
                self._last_allowed_reason=reason
                print("V8150_FIR_NATIVE_BLOCK",reason,flush=True)
            return 0
        # Never bind a FIR plot to whichever Smaart edition happens to
        # have a matching title. This is the same strict HWND used by
        # native MagEQ: the verified observer and active hub must agree.
        target=verified_smaart_host(self.hub)
        if not target:
            self._last_allowed_reason="smaart_hidden"
            return 0
        try:
            front=win32gui.GetForegroundWindow()
            fp=win32process.GetWindowThreadProcessId(front)[1]
            sp=win32process.GetWindowThreadProcessId(target)[1]
            if fp not in (sp,os.getpid()):
                reason="foreground_changed"
                if getattr(self,"_last_allowed_reason",None)!=reason:
                    self._last_allowed_reason=reason
                    print("V8150_FIR_NATIVE_BLOCK",reason,flush=True)
                return 0
        except Exception:
            return 0
        self._last_allowed_reason=None
        return target

    def _presentable(self,frame,hwnd,mag_rect=None,phase_rect=None):
        """Display-only freshness with the V8.106 in-flight grace."""
        if native_fir_fresh(frame,self.source,hwnd,mag_rect,phase_rect):
            return True
        verifying=verification_recoverable(self)
        return bool(verifying and native_fir_fresh(
            frame,self.source,hwnd,mag_rect,phase_rect,
            max_age_s=FIR_DISPLAY_GRACE_S))

    def _publish(self):
        engine=self.hub.engine
        src,frame=self.source,self.frame
        allowed=self._allowed() if src and frame else 0
        # Hiding/switching the dock only suspends native re-proof.  The last
        # independently verified FIR remains cached so returning to the panel
        # cannot produce PASS -> HOLD flicker or erase the plotted line.
        if (src is not None and frame is not None and not allowed and
                getattr(self,"_last_allowed_reason",None) in FIR_TRANSIENT_BLOCKS):
            engine.refresh_visibility()
            return
        ready=bool(allowed and engine.plot_layout and
                   self._presentable(frame,allowed,
                                     engine.plot_layout.mag,
                                     engine.plot_layout.phase))
        for graph,phase in ((engine.graph_mag,False),(engine.graph_phase,True)):
            good=ready and (src.mode==("phase" if phase else "mag")) and (not phase or frame.phase_verified)
            if good:
                if graph.fir_source is not src or graph.fir_frame is not frame:
                    graph.set_fir(src,frame)
            elif graph.fir_source is not None or graph.fir_frame is not None:
                graph.set_fir()
        label=("MagFIR "+("PASS" if ready else "HOLD") if src is not None and src.mode=="mag" else "MagFIR OFF") + " | " + (
            "PhaseFIR "+("PASS" if ready and frame.phase_verified else "HOLD") if src is not None and src.mode=="phase" else "PhaseFIR OFF")
        status=getattr(self.hub.fir,"overlay_status",None)
        if status is not None and status.text()!=label:
            # V8.124: the status label is hidden in the dock; log changes.
            print("V8124_FIR_NATIVE",label,flush=True)
            status.setText(label)
        engine.refresh_visibility()

    def tick(self):
        # No data / no in-flight work: skip UIA, HWND and status probes.
        # accept() schedules an immediate tick on the newly active tool.
        if self.source is None and self.future is None and self.frame is None:
            return
        hwnd=self._allowed()
        if not hwnd:
            if (self.frame is not None and
                    getattr(self,"_last_allowed_reason",None) not in FIR_TRANSIENT_BLOCKS):
                self.frame=None
                self._publish()
            return
        if self.future is not None and self.future.done():
            task=self.future
            self.future=None
            try:
                frame=task.result()
            except Exception as exc:
                print("V8150_FIR_NATIVE_EXCEPTION",repr(exc),flush=True)
                frame=None
            if (frame is not None and self.source is not None and
                    native_fir_fresh(frame,self.source,hwnd)):
                self.frame=frame
                self.last_verified=frame
                self._verify_failed=False
                self._verify_failures=0
                self._last_no_frame_reason=None
            else:
                if frame is None:
                    reason=LAST_HOLD_REASON[0]
                    if reason!=getattr(self,"_last_no_frame_reason",None):
                        print("V8150_FIR_NATIVE_NO_FRAME",reason,flush=True)
                        self._last_no_frame_reason=reason
                self._verify_failed=True  # ends display grace: strict TTL
                self._verify_failures=getattr(self,"_verify_failures",0)+1
                if self._verify_failures>=SEED_DROP_AFTER_FAILURES:
                    self.last_verified=None  # stale seed: full rescan
                    self.frame=None
        if self.frame is not None and not self._presentable(
                self.frame,hwnd):
            self.frame=None
        self._toast_hold_reason()
        now=time.monotonic()
        # V8.155: failed native fits must not monopolize the screenshot/UIA
        # worker. Retry at 0.25/0.5/1.0s, but a new source resets to 0.25s.
        retry_s=(.25 if self.frame is not None else
                 min(1.,.25*2**min(self._verify_failures,2)))
        if self.future is None and now-self.last_submit>retry_s:
            self.last_submit=now
            layout=getattr(self.hub.engine,"plot_layout",None)
            role_hint=((tuple(layout.phase),tuple(layout.mag))
                       if layout is not None else None)
            self.future=self.pool.submit(native_fir_frame,hwnd,
                self.source,float(self.hub.engine.graph_phase.y_max),
                self.last_verified,self._hint_color(),role_hint,
                (float(self.hub.engine.mag_smooth.currentData() or 0.),
                 float(self.hub.engine.phase_smooth.currentData() or 0.)))
        self._publish()

    def _toast_hold_reason(self):
        """V8.134: FIR made but not drawn for 2.5 s -> say why ON the plot."""
        src=self.source
        if src is None:
            return
        drawn=(self.frame is not None and
               (src.mode!="phase" or self.frame.phase_verified))
        if drawn or time.monotonic()-getattr(self,"_accepted_at",0.)<2.5:
            return
        reason=LAST_HOLD_REASON[0]
        if not reason:
            return
        key=(src.revision,reason)
        toasted=getattr(self,"_toasted",set())
        if key in toasted:
            return
        toasted.add(key)
        self._toasted=toasted
        print("V8134_FIR_HOLD_REASON",src.mode,reason,flush=True)
        engine=self.hub.engine
        graph=engine.graph_phase if src.mode=="phase" else engine.graph_mag
        try:
            from remix_duo.ui.widgets import show_notice
            show_notice(graph if graph.isVisible() else self.hub.fir,
                        "FIR chưa hiện: "+reason)
        except Exception as exc:
            print("V8134_TOAST_ERROR",exc,flush=True)

    def _hint_color(self):
        """V8.130: Data Bar icon colour of the approved FIR source trace."""
        try:
            token=self.hub.fir._approved[0]
            lookup=getattr(getattr(self.hub.engine,"observer",None),"trace_color",None)
            return lookup(token[0]) if callable(lookup) else None
        except Exception:
            return None

    def close(self):
        self.timer.stop()
        self.source=None
        self.frame=None
        self.last_verified=None
        bounded_shutdown(self.pool)
