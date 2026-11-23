# RemiX Dou Auto Phase — bàn giao tiếp tục chat mới, 30/10/2026

**TÀI LIỆU ƯU TIÊN cho phiên mới; đọc trước khi code.** Đây là tóm tắt kỹ thuật và trạng thái kiểm chứng của phiên làm việc V8.25–V8.35, KHÔNG phải bản lưu nguyên văn toàn bộ cuộc trò chuyện ChatGPT.

## 1. Source và Git chính xác
- Host: **Admin-PC**, Windows; truy cập bằng **Remote Desktop Commander**.
- Repository: `D:\REMIX_AUTO_ALIGN_V6_DEV`.
- Branch đã dùng: `qa/remix-signal-v825-checkpoint`.
- **CURRENT ACTIVE SOURCE:** `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA`.
- Entry: `overlay_v7.py`; UI top toolbar/dock: `signal_tools_gui_v813.py`.
- Interpreter: `D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe`; overlay khởi chạy bằng pythonw cùng venv.
- Latest feature commit at handoff: **19f9e5e** — V8.35 cyan LF–HF highlight on both plots.
- Existing feature tag: `checkpoint/remix-dou-v835-crossover-20261030`.
- Frozen recovery source: `windows_v8_25_BUTTON_ONLY_COMPACT_QA` (đã sửa PrintWindow title detection); không ghi đè.
- Không tìm/merge toàn bộ 39 bản QA cũ, không thay source bằng AutoEQ parallel.
- Trước mọi sửa đổi kiểm tra `git status`, `git log`, PID + command line + CWD của pythonw và HWND Smaart. PID **không phải định danh vĩnh viễn**.
- Vào thời điểm kiểm tra gần nhất: wrapper 5004/child 4044, Smaart PID 20372 và Responding=True; kiểm lại chứ không tin số này trong chat sau.

## 2. Chuỗi công việc/commit đã thực sự thực hiện trong phiên
| QA | Commit | Ý nghĩa |
|---|---|---|
| Git nguồn | da64e73, 1db31fc | Tạo repo cục bộ, commit V8.25 baseline / V8.26 candidate và hồ sơ |
| V8.27 | ca6f74d | Candidate native Mag Y kế thừa V8.25; không sao chép ngược source cũ |
| V8.28 | 0c835f2, 33b596b | Đồng bộ signed Y Phase/Mag, frame watermark, xử lý callback stale, exact-process restart |
| V8.29 | 343c92e | Kết nối `_check_phase_axis_drag()` vào GUI tick; Phase SUM preview kéo thước Y, settle native |
| V8.30 | 8f6310d | Sửa `plot_geometry_v7`: layout detection không dùng ngưỡng 52% cứng; khôi phục cùng lúc SUM Phase/Mag; transient UIA failure giữ layout hợp lệ ngắn |
| V8.31 | e1420b3, 957e682 | Thêm logo RemiX + nhãn **RemiX Dou** (X hoa) trước Auto Phase; không dịch các nút cũ |
| V8.32 | 25a5a93 | LF/HF vertical line draggable ở Mag và Phase, đồng bộ chung các giá trị ROI |
| V8.33 | 55b7dbb | Khi bật 3 trace cảnh báo co lại: Trace card 70px, warning 36px, right dock 148px; đủ 2 trace trả Top3 đầy đủ |
| V8.34 | 30ca888 | Tối ưu Y pan: pre-render/cache raster SUM, 16ms observer (~60Hz), epoch/latest-only native frame, màu đỏ saturated native được nhận diện; tránh ghost-panning |
| V8.35 | 19f9e5e | Vùng crossover cyan bán trong suốt LF–HF trên **cả Phase/Mag**, đường viền hai mép, chip `CROSSOVER 60–200 Hz` trên Mag; không rebuild raster SUM |

## 3. Yêu cầu của người dùng phải bảo toàn
- Ứng dụng phủ UI **Smaart Suite** thật, theo **đúng 2 trace được tick từ Data Bar**. 1/3 trace phải fail closed, không đoán; 3/3 stable tick verification.
- SUM Phase, SUM Magnitude đúng complex TF; đồng bộ đồ thị native và các thay đổi trục Y; tránh gật, lag, ghost. Native Mag Y không biến thành DSP boost giả.
- Auto Phase gồm Top3 ứng viên, INV, Delay, LF/HF, Phase Match; không xóa/thu nhỏ cả panel khi chỉ cần nút Auto Phase gọn.
- Logo/remix branding ở top trước Auto Phase, viết đúng **RemiX Dou**.
- LF/HF có dashed guides và vùng highlight crossover liên thông hai đồ thị; kéo LF/HF từ Phase **hoặc** Mag phải dịch vùng ở cả hai.
- UI nền đen, neon xanh/cyan, dễ đọc; overlay SUM tự ẩn đúng khi vào Auto EQ/FIR/Live/Hide, tránh che Smaart khác.
- Không làm mất phần AutoEQ/MagEQ/gradient và plugin code song song; đây là module riêng, cần integration có QA chứ không wholesale copy.

