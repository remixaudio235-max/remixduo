# V8.146 License / setup / macOS portability Reflexion — 2026-11-14

## Kết luận

Source hiện tại có nền tảng dùng chung đủ tốt cho thuật toán và license, nhưng
chưa thể đóng gói lại thành bản macOS ngang tính năng Windows. Có thể mang
`src/remix_duo/core` và hợp đồng license sang cả Apple Silicon lẫn Intel; phần
overlay Smaart, nhận diện tick/TF/Fs/trục, UI Auto Phase/EQ/FIR và lifecycle
Windows vẫn cần được nối lại bằng backend/UI macOS.

Không có thay đổi license server, secret, registry, Smaart, audio routing hay
DSP trong vòng kiểm tra này.

## Bằng chứng đã chạy

Lệnh kiểm tra chuyên biệt license/platform/build:

```text
C:\rdv311\Scripts\python.exe -m pytest -q \
  tests/shared/test_license_platform.py \
  tests/contracts/test_mac_native.py \
  tests/shared/test_build_preflight.py \
  test_v874_duo_license.py \
  test_v876_cloud_license_client.py \
  test_v878_pro_style_activation.py \
  test_v881_activation_async.py
```

Kết quả xác nhận lại trong vòng Reflexion: **66 passed in 2.49s**.

Required active-build guard vẫn HOLD vì venv được chỉ định trỏ tới Python đã
không còn tồn tại dưới `C:\Users\Admin\...\Python311\python.exe`. Đây là lỗi
hạ tầng của guard, không phải bằng chứng build identity PASS.

## License

### PASS trong source/unit scope

- Token Ed25519 dùng public key ghim trong client; signing/admin secret không
  nằm trong app.
- Windows và macOS tách chặt platform/fingerprint (`WIN/fpv3` và `MAC/fpv4`);
  token sai platform, machine, edition, thời gian hoặc fingerprint bị từ chối.
- Parser giới hạn kích thước, từ chối duplicate JSON keys và fail closed.
- Online activation chỉ chấp nhận HTTPS, giới hạn response, timeout 8 giây và
  xác minh token trước khi ghi nguyên tử xuống máy.
- Fingerprint Mac dựa trên hash IOPlatformUUID, không phụ thuộc arm64/Rosetta;
  cùng một máy không bị đổi entitlement chỉ vì kiến trúc tiến trình.

### Rủi ro/chính sách còn lại

- Offline token `exp=0` là vĩnh viễn theo thiết kế và không có revocation. Đây
  là quyết định thương mại cần xác nhận, không phải lỗi chữ ký.
- Python source/frozen app không phải ranh giới chống sửa tuyệt đối. Không nên
  quảng cáo client là tamper-proof.
- User-Agent và fallback machine label trong online client còn ghi Windows khi
  chạy Mac; không bypass license nhưng làm sai telemetry/chẩn đoán.

## Setup/build macOS

### Điểm tốt

- Preflight bắt buộc build native trên macOS, Python 3.11, đúng architecture;
  từ chối Windows cross-build và Rosetta.
- Quy trình có kiểm tra architecture bundle, frozen selfcheck, codesign, DMG,
  notarization và staple/validate.
- Release gate yêu cầu evidence riêng arm64/x86_64, cùng source digest, native
  Smaart và clean install.
- Bản arm64 QA lịch sử đã build/install/selfcheck; 222 binaries được kiểm tra
  architecture. Đây không phải release acceptance hiện tại.

### Gate phát hiện trong Reflexion

1. `packaging/macos/build.py::source_digest()` chỉ hash thư mục `src/`; chưa
   bind entrypoint, `pyproject.toml`, dependency lock và packaging scripts.
2. Acceptance receipts là JSON không ký. Gate kiểm tra nội dung nhưng người có
   quyền ghi filesystem có thể tự tạo receipt giả. Release evidence cần CI
   attestation/chữ ký hoặc được tạo trực tiếp bởi gate không thể sửa tay.
