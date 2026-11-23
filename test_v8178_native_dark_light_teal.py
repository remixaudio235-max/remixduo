"""P0 regression Smaart8 genuine Dark + Light native source identity.

Evidence: Smaart8 8.177 real dark/light PrintWindow screenshots captured
before change, source TRF pair names matched 3/3 native ticks.
Never accepts screenshot alone as proof for current runtime HWND/ticks.
"""
from pathlib import Path
from PIL import Image
import numpy as np
from smaart_native_mag_fit import NativeMagFrame,trace_color_mask
from smaart8_plot_profile_v868 import detect_v8_profile
from trf_core import read_trf
from selection_v7 import archive_order
from smaart_runtime_paths_v868 import trace_directory
from mag_sum_native_v826 import _smaart8_native_source_axis

EVIDENCE=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\QA_V8177_DUAL_SKIN_INSTALL_QA")
def test_colormasks_disjoint_core_teal_and_cyan():
    from PIL import Image as I
    im=np.zeros((280,1200,3),dtype=np.uint8)
    im[:,60:650]=[0,115,95] # Smaart8 native source on Dark/Light
    im[:,700:950]=[0,220,230] # independent brighter cyan trace
    s=I.fromarray(im)
    teal=trace_color_mask(s,"teal")
    cyan=trace_color_mask(s,"cyan")
    assert np.count_nonzero(teal[:,70:600])>500
    assert np.count_nonzero(cyan[:,70:600])==0
    assert np.count_nonzero(cyan[:,710:870])>500
    assert np.count_nonzero(teal[:,710:870])==0
def test_native_photos_verify_real_trace_both_skins():
    names=archive_order(trace_directory(8))
    by_name={path.name:path for path in names}
    assert {"find 1,2ms.trf","SUB SKY 2.trf"}<=set(by_name)
    for skin in ("DARK","LIGHT"):
        image=Image.open(EVIDENCE/f"SMAART8_{skin}_NATIVE_8177.png").convert("RGB")
        rects=detect_v8_profile(image)
        assert rects is not None,skin
        winrect=(0,0,image.width,image.height)
        mag=rects[1]
        frame=NativeMagFrame(image,mag,winrect)
        teal_pixels=np.count_nonzero(frame._mask("teal"))
        cyan_pixels=np.count_nonzero(frame._mask("cyan"))
        assert teal_pixels>=250,(skin,teal_pixels)
        assert teal_pixels>cyan_pixels*2,(skin,teal_pixels,cyan_pixels)
        # These historical screenshots prove the native colour/profile
        # matcher. Source-axis identity additionally requires immutable TRF
        # bytes or a current live tick frame; never pair old pixels with the
        # user's mutable trace directory.
