"""Read-only live chart-role and rendering prerequisite check."""
import win32gui
from plot_geometry_v7 import locate_plots
from plot_role_v812 import locate_role_plots
from pathlib import Path
h=win32gui.FindWindow(None,"Smaart Suite")
print("SMAART_HWND",h,"RECT",win32gui.GetWindowRect(h) if h else None,flush=True)
print("TEMPLATES",[(f,(Path(__file__).parent/f).exists()) for f in ("V812_MAG_TITLE_TEMPLATE.png","V812_PHASE_TITLE_TEMPLATE.png")],flush=True)
if h:
    try: print("PLOT_GEOMETRY",locate_plots(h),flush=True)
    except Exception as e: print("PLOT_GEOMETRY_ERROR",repr(e),flush=True)
    try: print("ROLE_GEOMETRY",locate_role_plots(h),flush=True)
    except Exception as e: print("ROLE_ERROR",repr(e),flush=True)
