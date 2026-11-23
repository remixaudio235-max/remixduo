import sys,unittest,tempfile,time,struct
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from trf_core import synthetic,compute_sum,auto_align,read_trf,TraceError

class TestComplexSum(unittest.TestCase):
 def test_sum_gain(self):
  f=np.geomspace(20,20000,1000)
  a=synthetic("a",f)
  b=synthetic("b",f)
  z=compute_sum(a,b,coh_gate=.5)
  self.assertAlmostEqual(float(np.median(z.mag_db)),20*np.log10(2),places=5)
  self.assertTrue(np.allclose(z.phase_deg,0))
 def test_invert_cancels(self):
  f=np.geomspace(30,20000,150)
  a,b=synthetic("a",f),synthetic("b",f)
  v=compute_sum(a,b,invert_trace2=True)
  self.assertTrue(np.max(v.mag_db)<-200)
 def test_phase_from_complex_before_smoothing(self):
  f=np.arange(20.,2000.,2.)
  a=synthetic("a",f)
  b=synthetic("b",f,delay_ms=2.4)
  v=compute_sum(a,b,delay_ms=-2.4)
  self.assertTrue(np.max(np.abs(v.phase_deg))<1e-8)
 def test_signed_delay_and_polarity(self):
  f=np.arange(30.,1200.,2.)
  a=synthetic("a",f)
  for delay in (-2.4,2.4):
   b=synthetic("b",f,delay_ms=-delay)
   v=auto_align(a,b,lf=80,hf=800,max_delay_ms=10)
   self.assertTrue(v)
   self.assertAlmostEqual(v[0].delay_ms,delay,delta=.11)
   self.assertFalse(v[0].invert_trace2)
 def test_mask_phase_wrap(self):
  f=np.arange(100.,1500.,2.)
  a=synthetic("a",f)
  b=synthetic("b",f,delay_ms=7)
  v=compute_sum(a,b,phase_oct=12,mag_oct=12)
  self.assertTrue(np.all(v.phase_deg>=-180) and np.all(v.phase_deg<=180))
 def test_real_windows_106_file_sample(self):
  folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
  if not folder.exists():self.skipTest("Windows Smaart traces absent")
  names=list(folder.glob("*.trf"))
  self.assertGreater(len(names),0)
  ok=0;bad=0
  for p in names:
   try:
    r=read_trf(p)
    self.assertGreater(len(r.hz),50)
    ok+=1
   except (TraceError,ValueError,IndexError,struct.error):
    bad+=1
  print("WINDOWS_SMAART_TRF_PARSE",ok,bad,len(names))
  self.assertGreater(ok,10)

if __name__=="__main__":unittest.main(verbosity=2)
