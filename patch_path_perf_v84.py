from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_4_SUM_CONTINUITY_QA\overlay_v7.py')
s=p.read_text(encoding='utf-8')
a=s.index('        paths={"high":QPainterPath(),"low":QPainterPath()}\n        for edge in geometry.edges:')
b=s.index('        self._last_points=len(geometry.edges)',a)
replacement='''        paths={"high":QPainterPath(),"low":QPainterPath()}
        # Merge consecutive edges of equal confidence into a single
        # QPainterPath subpath. Hundreds of moveTo+lineTo pairs can make Qt
        # software antialiasing 5-10x slower than real continuous polylines.
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
        self._last_subpaths=subpath_count
'''
s=s[:a]+replacement+s[b:]
p.write_text(s,encoding='utf-8')
print('V84_MERGED_CONTIGUOUS_QPAINTERPATH')
