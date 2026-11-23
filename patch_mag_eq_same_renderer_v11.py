# -*- coding: utf-8 -*-
"""V11: draw MagEq with SAME transparent QWidget renderer as AutoPhase SUM.

This removes the second top-level MagEq drawing window entirely; the
noninteractive native fit worker stays, but passes data to graph_mag's paint.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=ROOT/"overlay_v7.py"
s=p.read_text(encoding="utf-8")
def change(old,new):
 global s
 if old not in s:raise RuntimeError("Overlay template shifted: "+old[:80])
 s=s.replace(old,new,1)

change('''        self.data:SumTrace|None=None
        self.label=f"SUM {kind.upper()} (MODEL - Y do RemiX chon)"''',
'''        self.data:SumTrace|None=None
        self.mageq_source=None
        self.mageq_frame=None
        self.mageq_draw_count=0
        self.label=f"SUM {kind.upper()} (MODEL - Y do RemiX chon)"''')
change('''    def showEvent(self,event):
        super().showEvent(event)
        hwnd=int(self.winId())''',
'''    def set_mageq(self,source=None,frame=None):
        """One MagEq on native Magnitude; SUM state remains intact."""
        if self.kind!="mag":return
        if source is None or frame is None or frame.revision!=source.revision:
            source=frame=None
        self.mageq_source=source
        self.mageq_frame=frame
        self.update()

    def _paint_mageq(self,p):
        from smaart_native_mag_fit import native_points
        src,frame=self.mageq_source,self.mageq_frame
        if src is None or frame is None:return
        rect=frame.plot
        if self.geometry().getRect()!=rect:return
        x,y,w,h=rect
        pts,valid=native_points(rect,frame.fit,src.freqs,src.after_db,src.coh)
        if len(pts)<2:return
        pts[:,0]-=x;pts[:,1]-=y
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        p.setClipRect(QRectF(0.,0.,float(w),float(h)))
        for trusted in (False,True):
            line=QPainterPath()
            previous=None
            for (xx,yy),good in zip(pts,valid):
                xx=float(xx);yy=float(yy)
                if bool(good)!=trusted or not(np.isfinite(xx) and np.isfinite(yy)):
                    previous=None
                    continue
                if previous is None or xx-previous>23:
                    line.moveTo(xx,yy)
                else:line.lineTo(xx,yy)
                previous=xx
            color=QColor("#FFC970")
            if not trusted:color.setAlpha(115)
            p.setPen(QPen(color,1.4 if not trusted else 3.0,
                Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin))
            p.drawPath(line)
        p.setClipping(False)
        p.setPen(QColor("#FFE0A7"))
        p.drawText(100,22,
             f"MagEq [{src.source_name}]  {len(src.peqs)} PEQ"
             f"  | native REF {frame.fit.score:.0%}  | KHONG GHI DSP")
        self.mageq_draw_count+=1

    def showEvent(self,event):
        super().showEvent(event)
        hwnd=int(self.winId())''')
change('''    def paintEvent(self,event):
        self.draw_count+=1
        if self.data is None:return''',
'''    def paintEvent(self,event):
        self.draw_count+=1
        if self.kind=="mag" and self.mageq_source is not None:
            painter=QPainter(self)
            self._paint_mageq(painter)
            painter.end()
            return
        if self.data is None:return''')
change('''        has=(self.current_sum is not None and self.overlay_positioned and
             (not self.managed_mode or self.ui_tool_enabled))
        self.graph_mag.setVisible(bool(has))
        self.graph_phase.setVisible(bool(has))''',
'''        has=(self.current_sum is not None and self.overlay_positioned and
             (not self.managed_mode or self.ui_tool_enabled))
        eq_active=(self.managed_mode and not self.ui_tool_enabled and
                   self.graph_mag.mageq_source is not None and
                   self.graph_mag.mageq_frame is not None)
        # One original native Smaart Mag plus exactly ONE RemiX model line.
        self.graph_mag.setVisible(bool(has or eq_active))
        self.graph_phase.setVisible(bool(has))''')
p.write_text(s,encoding="utf-8")

p=ROOT/"native_eq_mag_v06.py"
s=p.read_text(encoding="utf-8")
def edit(a,b):
 global s
 if a not in s:raise RuntimeError("Calibration template shifted: "+a[:80])
 s=s.replace(a,b,1)
edit('''    def clear(self):
        self.revision+=1
        self.source=None
        self.frame=None
        self.hide()
        self.update()''',
'''    def clear(self):
        self.revision+=1
        self.source=None
        self.frame=None
        self._sync_sum_renderer()
        self.hide()
        self.update()

    def _sync_sum_renderer(self):
        """Drive original AutoPhase Mag QWidget; never show a second window."""
        graph=self.hub.engine.graph_mag
        active=(self.source is not None and self.frame is not None and
                self.enabled and self.hub.active=="eq" and
                self.hub.isVisible())
        if active:
            if graph.geometry().getRect()!=self.frame.plot:
                graph.setGeometry(*self.frame.plot)
            graph.set_mageq(self.source,self.frame)
        else:
            graph.set_mageq()
        self.hub.engine.refresh_visibility()''')
edit('''    def set_enabled(self,enabled):
        self.enabled=bool(enabled)
        if not self.enabled:self.hide()
        self.update()''',
'''    def set_enabled(self,enabled):
        self.enabled=bool(enabled)
        self._sync_sum_renderer()
        self.hide()
        self.update()''')
edit('''        if (source is None or not self.enabled or
                self.hub.active!="eq" or not self.hub.isVisible()):
            if self.isVisible():self.hide()
            return''',
'''        if (source is None or not self.enabled or
                self.hub.active!="eq" or not self.hub.isVisible()):
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return''')
edit('''        if not hwnd or not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            if self.isVisible():self.hide()
            return''',
'''        if not hwnd or not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return''')
edit('''        if active_pid not in (smaart_pid,os.getpid()) or not active_pid:
            if self.isVisible():self.hide()
            return''',
'''        if active_pid not in (smaart_pid,os.getpid()) or not active_pid:
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return''')
edit('''        if frame is None:
            if self.isVisible():self.hide()
            return''',
'''        if frame is None:
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return''')
edit('''        if w<900 or h<240:
            if self.isVisible():self.hide()
            return
        if self.geometry().getRect()!=(x,y,w,h):self.setGeometry(x,y,w,h)
        if not self.isVisible():self.show()
        self.update()''',
'''        if w<900 or h<240:
            self._sync_sum_renderer()
            if self.isVisible():self.hide()
            return
        # Single model renderer: no .show() here. Render in engine.graph_mag.
        self._sync_sum_renderer()
        if self.isVisible():self.hide()''')
p.write_text(s,encoding="utf-8")
# GUI's active page switch must clear stale MagEq from SUM renderer instantly.
p=ROOT/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8")
needle='''        if mode!="eq":self.native_eq.hide()
        self.engine.ui_tool_enabled=(mode=="phase")'''
replacement='''        if mode!="eq":
            self.native_eq.hide()
            self.engine.graph_mag.set_mageq()
        self.engine.ui_tool_enabled=(mode=="phase")'''
if needle not in s:raise RuntimeError("GUI template shifted")
s=s.replace(needle,replacement,1)
s=s.replace('''        self.setWindowTitle("RemiX Signal V8.18 + MagEq V10 QA")''',
            '''        self.setWindowTitle("RemiX Signal V8.19 | MagEq embedded V11 QA")''',1)
p.write_text(s,encoding="utf-8")
print("EMBEDDED_MAG_EQ_IN_EXISTING_SUM_GRAPH_ONLY; NO_SECOND_EQ_WINDOW")
