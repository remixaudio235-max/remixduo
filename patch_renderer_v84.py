from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_4_SUM_CONTINUITY_QA\overlay_v7.py')
s=p.read_text(encoding="utf-8")
needle='from mag_ref_anchor_v83 import capture_mag_ref,MagAnchor'
assert s.count(needle)==1
s=s.replace(needle,needle+'\nfrom sum_render_v84 import make_geometry')
s=s.replace('RemiX Auto Align V8.3 - Windows QA','RemiX Auto Align V8.4 - Windows QA')
s=s.replace('RemiX  AUTO ALIGN  V8.3','RemiX  AUTO ALIGN  V8.4')
start=s.index('        base=QColor("#39FF14") # Green neon SUM Mag and SUM Phase')
end=s.index('        painter.setPen(base)',start)
new='''        base=QColor("#39FF14")
        values=(d.mag_db+self.display_offset_db) if self.kind=="mag" else d.phase_deg
        # Confidence ONLY changes opacity. Preserve physical SUM in weak
        # coherence and phase-smoothing cancellation regions rather than
        # dropping the whole line. Missing/nonfinite source data is not joined.
        trusted=np.asarray(d.valid,dtype=bool)
        if self.kind=="phase" and d.phase_valid is not None:
            trusted=trusted & np.asarray(d.phase_valid,dtype=bool)
        geometry=make_geometry(d.hz,values,trusted,
                               self.f_min,self.f_max,
                               self.y_min,self.y_max,w,h,self.kind)
        paths={"high":QPainterPath(),"low":QPainterPath()}
        for edge in geometry.edges:
            path=paths[edge.quality]
            path.moveTo(edge.x0,edge.y0)
            path.lineTo(edge.x1,edge.y1)
        self._last_points=len(geometry.edges)
        self._last_segments=geometry.wrap_splits+geometry.data_gaps
        self._last_low_coh=geometry.low_edges
        self._last_clipped=geometry.clipped_edges
        self._last_wraps=geometry.wrap_splits
        # Draw both types solid so there are no false visual gaps: weak
        # regions are thinner/translucent and retain their honest uncertainty.
        painter.setClipRect(QRectF(0.,0.,float(w),float(h)))
        for quality in ("low","high"):
            color=QColor(base)
            if quality=="low":color.setAlpha(128)
            painter.setPen(QPen(color,2.0 if quality=="low" else 3.5,
                                Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(paths[quality])
        painter.setClipping(False)
'''
s=s[:start]+new+s[end:]
p.write_text(s,encoding="utf-8")
print("V84_DISCONTINUITY_RENDER_PATCHED")
