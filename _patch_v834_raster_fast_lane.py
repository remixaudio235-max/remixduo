"""V8.34 cached transparent trace bitmap: constant-time Y translation."""
from pathlib import Path
p=Path(__file__).with_name('overlay_v7.py')
s=p.read_text(encoding='utf-8')
def sub(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Raster patch mismatch: '+old[:100])
 s=s.replace(old,new,1)
sub('from PyQt6.QtGui import QColor,QPen,QPainter,QPainterPath',
    'from PyQt6.QtGui import QColor,QPen,QPainter,QPainterPath,QPixmap')
sub('        cached={"key":key,"paths":paths,"anchor_top":self.y_max,\n'
    '                "origin_shift":origin_shift,"geometry":geometry,\n'
    '                "subpath_count":subpath_count}\n',
    '        # Cache already-antialiased trace as a transparent bitmap.\n'
    '        # The following Y-only pan paints 1-2 pixmaps rather than\n'
    '        # stroking 4000+ QPainterPath segments at every 16ms tick.\n'
    '        surface=QPixmap(int(width),int(build_h))\n'
    '        surface.fill(Qt.GlobalColor.transparent)\n'
    '        raster=QPainter(surface)\n'
    '        for quality in ("low","high"):\n'
    '            raster.setRenderHint(QPainter.RenderHint.Antialiasing,\n'
    '                                 quality=="high")\n'
    '            color=QColor("#39FF14")\n'
    '            if quality=="low":color.setAlpha(128)\n'
    '            raster.setPen(QPen(color,2.0 if quality=="low" else 3.5,\n'
    '                             Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,\n'
    '                             Qt.PenJoinStyle.RoundJoin))\n'
    '            raster.drawPath(paths[quality])\n'
    '        raster.end()\n'
    '        cached={"key":key,"paths":paths,"anchor_top":self.y_max,\n'
    '                "origin_shift":origin_shift,"geometry":geometry,\n'
    '                "subpath_count":subpath_count,"trace_bitmap":surface}\n')
beg=s.index('        painter.setClipRect(QRectF(0.,0.,float(w),float(h)))\n'
            '        for quality in ("low","high"):',s.index('        cached,shifts=self._viewport_paths('))
end=s.index('        painter.setClipping(False)\n        painter.setPen(base)',beg)
old=s[beg:end]
new='''        painter.setClipRect(QRectF(0.,0.,float(w),float(h)))
        bitmap=cached["trace_bitmap"]
        for shift in shifts:
            painter.drawPixmap(0,int(round(float(shift))),bitmap)
'''
if 'painter.drawPath(cached["paths"][quality])' not in old:
 raise RuntimeError('Expected cached path paint block not found')
s=s[:beg]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('V834_RASTER_FAST_LANE_APPLIED',p)