3. Metadata vẫn mang nhãn 8.87/8.87.0 trong khi Windows source đã tới V8.145;
   không được phát hành Mac với provenance/version cũ.
4. Chỉ có dependency evidence arm64; Intel/x86_64 chưa có host/build/live QA.
5. Developer ID, notarization và clean-install public release vẫn HOLD.

## Khả năng mang source hiện tại sang Mac

| Phần | Trạng thái | Ghi chú |
|---|---|---|
| Core SUM/AutoEQ/FIR/Phase | PASS source portability | Không import Win32; dùng chung được |
| License contracts/client | PASS unit/contract | 66 test chuyên biệt PASS |
| SUM fallback một phía | PASS shared core | Nằm trong `src/remix_duo/core/traces.py` |
| Manual/Auto giới hạn Auto EQ | PASS một phần | Solver nằm shared core; control Windows chưa port |
| LF/HF FIR mặc định 500/2500 | HOLD parity | Hiện nằm trong UI Windows ngoài `src` |
| Toast chậm hơn 50 ms | HOLD parity | Hiện là logic UI Windows ngoài `src` |
| Native trace tick/TF/Fs/trục | HOLD | AX trên Mac chưa chứng minh tick thật/TF live |
| Auto Phase/EQ/FIR native overlay | HOLD | `ui/overlay.py` hiện cố ý trả HOLD, chưa chạy solver |
| macOS arm64 release | HOLD | Chỉ có QA lịch sử giới hạn |
| macOS Intel release | HOLD | Chưa có Intel host/evidence |

`overlay_v7.py` phụ thuộc Win32 và không thể dùng trực tiếp trên macOS. Entry
Mac dùng `src/remix_duo/entry.py`, `ui/overlay.py` và `ui/workspace.py`. Native
overlay hiện là shell/monitor fail-closed; khi chưa có TF/Fs/trục được xác minh,
nó luôn báo HOLD và không vẽ SUM/MagEQ/FIR. Offline Workspace xử lý TRF lưu được
nhưng không thay thế workflow live của Smaart.

Ngoài ra capture native yêu cầu macOS 14+, trong khi package khai báo tối thiểu
macOS 13. macOS 13 hiện chỉ nên được coi là offline; cần nâng yêu cầu native
overlay lên 14 hoặc bổ sung adapter tương thích 13.

`ui/workspace.py` vẫn shutdown executor với `wait=False`. Hai executor geometry
và selection trong `ui/native_monitor.py` cũng dùng cùng kiểu teardown không
đợi. Cần deadline hữu hạn như Windows trước khi chấp nhận crash/quit stability
trên Mac; không được biến thành chờ vô hạn khi Qt đang đóng.

## Thứ tự triển khai đề nghị

1. P0: đưa state/actions Auto Phase/EQ/FIR và các mặc định UI mới vào controller
   shared, không copy solver theo platform.
2. P0: hoàn tất nguồn TF live tin cậy trên Mac, ánh xạ tick thật và hiệu chuẩn
   Fs/trục; thiếu evidence phải tiếp tục fail closed.
3. P0: nối shared solvers vào native overlay Mac, gồm preview/provenance/export.
4. P1: mở rộng source digest và thay receipt tự khai bằng evidence có attestation.
5. P1: đồng bộ version/dependency lock; build/test riêng arm64 và x86_64.
6. P1: Developer ID, notarization, clean install và live Smaart acceptance cho
   từng architecture; không suy diễn Intel PASS từ arm64.
7. P2: sửa macOS 13/14 contract, bounded worker teardown và telemetry label.

## Trạng thái bàn giao

- Exact source audited: `windows_v8_87_MAC_OVERLAY_QA`.
- Changed product code: none.
- Unit/contract: 66 PASS.
- Native arm64: historical limited PASS; current full native workflow HOLD.
- Native Intel: HOLD.
- Public signed/notarized release: HOLD.
- Runtime restart: không cần; không thay đổi code chạy.
