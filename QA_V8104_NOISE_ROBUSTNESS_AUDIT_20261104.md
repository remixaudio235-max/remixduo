# QA V8.104 — Audit độ tin cậy Phase/Mag/Coh trong môi trường nhiễu (2026-11-04)

EXACT SOURCE: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA` (branch
`qa/remix-duo-v873-native-tf-reader`, HEAD `496371b`). **Chỉ audit + mô phỏng; KHÔNG sửa code sản phẩm.**
Không chạy Smaart, không phát Generator, không ghi DSP.

## 1. Sự thật kiến trúc (quyết định phạm vi nâng cấp)

App **không tự đo TF**. Bộ ước lượng dual-FFT (H1 = Gxy/Gxx), số lần average,
Coherence đều do **Smaart** tính. App chỉ đọc kết quả:

`Smaart (FFT, average, coherence)` → `.trf / ASCII / live SDK frame`
→ `read_trf` / `smaart_format_adapter` / `NativeTFReader`
→ `TFTrace(hz, h, coherence)` → `matched()` → AutoPhase / SUM / AutoEQ / FIR.

Hệ quả: app **không thể** làm cho TF "đúng hơn" khi chính Smaart đo sai. Việc app làm được là
(a) **phát hiện** khi TF/Coherence không đáng tin và fail-closed, (b) dùng đúng dữ liệu đáng tin,
(c) hướng dẫn người dùng chỉnh cách đo (average, mức kích thích, vị trí mic, ROI).

## 2. Cách Coherence đang được dùng (hiện trạng)

| Nơi | Ngưỡng / trọng số | File |
|---|---|---|
| AutoPhase delay solver | gate `coh>=0.60`, trọng số `coh**2`, cần ≥12 bin | `src/remix_duo/core/traces.py:101` |
| Ghép 2 trace | `min(coh_a, coh_b)` | `traces.py:99` |
| SUM hiển thị | mask `coh>=0.60`; phase smoothing trọng số `coh**2` | `traces.py:142`, `core/smoothing.py` |
| AutoEQ | gate 0.60 + `quality_floor 0.30`, `boost_quality_floor 0.65`, `weights=q**1.5*rel*fc` | `autoeq_core.py:117`, `core/autoeq_engine.py:223` |
| FIR, native mag fit, ref anchor | `coh>=.6` lặp lại cứng | `fir_native_v846.py:231`, `smaart_native_mag_fit.py:118`, `mag_ref_anchor_v83.py:61`, ... |

Ngưỡng 0.60 bị **lặp cứng ≥8 nơi**, không có một policy chung.

## 3. Bằng chứng mô phỏng (reproducible)

Script: `qa_v8104_noise_mc.py`, `qa_v8104_noise_welch.py` (chỉ dùng `remix_duo.core.traces`,
không đọc/ghi file dữ liệu). Chạy bằng `.venv` của project.

Mô hình Welch thực tế: tham chiếu điện sạch, nhiễu cộng vào mic (gió/quạt/đám đông),
Smaart ước lượng H1 và MSC từ `nd` lần average. Trace 2 trễ 3.7 ms. 40 lần thử mỗi ô.

| Kịch bản | nd | Coh bị thổi phồng | Bin xấu lọt gate 0.60 | Sai số Mag (bin "đạt") | AutoPhase sai (>0.3 ms / không ra) |
|---|---|---|---|---|---|
| Sạch | 1–64 | ≈0 | 0% | 1.9 → 0.1 dB | 0% |
| Quạt | 1 | **+0.46** | **100%** | **6.8 dB** | 25% |
| Quạt | 16 | +0.01 | 39% | 1.35 dB | 0% |
| Gió (LF) | 1 | **+0.36** | **100%** | **9.3 dB** | **60%** (sai tới 13.5 ms) |
| Gió (LF) | 2 | +0.16 | 49% | 5.8 dB | 40% |
| Gió (LF) | 16 | +0.02 | 5% | 0.5 dB | không đủ bin → fail-closed (đúng) |
| Đám đông | 1 | +0.31 | 100% | 5.9 dB | 0% |

Thử nghiệm phụ (`qa_v8104_noise_mc.py`): khi Coherence **khớp đúng** mức nhiễu thật, solver
hiện tại đúng 100% ở mọi kịch bản.

## 4. Kết luận audit

- **F1 (P1) — Coherence bị thổi phồng khi Smaart average ít.** Với nd=1–2 (FIFO ngắn/không
  average), ước lượng MSC lệch dương +0.16…+0.46. Gate 0.60 cho lọt tới 100% bin hỏng, nên Mag
  sai 6–9 dB và AutoPhase sai delay tới 60% trong gió. App **không có cách nào phát hiện** vì
  không biết `nd`, và TRF header chưa được giải mã trường average (`traces.py:42-74` chỉ đọc 5 mảng).
  Đây là rủi ro thực tế lớn nhất trong môi trường ồn.
- **F2 (P2) — Kết quả AutoPhase không có độ tin cậy.** Solver trả top-4 khi chỉ có 12+ bin,
  không báo margin giữa ứng viên 1 và 2, không báo số bin ROI. Trong quạt nd=64 chỉ còn ~6 bin,
  nên kết quả lúc có lúc không, mà người dùng không được cảnh báo.
- **F3 (P3) — Ngưỡng coherence phân tán**, lặp cứng ở ≥8 module. Muốn chỉnh một policy nhiễu
  thì phải sửa nhiều nơi, dễ lệch nhau.
- **F4 (P3) — Mag smoothing của AutoEQ không có trọng số coherence**
  (`fractional_octave_smooth`, `autoeq_engine.py:180`) và resample log-grid bằng `np.interp`
  chỉ lấy 2 bin lân cận (không trung bình) ở HF. Bin nhiễu đi thẳng vào đường cong phân tích
  (đã được giảm nhẹ một phần nhờ `weights` ở bước sau).
- **KHÔNG nên làm (bác bỏ bằng số liệu):** đổi trọng số AutoPhase sang inverse-variance
  `γ²/(1-γ²)` + chặn outlier. Mô phỏng cho thấy không cải thiện, có ô còn tệ hơn
  (quạt nd=2: 2% → 15% sai). Giữ `coh**2`.

## 5. Đề xuất nâng cấp (chờ duyệt thiết kế, chưa làm)

1. **Kiểm tra tự nhất quán Coherence (giải F1)** — so độ "gồ ghề" bin-to-bin thực tế của H
   (sau khi bỏ xu hướng trơn) với độ phân tán mà Coherence báo cáo dự đoán. Lệch lớn thì gắn cờ
   "Coherence không đáng tin — tăng Averaging Smaart" và HOLD AutoPhase/AutoEQ/FIR.
   Cần chứng minh bằng mô phỏng **trước** khi đưa vào sản phẩm.
2. **Giải mã trường Averaging trong TRF header** — cần 2–3 file TRF thật, lưu cùng hệ thống
   với Averaging khác nhau (vd 1, 4, 16). Có `nd` thì hiệu chỉnh bias MSC chính xác:
   `γ²_corr = (nd·γ² − 1)/(nd − 1)`.
3. **Độ tin cậy AutoPhase (F2)** — trả kèm số bin ROI, margin dB giữa ứng viên #1 và #2, và
   độ ổn định khi chia ROI làm đôi. Mơ hồ thì hiện "KHÔNG CHẮC" thay vì chọn ứng viên.
4. **Kiểm tra ổn định nhiều snapshot (chống cơn gió)** — so 2–3 TRF/frame liên tiếp. Delay hoặc
   Mag lệch quá ngưỡng thì HOLD.
5. **Gom policy Coherence (F3)** về một module `core/quality_policy.py`; các module khác import.
6. **Hướng dẫn đo trong UI** khi HOLD: tăng Averaging (≥16 ở ngoài trời), tăng mức kích thích,
   dùng mũ chắn gió, chọn LF/HF tránh vùng gió/hum.

## 5b. ĐÃ TRIỂN KHAI (cùng ngày, user chọn "Coherence check + confidence")

Đề xuất 1 (kiểm tra độ gồ ghề so với Coherence) **bị bác bỏ** sau khi khảo sát 25 TRF thật:
Smaart lưu MTW 463 điểm đã làm mượt, nên chỉ số ndEff ra 2–11 ngay cả với phiên đo tốt → HOLD giả.
Thay bằng hai tiêu chí đã kiểm chứng:

- **Bootstrap đồng thuận** (đề xuất 3): lấy mẫu lại các bin ROI 64 lần (seed cố định), đếm tỉ lệ
  lần giải ra cùng cực tính và delay ±0.3 ms với kết quả #1. Dưới 80% → `LOW` (vẫn hiện
  ứng viên kèm cảnh báo). Không tin vào con số Coherence, mà đo độ nhất quán thật của dữ liệu.
- **Coherence bão hòa + Mag gồ ghề**: ≥60% bin ROI có coh ≥0.995 **và** độ gồ ghề Mag
  (median |sai phân bậc 2 của dB|) >2 dB → `HOLD_SATURATED` (fail-closed, ẩn ứng viên).
  Loopback sạch (coh=1, mượt) **không** bị HOLD.
  Dữ liệu thật: bão hòa ≥0.6 có gồ ghề tối đa 0.24 dB; nd=1 gió/quạt mô phỏng ≥5 dB.

Code (shared core, không import native):
- `src/remix_duo/core/align_confidence.py` — mới, `assess_alignment()` → `AlignConfidence`.
- `src/remix_duo/core/traces.py` — tách `alignment_roi/alignment_delays/alignment_penalty_db`
  làm nguồn duy nhất của hàm mục tiêu AutoPhase. `auto_align` cho kết quả **bit-identical**
  (đã có test so với bản đông lạnh của solver cũ).
- `overlay_v7.py` — worker gọi `_solve_autophase` (solver cũ + độ tin cậy). Lỗi đánh giá
  thì không bao giờ che ứng viên. Trạng thái hiện `Tin cậy #1: xx%` / `⚠ ĐỘ TIN CẬY THẤP` / `HOLD: …`.
  Không đổi layout, kích thước nút, DSP hay Smaart.

