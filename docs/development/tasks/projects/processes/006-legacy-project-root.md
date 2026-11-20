# Giữ thư mục đã lưu khi bỏ ô thư mục node

## PROC-007

- [x] Sửa regression của PROC-006: Project cũ chưa có root nhưng node đã lưu cwd bị chặn khi lưu/mở Run.
- Migration 023 chuyển root đã lưu từ cấu hình node hiện tại (fallback định nghĩa legacy gần nhất) sang Project đang trống, chỉ khi các root cùng Project thống nhất và là đường dẫn tuyệt đối. So sánh không phân biệt chữ hoa/thường, bỏ dấu phân cách cuối; không ghi đè root Project đã chọn. Nhiều root khác nhau hoặc không có root thì không đoán theo Skill/topic.
- Không thay node, snapshot, Run, model, PC, file Skill hay output. API và form node không đổi; không thêm lại ô thư mục.
- Kiểm chứng: `.venv\Scripts\python.exe -m pytest apps/server/tests/integration/projects/test_project_root_upgrade.py apps/server/tests/integration/projects/test_current_configuration.py apps/server/tests/integration/projects/test_topic_run.py apps/server/tests/integration/persistence/test_sqlite_foundation.py -q` đạt **42 passed**. Test upgrade từ schema 22 kiểm cấu hình current/legacy, không đụng Project đã cấu hình, không tự chọn khi conflict/thiếu và giữ nguyên JSON cũ.
- Server local đã lên schema 23; Project thực tế nhận lại `E:\PhuongCH\AI\AgentCF\tests`. GET run-context của Process trả 200, topic_supported=true, đúng root/PC. Không tạo Run hoặc gọi model để kiểm tra lỗi này; các lỗi CLI/model/mạng đã ghi nhận riêng không được coi là đã giải quyết bởi thay đổi này.
