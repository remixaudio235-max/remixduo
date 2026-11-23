import time,unittest
from pathlib import Path
from selection_v7 import SelectionController
class TestSelection(unittest.TestCase):
    def test_atomic_invalidations(self):
        records=[]
        c=SelectionController(records.append)
        a=("A.trf","B.trf")
        b=("C.trf","D.trf")
        c.apply(a);self.assertTrue(c.is_current(1,a))
        c.apply(b);self.assertFalse(c.is_current(1,a))
        c.apply(["C.trf"]);self.assertIsNone(c.last_pair)
        c.apply(["C.trf","D.trf","E.trf"]);self.assertIsNone(c.last_pair)
        c.apply(b);self.assertEqual(c.last_pair,b)
        self.assertEqual(len(records),4)
    def test_rapid_1000_tick_changes(self):
        c=SelectionController(lambda _:None)
        samples=[]
        for i in range(1000):
            start=time.perf_counter()
            c.apply(("A.trf","B.trf") if i%2 else ("C.trf","D.trf"))
            samples.append((time.perf_counter()-start)*1000)
        self.assertEqual(c.generation,1000)
        import numpy as np
        p95=float(np.percentile(samples,95))
        print("SELECTION_1000_EVENT_P95_MS",p95)
        self.assertLess(p95,10)
    def test_nontrf_refused(self):
        c=SelectionController(lambda _:None)
        c.apply(("A.trf","B.txt"))
        self.assertIsNone(c.last_pair)
if __name__=="__main__":unittest.main(verbosity=2)