Bằng chứng:
- Mô phỏng: bắt 88–100% kết quả sai (gió/quạt, nd 1–4). HOLD/LOW sai 0% ở sạch nd≥2 và quạt nd≥2.
- TRF thật, 112 cặp liên tiếp: OK 74, LOW 38, HOLD 0. Thời gian ≤0.22 s (ROI 60–2000 Hz: 0.32 s).
  Cặp có đáp án đã biết `0 delay` / `4,8 ms delay` → −4.8 ms, OK, đồng thuận 100%.
  Các cặp LOW cùng phiên phần lớn có lời giải nhảy ±17 ms (mơ hồ chu kỳ trong ROI 60–200 Hz).
  **Chưa có ground truth** cho các cặp LOW, nên tỉ lệ cảnh báo giả trên dữ liệu thật CHƯA được chứng minh.
- Test: `tests/shared/test_align_confidence.py` (10) + `test_v8104_autophase_confidence.py` (5).

## 5c. Live session 2026-11-04 (Admin-PC)

- Preflight: Smaart Suite PID 26516, HWND 6425940. Được user cho phép, đã dừng đúng các
  overlay cũ: dev 19492/36728 (code trước V8.104) và V8.27 15028/24176 (watcher tự bật).
  Smaart và watcher 8012/9056 không bị đụng tới. Không Generator, không ghi DSP.
