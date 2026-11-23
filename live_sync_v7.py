"""Verified Windows 9.6.4 Data Bar tick synchronization.

Initial full read-only scan of 106 archived rows + subsequent visible page
checks from PrintWindow at ~5 Hz. All GUI actions read only except temporary
scroll during initial scan (restored). No Smaart audio, license or code changes.
Never extrapolate from unscanned rows; fail closed on ambiguity.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import time,win32gui
from full_scan_v7 import _uia,_page,full_scan,printwindow_image,ScanError
from uia_serial_v8152 import serialized_uia
from selection_v7 import archive_order,fresh_unindexed_imports
from win_databar_v7 import locate_smaart

INIT_RETRY_BACKOFF_S=(1.5,3.,6.,10.)


def _backoff_now():
    """Monotonic clock for the V8.108 full-scan retry backoff (test hook)."""
    return time.monotonic()

@dataclass(frozen=True)
class SyncResult:
    pair:tuple[str,str]|None
    status:str
    verified:int
    rows:int
    changed:bool
    captured_at:float
    active_names:tuple[str,...]|None=None
    ambiguous:int=0
    # V8.166: optional evidence supplied by the real native screenshot
    # reader. Legacy synthetic SyncResult fixtures remain compatible.
    source_id:tuple[int,str]|None=None
    frame_id:int|None=None
    observed_active_names:tuple[str,...]|None=None

class LiveDataBarV7:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.hwnd=0
        self.order=[]
        self.uia_rows={}
        self.states={}
        # V8.123: Smaart trace colour per file name, from Data Bar icons.
        self.colors_by_name={}
        self.row_seen_at={}
        self.header=None
        self.layout=None
        self.signature=None
        self.ready=False
        self.last_pair=None
        self.last_pos=None
        self.last_frame=None
        self.last_filecheck=0.
        self.last_scan=0.
        self.scan_count=0
        self.poll_count=0
        self.last_error=""
        # Separate 1-Trace gate: AutoPhase's 2-Trace guard remains untouched.
        self.single_tick=None
        self.single_candidate=None
        self.single_stable=0
        self.single_generation=0
        self.single_verified_at=0.
        self.single_scan_at=0.  # latest valid native Data Bar viewport
        # V8.108 full-scan retry backoff (see _reinitialize).
        self._init_failures=0
        self._init_fail_key=None
        self._init_retry_at=0.
        self._init_error=""
        self.row_pitch=22

    def _sig(self):
        order=archive_order(self.folder)
        return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in order)

    def clear(self,msg=""):
        self.hwnd=0
        self.order=[]
        self.uia_rows={}
        self.states={}
        self.colors_by_name={}
        self.row_seen_at={}
        self.header=None
        self.layout=None
        self.signature=None
        self.ready=False
        self.last_pair=None
        self.last_pos=None
        self.last_frame=None
        self.last_error=msg
        self.invalidate_single()

    def invalidate_single(self,clear_scan=True):
        """Drop one-tick lock immediately; preserve count only on valid scan."""
        if self.single_tick is not None or self.single_candidate is not None:
            self.single_generation+=1
        self.single_tick=None
        self.single_candidate=None
        self.single_stable=0
        self.single_verified_at=0.
        if clear_scan:self.single_scan_at=0.

    def suspend_single_transient(self):
        """Keep immutable file identity but require 3 new valid scans."""
        self.single_tick=None
        self.single_stable=0
        self.single_verified_at=0.
        self.single_scan_at=0.

    def observe_single(self,when,observed=None):
        """Record one *verified* full Data Bar state; commit only at stable 3/3.

        Same full scan/visible-page PrintWindow reader as AutoPhase.
        An invalid viewport never advances this counter.
        """
        # None means an explicitly complete observation (initial full scan
        # or a synthetic full-scan test). Poll must pass its visible indices.
        for index in self.states if observed is None else observed:
            if self.states.get(index) in ('on','off'):
                self.row_seen_at[index]=when
            else:self.row_seen_at.pop(index,None)
        if (not self.ready or len(self.order)==0 or
            len(self.states)!=len(self.order) or
            any(v not in ("on","off") for v in self.states.values())):
            self.invalidate_single()
            return
        # Native observation succeeded: show the actual enabled count even
        # when it is 0 or 6, but never allow EQ calculation without one.
        self.single_scan_at=when
        enabled=[i for i in range(len(self.order)) if self.states.get(i)=="on"]
        if len(enabled)!=1:
            self.invalidate_single(clear_scan=False)
            return
        # Three confirmations MUST observe the selected icon in each new
        # native frame. Cached checked state from another scroll page may
        # remain available for display, never for EQ/FIR export proof.
        if (observed is not None and enabled[0] not in observed):
            self.suspend_single_transient()
            return
        if (enabled[0] not in self.row_seen_at or
                not 0<=when-self.row_seen_at[enabled[0]]<=1.5):
            self.invalidate_single()
            return
        path=self.order[enabled[0]]
        try:
            stat=path.stat()
            candidate=(str(path),stat.st_mtime_ns,stat.st_size)
        except OSError:
            self.invalidate_single()
            return
        if candidate!=self.single_candidate:
            self.single_generation+=1
            self.single_candidate=candidate
            self.single_stable=1
            self.single_tick=None
        else:
            self.single_stable=min(3,self.single_stable+1)
        self.single_verified_at=when
        if self.single_stable>=3:
            self.single_tick=(*candidate,self.single_generation)

    def current_single(self):
        """Immutable (path,mtime,size,generation); only fresh 3/3 one-tick."""
        if (not self.ready or self.single_stable<3 or
            time.perf_counter()-self.single_verified_at>1.5):
            return None
        enabled=[i for i,state in self.states.items() if state=='on']
        if (len(self.states)!=len(self.order) or
                any(state not in ('on','off') for state in self.states.values()) or
                len(enabled)!=1 or not 0<=enabled[0]<len(self.order) or
                self.single_tick is None or
                not 0<=time.perf_counter()-self.row_seen_at.get(enabled[0],-1e30)<=1.5 or
                str(self.order[enabled[0]])!=self.single_tick[0]):
            return None
        return self.single_tick

    def _v8_map_epoch(self):
        """Detect index/file inventory edits around ONE Smaart 8 screenshot.

        No hashes or audio reads: this is a cheap metadata consistency
        witness for the Data Bar row-to-TRF mapping, not content identity.
        """
        index=self.folder.parent/"index.xml"
        stat=index.stat()
        inventory=tuple(sorted(p.name.casefold()
                               for p in self.folder.glob("*.trf")))
        return (stat.st_mtime_ns,stat.st_size,inventory)

    def _poll_v8(self,hwnd,now):
        """V8.121 read-only Smaart 8 tick map: pixel icons + index order."""
        from smaart8_databar_v8121 import v8_icon_color_rect,v8_row_states
        if self.ready and hwnd!=self.hwnd:
            # Never let a Smaart Suite map or prior Smaart 8 window
            # masquerade as proof for a newly selected process.
            self.clear("Smaart 8 HWND/edition changed")
        try:
            epoch_before=self._v8_map_epoch()
            order=archive_order(self.folder)
            image=printwindow_image(hwnd)
            host=win32gui.GetWindowRect(hwnd)
            import ctypes
            dpi=int(ctypes.windll.user32.GetDpiForWindow(hwnd))
            rows=v8_row_states(image,host,dpi=dpi)
            epoch_after=self._v8_map_epoch()
        except Exception as exc:
            self.suspend_single_transient();self.last_pair=None
            return SyncResult(None,"READ ERROR: Smaart 8 "+str(exc)[:120],
                              0,len(self.order),True,now,
                              source_id=(hwnd,str(self.folder)))
        if epoch_before!=epoch_after:
            # Files/index changed BETWEEN reading the row map and pixels:
            # a same-sized list could silently bind ticks to wrong TRFs.
            self.suspend_single_transient();self.last_pair=None
            return SyncResult(None,"Smaart 8 Data Bar HOLD: file/index "
                              "changed during native capture",
                              0,len(order),True,now,
                              source_id=(hwnd,str(self.folder)))
        if not order or len(rows)!=len(order):
            # A row scrolled out of view, a new capture not yet indexed or a
            # folder/state Duo cannot map: never guess which row is which.
            self.suspend_single_transient();self.last_pair=None
            return SyncResult(None,f"Smaart 8 Data Bar HOLD: {len(rows)} hàng / "
                              f"{len(order)} file — giữ mọi Trace trong vùng nhìn thấy",
                              0,len(order),True,now)
        states=[state for *_,state in rows]
        if any(state not in ("on","off") for state in states):
            self.suspend_single_transient();self.last_pair=None
            return SyncResult(None,"Visible tick ambiguous — keep checked rows visible and retry",
                              0,len(order),True,now,(),1)
        previous=(self.hwnd,list(self.order),dict(self.states))
        self.hwnd=hwnd;self.order=order;self.ready=True
        self.states=dict(enumerate(states))
        try:
            from selection_v7 import icon_color
            for name,(y0,y1,_state) in zip(order,rows):
                color=icon_color(image,v8_icon_color_rect(
                    dpi,y0,y1,host_top=host[1]))
                if color:self.colors_by_name[str(name)]=color
        except Exception:
            pass
        self.row_seen_at={i:now for i in self.states}
        self.poll_count+=1
        self.observe_single(now)
        pair=self._pair()
        changed=(previous!=(hwnd,list(order),self.states)) or pair!=self.last_pair
        self.last_pair=pair
        active=tuple(str(p) for p,s in zip(order,states) if s=="on")
        return SyncResult(pair,f"Verified viewport {len(rows)} rows; Smaart 8 pixel map, "
                          f"active {len(active)}",len(order),len(order),changed,now,active,0,
                          (hwnd,str(self.folder)),self.poll_count,active)

    def _reinitialize(self,hwnd,reason):
        """V8.108: full scroll scan with bounded retry backoff.

        A failed full scan (ambiguous tick under the mouse, row mismatch,
        tick changed mid-scan) used to be retried on EVERY 0.16 s poll,
        scrolling Smaart's Data Bar up/down continuously. Retry the SAME
        window/size only after 1.5/3/6/10 s; a different HWND or size retries
        at once. Fail closed: no pair while not initialized.
        """
        now=_backoff_now()
        try:
            l,t,r,b=win32gui.GetWindowRect(hwnd)
            key=(hwnd,r-l,b-t)
        except Exception:
            key=(hwnd,None,None)
        if key==self._init_fail_key and now<self._init_retry_at:
            self.clear(reason)
            return SyncResult(None,
                f"Data Bar HOLD: thử quét lại sau {self._init_retry_at-now:.1f}s"
                f" — {self._init_error[:110]}",0,0,False,time.perf_counter())
        self.clear(reason)
        try:
            result=self.initialize(hwnd)
        except Exception as exc:
            self._init_failures=(self._init_failures+1
                                 if key==self._init_fail_key else 1)
            delay=INIT_RETRY_BACKOFF_S[min(self._init_failures,
                                           len(INIT_RETRY_BACKOFF_S))-1]
            self._init_fail_key=key
            self._init_retry_at=now+delay
            self._init_error=str(exc)
            self.last_error=str(exc)
            self.invalidate_single()
            return SyncResult(None,"Data Bar HOLD: "+str(exc)[:140],
                              0,0,True,time.perf_counter())
        self._init_failures=0
        self._init_fail_key=None
        self._init_retry_at=0.
        self._init_error=""
        return result

    def initialize(self,hwnd):
        uia=_uia(hwnd)
        scan=full_scan(hwnd,self.folder,uia=uia)
        if scan.covered!=scan.total or len(scan.states)!=scan.total:
            raise ScanError("full scan incomplete, no pair accepted")
        root,bar,rows=uia
        order=archive_order(self.folder)
        if len(order)!=len(rows) or len(order)!=scan.total:
            raise ScanError("row count changed during initial scan")
        # Verify the one-to-one sorted names against visible labels separately
        # during platform calibration. Windows 9.6.4 verified the first 20.
        l,t,r,b=win32gui.GetWindowRect(hwnd)
        br=bar.rectangle()
        scroll=float(bar.iface_range_value.CurrentValue)
        anchor=rows[0].rectangle().top-t+scroll
        icon_left=rows[0].rectangle().left-l+7
        # Row pitch is only an index ESTIMATE for the visible-row walk;
        # classification always uses each row's own UIA rectangle.
        if len(rows)>=2:
            pitch=rows[1].rectangle().top-rows[0].rectangle().top
            self.row_pitch=max(12,min(40,pitch))
        self.hwnd=hwnd
        self.order=order
        self.imports_count=len(fresh_unindexed_imports(self.folder))
        self.uia_rows=rows
        self.states=dict(enumerate(scan.states))
        self.row_seen_at={i:time.perf_counter() for i in self.states}
        self.header=(bar,anchor,br.top-t,br.bottom-t,icon_left)
        self.layout=(r-l,b-t)
        self.signature=self._sig()
        self.ready=True
        self.last_pos=scroll
        self.last_scan=time.perf_counter()
        self.scan_count+=1
        self.poll_count+=1
        self.last_pair=self._pair()
        self.observe_single(time.perf_counter())
        active=tuple(str(self.order[i]) for i in range(len(self.order))
                     if self.states.get(i)=="on")
        ambiguous=sum(v not in ("on","off") for v in self.states.values())
        return SyncResult(self.last_pair,
            f"FULL SCAN {scan.covered}/{scan.total} in {scan.elapsed_s:.2f}s"
            + (f" | {self.imports_count} ASCII imports (index pending)"
               if self.imports_count else ""),
            scan.covered,scan.total,True,time.perf_counter(),
            active,ambiguous,
            (hwnd,str(self.folder)),self.poll_count,active)

    def _pair(self,observed=None):
        if (not self.ready or len(self.states)!=len(self.order) or
                any(v not in ('on','off') for v in self.states.values())):
            return None
        now=time.perf_counter()
        if any(not 0<=now-self.row_seen_at.get(i,-1e30)<=1.5
               for i,state in self.states.items() if state=='on'):
            return None
        enabled=[i for i in range(len(self.order))
                 if self.states.get(i)=="on"]
        if len(enabled)!=2:
            return None
        # Both checked icons must be witnessed in THIS frame when this is
        # a visible-page poll; a cached tick is not positive proof.
        if observed is not None and any(i not in observed for i in enabled):
            return None
        return tuple(str(self.order[i]) for i in enabled)

    def trace_color(self,name):
        """V8.123: '#RRGGBB' of a trace as drawn by Smaart, or None."""
        return self.colors_by_name.get(str(name))

    @serialized_uia
    def poll(self,hwnd=None):
        now=time.perf_counter()
        # A minimized Smaart HWND has an artificial (-32000,-32000) rect.
        # Never feed it into PrintWindow, full scan, or Smaart 8 pixel rows.
        # Keep previous display candidate only; no Solve/Export proof.
        if hwnd is not None and win32gui.IsIconic(hwnd):
            self.suspend_single_transient()
            self.last_pair=None
            return SyncResult(None,"Smaart viewport unavailable: minimized",
                              0,len(self.order),True,now,
                              source_id=(hwnd,str(self.folder)))
        if hwnd is not None:
            from smaart8_api3_readonly_v868 import process_smaart_major
            if process_smaart_major(hwnd)==8:
                # V8.121: Smaart 8 has no UIA tree and API V3 cannot report
                # ticks; read its Data Bar icons from pixels (never scroll).
                return self._poll_v8(hwnd,now)
        if hwnd is None:
            target=locate_smaart()
            if target is None:
                self.invalidate_single()
                return SyncResult(None,"Smaart not visible",0,len(self.order),
                                  bool(self.last_pair),now)
            hwnd=target.hwnd
        if not self.ready or hwnd!=self.hwnd:
            return self._reinitialize(hwnd,"Smaart HWND changed")
        rect=win32gui.GetWindowRect(hwnd)
        if (rect[2]-rect[0],rect[3]-rect[1])!=self.layout:
            return self._reinitialize(hwnd,"Smaart window resized; recalibrate")
        if now-self.last_filecheck>1.:
            self.last_filecheck=now
            if self._sig()!=self.signature:
                return self._reinitialize(
                    hwnd,"Session Data changed; list mapping invalidated")
        bar,anchor,top,bottom,left=self.header
        try:
            offset0=float(bar.iface_range_value.CurrentValue)
            image=printwindow_image(hwnd)
            offset1=float(bar.iface_range_value.CurrentValue)
            if abs(offset0-offset1)>.5:
                self.suspend_single_transient()
                # Scroll happened during screenshot — keep prior state, but
                # never emit a pair based on an inconsistent page.
                self.last_pair=None
                return SyncResult(None,"Scroll changed during capture; unverified",
                                  0,len(self.order),True,now)
            colors={}
            rows=_page(image,self.order,offset1,anchor,top,bottom,left,
                       getattr(self,"row_pitch",22),
                       uia_rows=self.uia_rows,window_origin=(rect[0],rect[1]),
                       colors=colors)
            for index,color in colors.items():
                if 0<=index<len(self.order):
                    self.colors_by_name[str(self.order[index])]=color
            if not rows:
                self.suspend_single_transient()
                self.last_pair=None
                return SyncResult(None,"No unambiguous rows in viewport",
                                  0,len(self.order),True,now)
            # A cached checked row which is no longer in this capture is NOT
            # a fresh tick witness. Mark it unknown, never renew it through
            # repeated captures of unrelated rows. Returning to view can
            # resolve it on/off again; no automatic live scrolling is added.
            hidden_active=[i for i,state in self.states.items()
                           if state=='on' and i not in rows]
            for index in hidden_active:
                self.states[index]='unknown'
                self.row_seen_at.pop(index,None)
            if any(state not in ('on','off') for state in rows.values()):
                for index,state in rows.items():
                    self.states[index]=state
                self.suspend_single_transient()
                self.last_pair=None
                return SyncResult(None,"Visible tick ambiguous — keep checked rows visible and retry",
                                  0,len(self.order),True,now,(),1)
            changed=bool(hidden_active)
            for i,state in rows.items():
                old=self.states.get(i)
                if old!=state:
                    self.states[i]=state
                    changed=True
            self.poll_count+=1
            self.observe_single(now,observed=rows)
            pair=self._pair(observed=rows) if len(self.states)==len(self.order) else None
            if pair!=self.last_pair:changed=True
            self.last_pair=pair
            self.last_pos=offset1
            text=(f"Verified viewport {len(rows)} rows; "
                  f"cached {len(self.states)}/{len(self.order)} rows, "
                  f"active {sum(1 for x in self.states.values() if x=='on')}")
            if getattr(self,"imports_count",0):
                text+=f" | {self.imports_count} ASCII imports (index pending)"
            active=tuple(str(self.order[i]) for i in range(len(self.order))
                         if self.states.get(i)=="on")
            ambiguous=sum(v not in ("on","off") for v in self.states.values())
            if ambiguous:
                text="Tick chưa xác minh: giữ mọi Trace được tick trong vùng nhìn thấy. "+text
            observed_active=tuple(str(self.order[i]) for i in rows
                                  if self.states.get(i)=="on")
            return SyncResult(pair,text,len(self.states),len(self.order),
                              changed,now,active,ambiguous,
                              (hwnd,str(self.folder)),self.poll_count,
                              observed_active)
        except Exception as exc:
            self.suspend_single_transient()
            self.last_error=str(exc)
            self.last_pair=None
            return SyncResult(None,"READ ERROR: "+str(exc)[:145],
                              0,len(self.order),True,now)
