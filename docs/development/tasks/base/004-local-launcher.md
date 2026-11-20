# Launcher local trên Windows

[Module](README.md) · [Hướng dẫn chạy](../../setup.md#chạy-nhanh-trên-windows)

## BASE-005

- [x] **BASE-005 — run.bat khởi động Web/Server để xem giao diện local** — Xong | Infrastructure
  - Yêu cầu: double-click file tại root để khởi động và mở Web local, không cần nhập lệnh riêng cho từng ứng dụng.
  - Thực hiện: `run.bat` gọi `infra/start-local.ps1`; kiểm tra `.venv`, Node.js 24 và dependency, khởi động Server/Vite trong tiến trình ẩn, đợi health và proxy trước khi mở trình duyệt. Log riêng từng lần chạy, Enter dừng cây tiến trình chỉ do launcher sở hữu. Tái sử dụng cặp Server/Web đang sẵn sàng; cổng dịch vụ khác bị chiếm thì báo lỗi, không dừng tiến trình có sẵn. Hỗ trợ đổi cổng đồng bộ và CheckOnly/NoBrowser.
  - Phạm vi: UI local, Temporal tắt cho tiến trình mới; worker/Client cấu hình riêng. Không tự cài dependency, seed dữ liệu, xóa DB, ghép nối PC hay thực thi model. DB/artifact từ environment được giữ nếu có; mặc định theo cấu hình Server.
  - Kiểm chứng 2026-11-17:
    - `cmd.exe /c run.bat -CheckOnly` đạt; gọi bằng đường dẫn tuyệt đối từ thư mục ngoài repo cũng đạt.
    - `powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File infra/start-local.ps1 -SmokeTest -NoBrowser -ServerPort 18083 -WebPort 5181 -DatabasePath <DB-tạm-riêng>` đạt Web → proxy → Server → SQLite, không dùng DB thật. Sau smoke không còn listener ở hai cổng này.
    - Giữ listener riêng ở cổng 18084 rồi chạy launcher: trả exit code 1, thông báo cổng bị chiếm; listener cũ vẫn được giữ.
    - Chạy trực tiếp `run.bat -SmokeTest -NoBrowser` với DB tạm có dấu cách trong đường dẫn đạt; PowerShell parser không có lỗi, `git diff --check` đạt.
  - Giới hạn: smoke không mở trình duyệt mặc định để tránh bật cửa sổ tương tác trong kiểm thử; nhánh mở trình duyệt dùng URL đã qua readiness. Không nghiệm thu Temporal/worker/Client hoặc tải runtime thật tại task này.
