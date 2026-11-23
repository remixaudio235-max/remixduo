"""Read-only bounded AX traversal. Unsupported custom Data Bar ticks stay unknown."""
import time
from .selection import TraceRow,checkbox_state,selection_from_rows

def attribute(element,name):
    import ApplicationServices as AX
    error,value=AX.AXUIElementCopyAttributeValue(element,name,None)
    return value if error==0 else None

def _rect(element):
    import ApplicationServices as AX
    frame=attribute(element,'AXFrame')
    if frame is not None:
        ok,value=AX.AXValueGetValue(frame,AX.kAXValueCGRectType,None)
        if ok:return (value.origin.x,value.origin.y,value.size.width,value.size.height)
    position,size=attribute(element,'AXPosition'),attribute(element,'AXSize')
    if position is None or size is None:return None
    ok,p=AX.AXValueGetValue(position,AX.kAXValueCGPointType,None)
    good,s=AX.AXValueGetValue(size,AX.kAXValueCGSizeType,None)
    return (p.x,p.y,s.width,s.height) if ok and good else None

def tree_snapshot(window,*,limit=4000,budget=.75):
    import ApplicationServices as AX
    if not AX.AXIsProcessTrusted():raise RuntimeError('HOLD: cần quyền Accessibility cho RemiX Duo')
    app=AX.AXUIElementCreateApplication(window.ref.pid)
    # Bound the time spent in any single remote accessibility message.
    AX.AXUIElementSetMessagingTimeout(app,.1)
    candidates=[]
    for candidate in attribute(app,'AXWindows') or []:
        rect=_rect(candidate)
        if rect and all(abs(a-b)<2 for a,b in zip(rect,window.rect)):
            candidates.append(candidate)
    if len(candidates)!=1:raise RuntimeError('HOLD: không ghép duy nhất AX window với CGWindow identity')
    started=time.monotonic();count=0;complete=True
    def visit(element):
        nonlocal count,complete
        if count>=limit or time.monotonic()-started>budget:
            complete=False;return None
        count+=1
        role=str(attribute(element,'AXRole') or '')
        value=attribute(element,'AXValue')
        if isinstance(value,(int,bool)):value=int(value)
        elif not isinstance(value,str):value=None
        node={'AXRole':role,'AXTitle':str(attribute(element,'AXTitle') or ''),
              'AXValue':value,'rect':_rect(element),'children':[]}
        for key in ('AXRowCount','AXVisibleChildren'):
            val=attribute(element,key)
            if val is not None:node[key]=int(val) if key=='AXRowCount' else len(val)
        for child in attribute(element,'AXChildren') or []:
            result=visit(child)
            if result is not None:node['children'].append(result)
            else:break
        return node
    root=visit(candidates[0])
    return {'root':root,'complete':complete,'nodes':count,'elapsed':time.monotonic()-started}

def read_selection(window):
    from .discovery import current_window
    before=current_window(window.ref)
    if before!=window or not window.on_screen or not (window.foreground or window.companion_foreground):
        raise RuntimeError('HOLD: Smaart không ở trước hoặc window identity thay đổi')
    observed=time.monotonic();snapshot=tree_snapshot(window)
    rows=[];counts=[]
    def walk(node):
        if node is None:return
        if node.get('AXRole')=='AXOutline' and 'AXRowCount' in node:counts.append(node['AXRowCount'])
        title=node.get('AXTitle','')
        if node.get('AXRole')=='AXCheckBox' and title.lower().endswith('.trf'):
            r=node.get('rect');x,y,w,h=window.rect
            visible=bool(r and r[2]>0 and r[3]>0 and r[0]>=x and r[1]>=y and
                         r[0]+r[2]<=x+w and r[1]+r[3]<=y+h)
            rows.append(TraceRow(title,checkbox_state(node),visible))
        for child in node.get('children',[]):walk(child)
    walk(snapshot['root'])
    total=counts[0] if len(counts)==1 and snapshot['complete'] else -1
    after=current_window(window.ref)
    if after!=before:raise RuntimeError('HOLD: Smaart di chuyển/thay cửa sổ khi quét AX')
    return selection_from_rows(window.ref,rows,total=total,observed_at=observed)
