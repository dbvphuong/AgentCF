# Thư mục làm việc chỉ cấu hình ở Project

## PROC-006

Regression dữ liệu cũ chưa có root Project được sửa bằng migration 023 tại [PROC-007](006-legacy-project-root.md), giữ nguyên ô thư mục node đã bỏ.

- [x] Bỏ ô thư mục node, dùng root Project trong luồng hiện tại và giữ snapshot cũ; Server local đã nạp thay đổi, health schema 22 đạt.

- Yêu cầu: bỏ ô thư mục trong node AI; gọi Skill cho chủ đề, Skill quyết định output theo quy trình gốc.
- Form node không có `working_directory`; sửa node bỏ override cũ. Luồng cấu hình hiện tại lấy cwd từ Project khi kiểm tra/chụp snapshot, kể cả node cũ còn giá trị riêng. Run vẫn chọn thư mục chủ đề có sẵn, không là cấu hình output và không đổi cwd.
- API lifecycle cũ và snapshot Run cũ giữ nguyên, không migration hay sửa lịch sử. Không thêm thư mục output hoặc ghi chat thay file.
- Kiểm chứng: `.venv\Scripts\python.exe -m pytest apps/server/tests/integration/projects/test_current_configuration.py apps/server/tests/integration/projects/test_topic_run.py -q` đạt **15 passed**; TypeScript/Vite build đạt. Regression kiểm node còn override cũ vẫn dùng root Project, đổi root chỉ ảnh hưởng lần chạy mới, snapshot cũ giữ nguyên. Thiếu root báo rõ cần cấu hình ở Sửa Project.
- Đối chiếu model theo yêu cầu cùng lượt: Web lưu `gpt-6.1-sol`; config local cũng là `gpt-6.1-sol`/`medium`, auth ChatGPT. Client tìm `codex.cmd` npm 0.147.0, trong khi IDE dùng `codex.exe` 0.164.0-alpha.11.1. Log CLI cũ báo model unsupported và không đọc được cache schema của client 0.164.0. Không đổi Model ID hoặc kết luận tài khoản nói chung không có model chỉ từ log bản cũ.
