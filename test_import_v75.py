import os,time,tempfile,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from selection_v7 import archive_order,fresh_unindexed_imports

def make_environment(root):
    folder=root/"Session Data"
    folder.mkdir()
    idxroot=ET.Element("root")
    for i,name in enumerate(("A.trf","B.trf")):
        (folder/name).write_bytes(b"stub")
        p=ET.SubElement(idxroot,"path",adhocIndex=str(i))
        p.text=str(folder/name)
    idx=root/"index.xml"
    ET.ElementTree(idxroot).write(idx,encoding="unicode")
    now=time.time()
    os.utime(idx,(now-120,now-120))
    return folder,idx,now

class ImportFallback(unittest.TestCase):
    def test_native_index_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder,idx,now=make_environment(Path(tmp))
            self.assertEqual([p.name for p in archive_order(folder)],["A.trf","B.trf"])
            self.assertEqual(fresh_unindexed_imports(folder),())
    def test_new_ascii_trf_prepend(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder,idx,now=make_environment(Path(tmp))
            one=folder/"0 delay-1.trf"
            two=folder/"4,8 ms delay-1.trf"
            one.write_bytes(b"stub")
            two.write_bytes(b"stub")
            os.utime(one,(now-30,now-30))
            os.utime(two,(now-10,now-10))
            names=[p.name for p in archive_order(folder)]
            self.assertEqual(names,["4,8 ms delay-1.trf","0 delay-1.trf","A.trf","B.trf"])
            self.assertEqual(len(fresh_unindexed_imports(folder)),2)
    def test_stale_unknown_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder,idx,now=make_environment(Path(tmp))
            other=folder/"old unknown.trf"
            other.write_bytes(b"stub")
            os.utime(other,(now-500,now-500))
            with self.assertRaisesRegex(ValueError,"older"):
                archive_order(folder)
    def test_ambiguous_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder,idx,now=make_environment(Path(tmp))
            for name in ("import-a.trf","import-b.trf"):
                f=folder/name;f.write_bytes(b"stub")
                os.utime(f,(now,now))
            with self.assertRaisesRegex(ValueError,"tied"):
                archive_order(folder)
    def test_missing_indexed_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder,idx,now=make_environment(Path(tmp))
            (folder/"B.trf").unlink()
            with self.assertRaisesRegex(ValueError,"missing TRF"):
                archive_order(folder)
if __name__=="__main__":
    unittest.main(verbosity=2)
