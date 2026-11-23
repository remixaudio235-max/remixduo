from pathlib import Path
from PIL import Image
import sys,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from selection_v7 import archive_order,scan_icon_white_cross
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
image=Image.open(Path(__file__).resolve().parent/"smaart_printwindow.png")
order=archive_order(folder)
for i,p in enumerate(order[:35]):
 y=163+i*22
 if y+18>=image.height:break
 print(i,p.name,
       [(x,scan_icon_white_cross(image,(x,y+3,x+15,y+18))) for x in (12,15,18,21,23)])