## 4. Bằng chứng QA mới nhất: KHÔNG suy diễn quá phạm vi
**V8.35:** `V835_CROSSOVER_ROI_HIGHLIGHT_QA_20261030.md`
- **52/52 pytest PASS**: V8.28–V8.35 cộng TF/selection/EQ baseline.
- ROI visual test: LF 60→90, HF 200→450, highlight di chuyển đúng cả hai plot; SUM bitmap cache rebuild count không đổi.
- Native GUI screenshot thật: `V835_CROSSOVER_LIVE_QA.png` — hai đồ thị đều có cyan band 60–200 Hz và SUM vẫn thấy; logo đúng.
- Qt offscreen P95 (4096 points, 40 frames post-warmup): **Phase 2.72ms; Mag 2.91ms**. Đây là chi phí paint offline, **không phải end-to-end mouse→screen P95**.
- V8.34 raster parity giữ F1 = 1.0 cho các mức shift đã test. Stress GUI 160px xuống/trả trên Phase/Mag đã thực hiện, nhưng ở tọa độ Mag thử nghiệm trace native không thực sự di chuyển.
- V8.33 có 43/43 test PASS, compact invalid warning mock Qt PASS; GUI Smaart thực với đúng 2 trace PASS.
- V8.32 có 42/42 test PASS; native mouse-hit trực tiếp ở Mag vẫn HOLD khi foreground HWND không hợp lệ trong lần thử.

## 5. Các vấn đề CÒN HOLD
1. **Ưu tiên cao nhất** nếu người dùng yêu cầu Y-follow: kiểm tra tương tác Smaart thật với **native trace thực sự dịch Y** (Phase và Mag), ghi video/chuỗi frame + timestamp SOURCE/SUM và P50/P95 mouse→present. Nhiều test chỉ drag chuột nhưng native curve không đổi. Không đánh dấu PASS bằng mock/offscreen.
2. Wheel zoom / pan, wrapping ±360 Phase, thay đổi REF, các viewport layout/resizes, liên tục kéo biên độ lớn và giật ngược cuối drag: chưa nghiệm thu end-to-end.
3. **Realtime complex TF streaming từ Smaart chưa có**: SUM hiện tính từ snapshot `.trf` đã lưu, không được gọi là streaming live H(f) theo trace. Phân biệt viewport Y với thay đổi dữ liệu TF.
4. AutoEQ một trace tick + MagEq markers/gradient là nhánh phát triển riêng, chưa tự động coi là đã merge vào source Auto Phase này.
5. Khi Smaart minimize/foreground bị đổi, test desktop cần fail closed; không bịa vị trí hoặc kết quả.

## 6. Lưu ý tránh mất code khi chat mới
- Một số file gốc `AGENTS.md`, `CURRENT_WORK_STATE.md`, `FEATURE_ACCEPTANCE_MATRIX.md`, `START_NEW_CHAT_HERE.txt` đang có thay đổi chưa commit từ **phiên khác** và có thể chứa source/PID lịch sử không còn đúng. Chúng cần được đọc để hiểu quy tắc, nhưng **chính source/PID đang chạy và handoff V8.35 này** quyết định phiên tiếp theo. Không ghi đè hay commit hộ các thay đổi đó.
- Có 4 screenshot V8.34 (`V834_MAG_PEAK.png`, `V834_MAG_PRE.png`, `V834_PHASE_PEAK.png`, `V834_PHASE_PRE.png`) đang dirty do stress test khác: **đừng gộp vào commit handoff**.
- V8.25, V8.32, V8.33, V8.34, V8.35 đều có điểm rollback riêng. Backup Git bundles lưu ở `D:\REMIX_AUTO_ALIGN_GIT_BACKUPS`.
- Không phát noise / Generator / Sweep, không động tới ASIO/soundcard, hardware DSP, `.trf` saved files, không stop Smaart. Nếu cần restart overlay dùng đúng file `restart_exact_v828.py` sau kiểm tra an toàn exact-owner.

## 7. Lệnh mở đầu trong chat mới (read-only)
```powershell
$root = 'D:\REMIX_AUTO_ALIGN_V6_DEV'
git -C $root status -sb
git -C $root log -4 --oneline
git -C $root tag -l 'checkpoint/remix-dou-v83*'
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
  Where-Object { $_.CommandLine -like '*windows_v8_27_MAG_NATIVE_SYNC_QA*' } |
  Select-Object ProcessId,ParentProcessId,CommandLine
```
Đọc tiếp `HANDOFF_NEW_CHAT_V835_20261030.md` (file này), `V834_FAST_NATIVE_Y_PAN_QA_20261030.md` và `V835_CROSSOVER_ROI_HIGHLIGHT_QA_20261030.md`.

## 8. Điều kiện bàn giao
Phiên mới bắt đầu trên **cùng source V8.35**, dùng Git log/tag, không chạy lại source cũ. Khi nhận yêu cầu mới: đọc đúng code trong thư mục trên, chỉ sửa file liên quan, test Qt + ảnh Smaart thật, commit và tạo tag. Không nói "đã PASS GUI" nếu mới chỉ test mock. Sau cùng đưa commit hash/rollback tag/PID mới cho người dùng.
