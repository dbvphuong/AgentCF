# 0004 - SQLite cho database nghiệp vụ giai đoạn local

- Status: Accepted
- Date: 2026-11-16

## Context

Agent CF đang chuẩn bị Chặng 3: Web → Server → Client chạy Skill 0 và xem lại kết quả đã lưu. Giai đoạn này phục vụ một người dùng trên một máy, ưu tiên dễ cài, dễ chạy và ít thành phần phải quản lý. Chưa có schema, migration hoặc database nghiệp vụ được triển khai.

ADR 0001 ban đầu đề xuất PostgreSQL. Sau khi so sánh, chủ dự án đã xác nhận chọn SQLite để dễ triển khai hiện tại, đồng thời muốn giữ khả năng chuyển sang PostgreSQL khi cần chạy tập trung hoặc mở rộng.

## Decision

Chọn **SQLite làm database nghiệp vụ của Agent CF cho giai đoạn chạy local**, bắt đầu từ Chặng 3. Quyết định được chấp thuận bởi chủ dự án; Accepted không có nghĩa database đã được tạo hoặc tích hợp.

- Server sở hữu kết nối và thao tác database. Web và CF Client giao tiếp qua API/hợp đồng, không mở trực tiếp file SQLite hoặc chia sẻ file DB giữa các PC qua mạng.
- Lưu dữ liệu nghiệp vụ có cấu trúc như cấu hình Process/version, lần chạy, trạng thái, quyết định và tham chiếu kết quả theo schema thực tế được triển khai từng chặng. Không coi danh sách này là schema đã có; không đưa nội dung video/audio lớn vào DB.
- File DB và các file phụ trợ nằm trong vùng dữ liệu runtime local, ngoài Git; đường dẫn phải cấu hình được khi có config schema. Chưa chốt tên file, biến môi trường, ORM hoặc thư viện migration ở thay đổi tài liệu này.
- Truy cập DB nằm ở lớp infrastructure, qua các interface/use case đã xác định. Domain không phụ thuộc SQLite; không đưa SQL vào UI hoặc handler thay cho lớp lưu trữ.
- Có schema/migration theo phiên bản và kiểm thử persistence. Transaction phải ngắn; không giữ transaction mở trong lúc chờ Codex/Antigravity, tool hoặc quyết định duyệt.
- Khi triển khai, xác định rõ kiểm tra foreign key, xử lý tranh chấp ghi, thời gian chờ khóa và chế độ journal/WAL phù hợp; kiểm thử thay vì mặc định SQLite đáp ứng mọi mức đồng thời.

**Phạm vi chỉ là database nghiệp vụ Agent CF.** Quyết định này không chọn SQLite làm persistence của Temporal. Engine Temporal và cách triển khai/lưu trữ của nó vẫn theo [ADR 0003](0003-process-engine-temporal.md), đang Proposed và chưa được kiểm chứng.

## Consequences

- Không phải cài hoặc vận hành dịch vụ PostgreSQL để bắt đầu lưu dữ liệu nghiệp vụ local. SQLite vẫn cần được tích hợp và kiểm thử trong Server; thay đổi này chỉ ghi quyết định.
- Dữ liệu nằm trong file thuận tiện cho triển khai một máy; phải có quy trình sao lưu/khôi phục nhất quán khi ứng dụng đang dùng DB, không coi chép riêng file đang mở là bản backup đã được xác minh.
- SQLite chỉ cho một writer tại một thời điểm. Khi nhiều worker hoặc Server cùng ghi gây chờ khóa đáng kể, hoặc cần DB tập trung qua mạng, đánh giá chuyển sang PostgreSQL; không đặt ngưỡng số Run tùy ý khi chưa đo tải thực tế.
- Tách phần truy cập dữ liệu và giữ schema có ràng buộc giúp giới hạn phạm vi chuyển đổi sau này, nhưng không đảm bảo chỉ đổi connection string là hoàn tất.

### Hướng chuyển sang PostgreSQL

Khi có nhu cầu được xác nhận, tạo ADR mới và kế hoạch chuyển đổi gồm:

1. Đối chiếu kiểu dữ liệu, khóa/ràng buộc, SQL và hành vi transaction của schema đang có.
2. Tạo migration/schema đích và cập nhật phần truy cập DB cùng config tương ứng.
3. Sao lưu, chuyển dữ liệu và đối soát ID, quan hệ, version, số bản ghi cùng lịch sử chạy; có phương án quay lại nếu chuyển đổi lỗi.
4. Chạy lại test persistence và các luồng tạo/xem Run, đồng thời ghi, khôi phục; không tuyên bố tương thích chỉ vì dùng ORM.

## Alternatives considered

- **PostgreSQL ngay từ đầu:** phù hợp khi có nhiều bên ghi đồng thời hoặc triển khai tập trung, nhưng thêm dịch vụ, kết nối và công vận hành cho nhu cầu một máy hiện tại. Giữ làm hướng mở rộng, không phải database mặc định của giai đoạn này.

## References

- [SQLite: Appropriate Uses](https://www.sqlite.org/whentouse.html)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [PostgreSQL: Architectural Fundamentals](https://www.postgresql.org/docs/current/tutorial-arch.html)
- [Cấu trúc source code](../../development/project-structure.md)