- Khởi chạy MỘT overlay V8.104: PID 36424→11928, CWD `windows_v8_87_MAC_OVERLAY_QA`,
  venv python `-X faulthandler`.
- Log: `V812_ROLE_GEOMETRY 6425940` (tìm thấy Mag/Phase). `V7_PAIR_EVENT` + `V7_SUM_RENDER_READY 463`
  cho cặp (TUNNINNGGG-6, TUNNINNGGG-4), rồi (TUNNINNGGG-4, TUNNING-30). User bấm AUTO PHASE.
  stderr chỉ có 2 cảnh báo Qt lúc khởi động, **không exception**.
- Giá trị đối chiếu offline (cùng hàm, ROI 60–200 Hz):
  - 6|4 → 0.0 ms Không đảo, `OK`, đồng thuận 100% (dòng trạng thái kỳ vọng "Tin cậy #1: 100%").
  - 4|30 → 12.7 ms Đảo pha, `OK`, đồng thuận 98% ("Tin cậy #1: 98%").
- **Live GUI: HOLD.** Chưa có ảnh/nguyên văn dòng trạng thái từ màn hình thật (user từ chối
  quyền chụp/điều khiển màn hình). Đã xác nhận: chạy được trên Smaart thật, nhận cặp, không lỗi.

## 5d. Full test AutoPhase / AutoEQ / FIR (2026-11-04)

Unit/offscreen Qt (file test gom theo từ khóa):
- AutoPhase: **48/48 PASS**.
- AutoEQ: 211 PASS, 2 FAIL. FIR: 248 PASS, 1 FAIL. Cả 2 FAIL (`test_export_eq_v08` top-bar
  thêm `remote`; `test_native_eq_v06` KeyError `teal`) **đã FAIL sẵn trên HEAD 496371b sạch**.

