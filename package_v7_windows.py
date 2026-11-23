from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from datetime import datetime,timezone
import hashlib,json
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7")
out=root/"dist"
out.mkdir(exist_ok=True)
receipt={
 "date":datetime.now(timezone.utc).isoformat(),
 "host":"Admin-PC",
 "smaart_version":"9.6.4",
 "native_trf_decoder":"PASS 106/106",
 "real_smaart_full_databar_scan":"PASS 106/106 rows; source files sub p5.trf + TUNNING-1.trf",
 "data_bar_scroll_restored":"PASS 0 -> 0",
 "incremental_scan_seconds_sampled":[0.178,0.150,0.162],
 "tick_changes_observed_on_original_gui":[
  ["610.trf","TUNNINNGGG-2.trf"],
  ["623.trf","TUNNING-31.trf"],
  ["623.trf","643.trf"]
 ],
 "live_sum_render":"PASS 463 bins into Smaart GUI overlay",
 "plot_regions_absolute_windows_coords":{"phase":[252,112,1442,398],"mag":[252,553,1442,398]},
 "foreign_window_hide":"PASS Claude foreground and no visible V7 GUI windows",
 "transparent_click_through":"PASS WS_EX_TRANSPARENT",
 "simulation_gui_transitions":"PASS 5/5",
 "selection_dispatch_stress":"PASS 1000 changes; P95 0.0134 ms (state only)",
 "algorithm_tests":"PASS 6/6",
 "source_version":"V7 Windows QA, source-first port",
 "y_axis_auto_calibration":"HOLD; requires manual controls and matching Smaart plot axes",
 "source_pair_clock_ref_parity":"HOLD",
 "smaart_fft_tf_stream":"NOT IMPLEMENTED",
 "full_tick_to_draw_p95":"NOT MEASURED",
 "smaart_binary_modified":False,
 "remix_production_merge":False,
}
(root/"V7_REAL_GUI_RECEIPT_20261029.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
path=out/"REMIX_AUTO_ALIGN_V7_WINDOWS_SOURCE_QA_20261029.zip"
files=sorted(p for p in root.iterdir() if p.is_file() and
  (p.suffix in {".py",".bat",".md",".json"} or
   p.name=="V7_LIVE_SMAART_GUI_20261029.jpg"))
with ZipFile(path,"w",ZIP_DEFLATED,compresslevel=7) as z:
    for p in files:z.write(p,p.name)
with ZipFile(path) as z:
    assert z.testzip() is None
sha=hashlib.sha256(path.read_bytes()).hexdigest()
print("V7_PACKAGE_PASS",len(files),"FILES",path,"BYTES",path.stat().st_size,"SHA256",sha)
print("V7_RUN",root/"RUN_V7_WINDOWS.bat")
