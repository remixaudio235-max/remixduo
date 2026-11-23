"""Screen-only ScreenCaptureKit screenshots (macOS14+). No audio stream."""
import threading
import time
from ..contracts import CapturedFrame

class CaptureResult:
    def __init__(self):
        self.event=threading.Event();self.lock=threading.Lock()
        self.value=None;self.error=None;self.cancelled=False
    def finish(self,value,error):
        with self.lock:
            if self.cancelled or self.event.is_set():return
            self.value,self.error=value,error
            self.event.set()
    def cancel(self):
        with self.lock:self.cancelled=True;self.event.set()
    def wait(self,timeout):
        if threading.current_thread() is threading.main_thread():
            import Foundation
            deadline=time.monotonic()+timeout
            while not self.event.is_set() and time.monotonic()<deadline:
                Foundation.NSRunLoop.currentRunLoop().runUntilDate_(Foundation.NSDate.dateWithTimeIntervalSinceNow_(.01))
        else:self.event.wait(timeout)
        if not self.event.is_set():
            self.cancel();raise TimeoutError('HOLD: ScreenCaptureKit timeout')
        if self.error is not None:raise RuntimeError('HOLD: ScreenCaptureKit '+str(self.error))
        if self.value is None:raise RuntimeError('HOLD: ScreenCaptureKit không trả frame')
        return self.value

def configure_capture(config,window):
    config.setCapturesAudio_(False)
    config.setShowsCursor_(False)
    config.setIgnoreShadowsSingleWindow_(True)
    config.setScalesToFit_(True)
    config.setPreservesAspectRatio_(False)
    width,height=round(window.rect[2]),round(window.rect[3])
    config.setWidth_(width);config.setHeight_(height)
    config.setSourceRect_(((0.,0.),(float(window.rect[2]),float(window.rect[3]))))
    config.setDestinationRect_(((0.,0.),(float(width),float(height))))

def capture_window(window,timeout=2.):
    import AppKit
    import ScreenCaptureKit as SCK
    from .permissions import status
    from .discovery import current_window
    if not status()['screen_capture']:raise RuntimeError('HOLD: cần quyền Screen Recording')
    if not hasattr(SCK,'SCScreenshotManager'):
        raise RuntimeError('HOLD: native screenshot adapter cần macOS14+; macOS13 dùng offline workspace')
    if current_window(window.ref)!=window or not window.on_screen or not (window.foreground or window.companion_foreground):
        raise RuntimeError('HOLD: cửa sổ Smaart thay đổi/trở nền')
    deadline=time.monotonic()+timeout
    content=CaptureResult()
    SCK.SCShareableContent.getShareableContentWithCompletionHandler_(content.finish)
    result=content.wait(max(.01,deadline-time.monotonic()))
    candidates=[w for w in result.windows() if str(w.windowID())==window.ref.opaque_id
                and int(w.owningApplication().processID())==window.ref.pid]
    if len(candidates)!=1:raise RuntimeError('HOLD: ScreenCaptureKit không có đúng window identity')
    filter_=SCK.SCContentFilter.alloc().initWithDesktopIndependentWindow_(candidates[0])
    config=SCK.SCStreamConfiguration.alloc().init()
    # Explicit crop/destination prevents implicit letterboxing and shadow offsets.
    configure_capture(config,window)
    image=CaptureResult();started=time.monotonic()
    SCK.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(filter_,config,image.finish)
    cgimage=image.wait(max(.01,deadline-time.monotonic()))
    bitmap=AppKit.NSBitmapImageRep.alloc().initWithCGImage_(cgimage)
    data=bitmap.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG,{})
    if data is None:raise RuntimeError('HOLD: không encode được frame PNG')
    frame=CapturedFrame(window,bytes(data),int(bitmap.pixelsWide()),int(bitmap.pixelsHigh()),started)
    current=current_window(window.ref)
    if not frame.valid_for(current,time.monotonic()):raise RuntimeError('HOLD: frame cũ/geometry đổi')
    return frame