End-to-end trên 12 TRF thật, chỉ đọc (`qa_v8104_realdata_e2e.py`):
- AutoPhase: 9 OK, 2 LOW. Cặp chuẩn 0/4.8 ms đúng ±4.80 ms.
- AutoEQ (Flat, 60–12k, 12 band): 11 PREVIEW_READY (wRMS giảm ~1.2–1.6 dB, gain trong giới hạn),
  1 NO_SAFE_SOLUTION (`4,8 ms delay-1`: coherence median 0.67 so với 0.82 vì đo khi chưa bù delay; fail-closed đúng).
- FIR Mag: 12/12 taps hữu hạn. p95 sai số 100–10k ≤0.33 dB (1024 tap), giảm khi tăng tap.
  Sai số lớn nhất ở LF bị giới hạn bởi độ dài tap (vật lý).
- **FIR Phase: HOLD 12/12** ("actual magnitude ripple >1.5 dB") ở mọi tap 1024/2048/4096,
  có/không Phase+. FIR Phase chưa bao giờ ra kết quả trên dữ liệu thật → **phát hiện mới, chưa điều tra**.

## 5e. V8.105 — FIR Phase debug & fix (2026-11-04)

Triệu chứng: FIR Phase HOLD 113/113 TRF thật ở dải mặc định GUI (LF 30, HF 16000 Hz).
Các test cũ chỉ dùng dải hẹp (111–310, 368–3350 Hz) nên không bắt được.

Nguyên nhân gốc (đã đo):
1. **Xoay phase dưới mức phân giải của FIR.** Ripple vượt 1.5 dB chỉ ở 33–35 Hz
   (−2.24 dB / 1024 tap, −1.56 dB / 4096 tap). Từ 300 Hz trở lên chỉ còn 0.13 / 0.02 dB.
2. **`np.unwrap` bị aliasing trên lưới MTW 463 điểm.** Delay thuần 7.3 ms ra 2.16 ms,
   40 ms ra 0.45 ms. Phase "cần sửa" bị kẹp ±75° ở 98% điểm, tức là hiệu chỉnh rác.
   Chỉ số `phase_excess_rms` (Excess RMS hiển thị cho người dùng) cũng bị cùng lỗi.

Sửa (shared core, numpy only):
- MỚI `src/remix_duo/core/phase_tools.py` `remove_bulk_delay()`: tìm delay coherent trên dải
  ≤1 kHz (±300 ms, bước 0.05 ms), xoay ngược, rồi mới unwrap phần dư + polyfit.
  Kết quả: 7.30 / 40.03 / −2.93 ms (thật 7.3 / 40 / −3).
- `filters.design_phase_only_fir`: dùng `remove_bulk_delay`. Phase chỉ được sửa từ
  `phase_lf = max(LF, 12·fs/taps)` (`PHASE_RESOLVE_CYCLES=12`, chọn theo thực nghiệm).
  Cổng Mag 1.5 dB **giữ nguyên** trên toàn LF–HF. Thêm cổng mới: HOLD nếu Excess Phase
  **tệ hơn** trong dải FIR tác động. `FIRResult.phase_lf_hz` (trường tùy chọn mới).
- `fir_preview.phase_excess_rms`: xoay ngược bulk delay trước khi unwrap.
- `signal_tools_gui_v813.py`: phần chi tiết FIR hiện "Phase chỉ được sửa từ X Hz trở lên…".

Bằng chứng (113 TRF thật, 30–16000 Hz):
- 1024 tap: 59 cải thiện, 23 ra kết quả chưa kiểm chứng được, 20 HOLD (tệ hơn), 10 HOLD (ripple), 1 HOLD khác.
- 4096 tap: 72 cải thiện, 13 chưa kiểm chứng được, 12 HOLD (tệ hơn), 15 HOLD (ripple), 1 HOLD khác.
- Cải thiện Excess RMS điển hình 17–46% (vd TUNNINNGGG-11: 33.1° → 18.0° @4096). Mag lệch ≤0.76 dB.
- Test: `tests/shared/test_fir_phase_range.py` (14), `test_v8105_fir_phase_default_range.py` (1).
  Các test cũ v862/v893/v895 PASS không sửa.
- HOLD: chưa nghe thử / chưa đo FIR đã nạp vào DSP thật. "Chưa kiểm chứng được" vẫn xuất ra như hành vi cũ.

## 6. HOLD / chưa chứng minh

- Giả định Smaart Coherence = MSC (γ²): **chưa xác minh** với tài liệu Smaart.
- Mô hình nhiễu là tổng hợp, chưa phải đo thật ngoài trời.
- Unit / Native / Live GUI: không có thay đổi sản phẩm, nên không có PASS mới.
- Next safe command:
  `D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe qa_v8104_noise_welch.py`
