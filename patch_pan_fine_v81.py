from pathlib import Path
p=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_1_HYBRID_PHASE_Y_QA\native_fast_pan_v81.py')
s=p.read_text(encoding='utf-8')
start=s.index('def colored_profiles(image):')
end=s.index('\nclass NativeFastPan:',start)
replacement='''def colored_profiles(image):
    pix=np.asarray(image.convert("RGB"),dtype=np.uint8)
    r,g,b=(pix[:,:,j].astype(np.int16) for j in range(3))
    native=((b>75)&(b>r*1.45)&(b>g*.68)) | (
             (r>95)&(r>g*1.2)&(r>b*.85)&(g>30))
    native[:8]=False
    native[-3:]=False
    mid=native.shape[1]//2
    # Downsample horizontal pixels only. Preserve 1px vertical precision.
    masks=(native[:,:mid:3],native[:,mid::3])
    profiles=tuple(z.sum(axis=1).astype(float) for z in masks)
    return (profiles,masks),int(native.sum())

def best_vertical_shift(before,after,limit=90):
    """C-vectorized zero-mean cross-correlation, not ~200 Python loops."""
    a=np.asarray(before,dtype=float)
    b=np.asarray(after,dtype=float)
    if a.shape!=b.shape or a.ndim!=1 or len(a)<150:
        return None,0.
    n=len(a)
    a=a-a.mean()
    b=b-b.mean()
    corr=np.correlate(b,a,mode="full")
    steps=np.arange(-min(limit,n//3),min(limit,n//3)+1)
    idx=n-1+steps
    asq=np.r_[0,np.cumsum(a*a)]
    bsq=np.r_[0,np.cumsum(b*b)]
    al=np.where(steps>=0,0,-steps)
    ar=np.where(steps>=0,n-steps,n)
    bl=np.where(steps>=0,steps,0)
    br=np.where(steps>=0,n,n+steps)
    denom=np.sqrt(np.maximum((asq[ar]-asq[al])*(bsq[br]-bsq[bl]),1e-12))
    q=corr[idx]/denom
    i=int(np.argmax(q))
    return int(steps[i]),float(q[i])

def _pixel_score(a,b,dy):
    h=a.shape[0]
    if dy>0:
        x=a[:h-dy];y=b[dy:]
    elif dy<0:
        x=a[-dy:];y=b[:h+dy]
    else:
        x=a;y=b
    aa=int(x.sum());bb=int(y.sum())
    if aa<20 or bb<20:return 0.
    return float(np.count_nonzero(x&y)/np.sqrt(aa*bb))

def infer_pan(prev,current):
    if prev is None or current is None:
        return PanFrame(0.,0.,False,"No baseline",0.,time.monotonic())
    before_profiles,before_masks=prev
    after_profiles,after_masks=current
    shifts=[]
    for pa,pb,a,b in zip(before_profiles,after_profiles,
                         before_masks,after_masks):
        coarse,_=best_vertical_shift(pa,pb)
        if coarse is None:
            return PanFrame(0.,0.,False,"Invalid row signature",0.,time.monotonic())
        # Coarse candidate + fine 2D matching recovers 1-4px motion even
        # when row-density correlation is too broad or ambiguous.
        candidates=set(range(max(-89,coarse-8),min(89,coarse+8)+1))
        candidates.update(range(-8,9))
        scored=[(_pixel_score(a,b,k),k) for k in candidates]
        best,dy=max(scored)
        zero=_pixel_score(a,b,0)
        if best<.42 or (abs(dy)>0 and best-zero<.055):
            return PanFrame(0.,best,False,"Native pixel movement ambiguous",
                            0.,time.monotonic())
        shifts.append((dy,best))
    if abs(shifts[0][0]-shifts[1][0])>2:
        return PanFrame(0.,min(x[1] for x in shifts),False,
                        "Independent native regions disagree",0.,time.monotonic())
    return PanFrame(float(round(sum(z[0] for z in shifts)/2)),
                    min(z[1] for z in shifts),True,"Native pixel pan",
                    0.,time.monotonic())
'''
s=s[:start]+replacement+s[end:]
p.write_text(s,encoding='utf-8')
t=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_1_HYBRID_PHASE_Y_QA\qa_native_pan_v81.py')
q=t.read_text(encoding='utf-8').replace('a,n=colored_profiles(Image.fromarray(roi))','a,n=colored_profiles(Image.fromarray(roi))')
t.write_text(q,encoding='utf-8')
print("V81_VECTORIZED_1D_COARSE_AND_2D_FINE_PATCHED")
