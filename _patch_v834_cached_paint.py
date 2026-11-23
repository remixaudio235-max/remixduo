"""V8.34 viewport-path caching: phase wrap periodic tiling, Mag extended axis."""
from pathlib import Path
p=Path(__file__).with_name('overlay_v7.py')
s=p.read_text(encoding='utf-8')
def sub(old,new):
    global s
    n=s.count(old)
    if n!=1:raise RuntimeError(f"V834 unsafe cached paint patch: {n} of {old[:80]!r}")
    s=s.replace(old,new,1)
sub('        self.draw_count=0\n'
    '        self.display_offset_db=0.0',
    '        self.draw_count=0\n'
    '        self._paint_cache=None\n'
    '        self._cache_rebuilds=0\n'
    '        self.display_offset_db=0.0')
sub('    def set_data(self,value:SumTrace|None):\n'
    '        self.data=value\n'
    '        self.update()',
    '    def set_data(self,value:SumTrace|None):\n'
    '        self.data=value\n'
    '        self._paint_cache=None\n'
    '        self.update()')
anchor='    def showEvent(self,event):\n'
if s.count(anchor)!=1:raise RuntimeError('Missing SumGraph showEvent')
fn='''    def _viewport_paths(self,data,width,height,values,trusted):
        """Build native SUM topology only when TF, zoom/span or size changes.

        Magnitude: prepare a broad 7-height vertical canvas once and
        translate it over the current Y viewport. Phase (360-degree
        wrap): prepare exactly one wrapped period and tile the SAME
        segments at 2 offsets. This preserves proper split-at-wrap paths
        without a full Python 4096-edge rebuild per 16ms pointer move.
        """
        span=float(self.y_max-self.y_min)
        if span<=0:return None,()
        periodic=(self.kind=="phase" and 350.<=span<=370.)
        key=(id(data),self.kind,int(width),int(height),
             round(self.f_min,7),round(self.f_max,7),
             round(self.display_offset_db,7),round(span,7),periodic)
        cached=self._paint_cache
        if cached is not None and cached["key"]==key:
            delta=(self.y_max-cached["anchor_top"])*height/span
            if periodic:
                y_shift=delta%height
                return cached,(y_shift-height,y_shift)
            if abs(delta)<=2.7*height:
                return cached,(cached["origin_shift"]+delta,)
        if periodic:
            y_lo,y_hi=self.y_min,self.y_max
            build_h=height
            origin_shift=0
        else:
            y_lo=self.y_min-3.*span
            y_hi=self.y_max+3.*span
            build_h=7*height
            origin_shift=-3*height
        geometry=make_geometry(data.hz,values,trusted,
                               self.f_min,self.f_max,
                               y_lo,y_hi,width,build_h,self.kind)
        paths={"high":QPainterPath(),"low":QPainterPath()}
        last_end={"high":None,"low":None}
        subpath_count=0
        for edge in geometry.edges:
            path=paths[edge.quality]
            previous=last_end[edge.quality]
            if (previous is None or
                abs(previous[0]-edge.x0)>1e-4 or
                abs(previous[1]-edge.y0)>1e-4):
                path.moveTo(edge.x0,edge.y0)
                subpath_count+=1
            path.lineTo(edge.x1,edge.y1)
            last_end[edge.quality]=(edge.x1,edge.y1)
        cached={"key":key,"paths":paths,"anchor_top":self.y_max,
                "origin_shift":origin_shift,"geometry":geometry,
                "subpath_count":subpath_count}
        self._paint_cache=cached
        self._cache_rebuilds+=1
        return cached,((origin_shift,) if not periodic
                       else (-height,0))

'''
s=s.replace(anchor,fn+anchor,1)
beg=s.index('        geometry=make_geometry(d.hz,values,trusted,')
end=s.index('        painter.setClipping(False)\n        painter.setPen(base)',beg)
original=s[beg:end]
if 'for quality in ("low","high"):' not in original:raise RuntimeError('Paint block anchor wrong')
replace='''        cached,shifts=self._viewport_paths(d,w,h,values,trusted)
        if cached is None:
            painter.end()
            return
        geometry=cached["geometry"]
        self._last_subpaths=cached["subpath_count"]
        self._last_points=len(geometry.edges)
        self._last_segments=geometry.wrap_splits+geometry.data_gaps
        self._last_low_coh=geometry.low_edges
        self._last_clipped=geometry.clipped_edges
        self._last_wraps=geometry.wrap_splits
        painter.setClipRect(QRectF(0.,0.,float(w),float(h)))
        for quality in ("low","high"):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing,
                                  quality=="high")
            color=QColor(base)
            if quality=="low":color.setAlpha(128)
            painter.setPen(QPen(color,2.0 if quality=="low" else 3.5,
                                Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            for shift in shifts:
                painter.save()
                painter.translate(0.,float(shift))
                painter.drawPath(cached["paths"][quality])
                painter.restore()
'''
s=s[:beg]+replace+s[end:]
p.write_text(s,encoding='utf-8')
print('V834_CACHED_PAINT_APPLIED',p,'OLD_BLOCK_LINES',len(original.splitlines()))
