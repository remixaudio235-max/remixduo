"""V18 QA log only: inspect Qt model state without changing Smaart."""
from pathlib import Path
import time
import win32gui,win32process
LOG=Path(__file__).resolve().parent/"QA_V18_RUNTIME_GATE.log"
_last=0.
def record(widget):
    global _last
    now=time.monotonic()
    if now-_last<1.8:return
    _last=now
    hub=widget.hub
    eng=hub.engine
    observer=getattr(eng,"observer",None)
    tick=getattr(observer,"current_single",lambda:None)()
    eq=hub.eq
    accepted=getattr(eq,"_single_token",None)
    frame=widget.frame
    front=win32gui.GetForegroundWindow()
    frontpid=win32process.GetWindowThreadProcessId(front)[1] if front else -1
    graph=eng.graph_mag
    fields=dict(
        source=bool(widget.source),
        source_name=(widget.source.source_name if widget.source else "-"),
        frame=bool(frame),future=bool(widget.future),
        future_done=(widget.future.done() if widget.future else False),
        frame_age=(round(now-frame.created,2) if frame else None),
        frame_score=(round(frame.fit.score,3) if frame else None),
        fit_color=(frame.color if frame else None),
        single=(tick[0] if tick else "-"),
        accepted=(accepted[0] if accepted else "-"),
        safe=hub._eq_tick_safe(),
        eq_ready=(bool(eq.result and eq.result.status=="PREVIEW_READY")),
        visible=widget.isVisible(),hub_visible=hub.isVisible(),
        workspace=hub.workspace_visible,active=hub.active,
        overlay_mode=eng.overlay_tool_mode,
        engine_workspace=eng.overlay_workspace_visible,
        eq_enabled=widget.enabled,
        graph=graph.isVisible(),graph_source=bool(graph.mageq_source),
        graph_frame=bool(graph.mageq_frame),
        last_native_drop=getattr(widget,"last_native_drop",""),
        graph_rect=graph.geometry().getRect(),
        foreground_pid=frontpid,
        native_tick_lag=(round(time.perf_counter()-observer.single_verified_at,2) if observer and hasattr(observer,"single_verified_at") else None),
        native_stable=(observer.single_stable if observer and hasattr(observer,"single_stable") else None),
    )
    with LOG.open("a",encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {fields}\n")
