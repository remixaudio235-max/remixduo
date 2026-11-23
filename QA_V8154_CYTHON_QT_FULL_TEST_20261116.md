# RemiX Duo V8.150 RC1 — V8.154 Cython/Qt crash QA (2026-11-16)

## Phạm vi
- Máy: DESKTOP-VNPRJCI
- Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_150_RELEASE_RC1
- Smaart Suite lúc bắt đầu: PID 31564, HWND 722050; chuyển sang PID 31624, HWND 1245598 trong phiên QA (nguyên nhân chưa xác định)
- RemiXDuo frozen EXE mới: PID 7632, build 14:08:04, source manifest SHA-256 khớp
- Bản EXE và installer trước vá đã được lưu riêng trong dist\archive_pre_v8154_slot_fix_20261116

## Kết quả xác minh
- Cython/Qt targeted: 8 passed
- Canonical pytest: 114 passed, 4 skipped
- Full pytest: 806 passed, 54 skipped, 1 failed
- FAIL: test_v867_mageq_amber_glass.py::test_offline_paint_no_unbounded_cost_and_save_preview, CPU P95 35.94 ms > 33.33 ms, wall P95 4.73 ms; chạy lại riêng file: 4 passed
- Rebuild: 26 protected .pyd, PyInstaller EXE / watcher / setup hoàn tất; 7 frozen self-check trong build script exit 0
- Live frozen EXE: launch PID 7632; VERIFY_ACTIVE_BUILD.py GUARD PASS; Qt dock/toolbar Auto Phase/Auto EQ/Auto FIR quan sát được trên Smaart
- Native click AUTO PHASE: click đã gửi, RemiXDuo vẫn sống, log phiên PID 7632 không có TypeError / V8154_QT_CALLBACK_EXCEPTION
- Log trong phiên EXE mới: 1 V8152_AUTOEQ_PREVIEW_READY; 3 V8124_FIR_OK; 5 V7_SUM_RENDER_READY
- 4 mẫu theo dõi mỗi 5 giây: RemiXDuo PID 7632 đều Responding=True, handles 1845 ổn định, RAM ~338-341 MB; Smaart PID 31624 Responding=True, handles ~826-827
- Windows Application Error Event ID 1000 sau 14:08:00 cho Smaart/RemiXDuo/Qt6Core: không ghi nhận
- Manifest _remixduo_native source SHA: b902f6fb49e7d4a7f53f583d356f305cdfd95a1214db820e92ad815765bb5e23
- EXE SHA256: C798BD8CA417DCFEFD246A0B98A8AAB15D19389A24C23EB9D60F12CBB62399A7
- Installer SHA256: 93AB75CA6685609C9B925E9718B083941B87FCEFA6CAEDC368CA0CE00957CB7D
- Installer Authenticode: NotSigned

## HOLD / hạn chế
1. Auto Phase: regression lỗi callback/crash PASS, nhưng kết quả tính toán Top-3 và hình hiển thị native chưa được nghiệm thu trực quan.
2. Auto EQ/FIR: engine tạo preview/taps theo log, chưa có chứng cứ so sánh hoàn chỉnh đáp tuyến thực tế / xuất file.
3. Có 86 dòng V73_ROI_DRAG trong log EXE mới trong khi môi trường UIA/foreground không ổn định. Không xác định nguồn thao tác. Log không tăng thêm ở mẫu 5 giây; dừng click_input để tránh sửa ROI ngoài ý muốn.
4. Smaart đổi PID/HWND trong phiên QA, chưa rõ nguyên nhân; cần kiểm thử lại không có tác vụ giao diện khác tranh foreground.
5. Full pytest benchmark CPU P95 không đạt một lượt, dù chạy độc lập đạt: cần kiểm tra hiệu năng dưới tải.
6. Installed clean-VM install/uninstall và Authenticode chưa PASS. **KHÔNG phát hành installer** trước khi nghiệm thu các mục trên và ký số.

## Kiểm thử tiếp theo
- Dành một phiên Smaart GUI không bị ứng dụng khác chiếm foreground; chụp trước/sau native Auto Phase Top-3 và Δ SUM, xác nhận 2 trace và ROI không tự di chuyển.
- Auto EQ: chọn 1 trace, nhấn Auto EQ, xác nhận MagEQ và 8 PEQ (nếu có), xuất và tái nhập để so khớp.
- Auto FIR: tạo preview, kiểm tra Phase+/OFF, taps, lưu file và đối chiếu nội dung.
- Lặp benchmark MagEQ 3 lần ở trạng thái tải thấp/và thực; đo P95 CPU / wall.
- QA installer trên VM sạch và ký số trước khi phát hành.
