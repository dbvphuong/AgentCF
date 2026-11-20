# 0005 - Process động, snapshot và giao việc có đối soát

- Status: Accepted
- Date: 2026-11-16

## Context

Phạm vi được giao là hoàn thiện BASE-001 → PROC-001, REL-004 → RUN-001 → API-001 cho hệ thống quản lý tổng và Process động, chưa triển khai ứng dụng. Skill 0–1–2 là dữ liệu kiểm thử, không phải loại Task hoặc đồ thị cố định trong engine. Domain và execution cũ còn bỏ ngỏ snapshot, mapping, lease và nguồn trạng thái.

## Decision

Chấp thuận thiết kế trong phạm vi task được giao, dựa trên stack/Client/Temporal tại ADR 0001–0003 và SQLite nghiệp vụ tại ADR 0004. Đây là quyết định thiết kế, chưa có bằng chứng chạy tích hợp.

- Một bộ thông dịch DAG có `definition_format_version` và `interpreter_version` chạy mọi ProcessVersion hợp lệ. Không sinh code Workflow từ mỗi graph và không phân nhánh engine theo tên Skill. Chưa hỗ trợ condition, loop, process lồng nhau hoặc node Human.
- Publish đóng băng execution snapshot của Agent, runtime/model, hướng dẫn, Skill bundle và Tool/Robot contract; dùng SHA-256 kiểm tra nội dung. Không chọn version hóa toàn bộ catalog Agent ở giai đoạn này. Secret chỉ được phân giải từ credential binding tại phía tin cậy, không có trong snapshot/history.
- JSON Schema 2020-12 mô tả input/output. Mapping khai báo bằng nguồn `run_input`, `task_output` hoặc `literal` cùng JSON Pointer; không dùng expression, template chạy mã hoặc shell. Đích là các trường cấp đầu của input object. Nguồn Task phải là tổ tiên trong DAG. Schema và mapping là dữ liệu, không phải code tùy ý.
- Server là bên duy nhất ghi SQLite nghiệp vụ, kể cả worker: Activity gọi interface nội bộ có xác thực của Server. Workflow chỉ chứa quyết định xác định, ID và tham chiếu; không đọc DB hoặc gọi PC trực tiếp.
- SQLite là nguồn chuẩn của định nghĩa, run, trạng thái công bố, quyền thực thi, inbox/outbox và artifact metadata. Temporal history là nguồn lịch sử điều phối/replay; không đồng bộ hai chiều bằng cách ghi đè DB từ trạng thái UI hoặc từ một snapshot engine.
- Ghi thay đổi nghiệp vụ và outbox trong cùng transaction. Relay gửi lệnh engine ít nhất một lần. Workflow ID ổn định theo ProcessRun; không cho tạo lại một Workflow đã đóng bằng cùng ID. Command có ID, sequence và revision; Activity áp dụng có inbox và compare-and-set nên replay/gửi lại không tạo side effect nghiệp vụ mới. Lệnh hoàn tất phải ghi DB trước khi Workflow đóng.
- Client dùng HTTPS để claim/renew/report; WebSocket chỉ thông báo có việc hoặc có thay đổi, không mang quyền khởi chạy. CF Client không là Temporal Worker, không có quyền mở DB hoặc kết nối Temporal.
- Quyền thực thi ràng buộc Runner/session/TaskRun/Attempt/generation, token ngẫu nhiên chỉ lưu hash ở Server. Expiry ngăn sử dụng quyền cũ nhưng không chứng minh chương trình đã dừng. Chưa rõ kết quả thì giữ `reconciling`, chặn giao lại và chặn terminal thành công giả. Kết quả đến muộn chỉ là bằng chứng đối soát.
- Client giữ journal bền vững trước khi spawn, khử trùng theo Attempt, không tự spawn lại sau crash hoặc nhận thông báo lặp. Fencing bảo vệ ghi trạng thái của Agent CF; không bảo đảm exactly-once đối với dịch vụ/tool bên ngoài.

Chi tiết dữ liệu nằm tại [domain](../domain-model.md#định-nghĩa-process-động-và-snapshot), state machine và bảng tình huống tại [execution](../execution-model.md), HTTP tại [OpenAPI](../../../openapi/openapi.yaml), quy tắc Client tại [contract](../client-protocol.md). Không duy trì enum hoặc schema bản sao ở ADR.

## Consequences

- Đổi tên/sửa catalog không làm thay đổi run cũ; policy hiện tại vẫn có thể thu hẹp quyền trước dispatch.
- Phải triển khai inbox/outbox, CAS và journal trước khi giao việc thật; retry của Activity hạ tầng không được biến thành retry chương trình trên PC.
- Khi không chứng minh được tiến trình cũ đã dừng, hệ thống ưu tiên chặn giao lại. Recovery đầy đủ và thao tác giải quyết của người dùng thuộc REL-001/REL-003.
- API thiết kế cho số Task bất kỳ trong giới hạn vận hành được cấu hình; giao diện editor và catalog vẫn có task triển khai riêng. Các Task loại Robot có hợp đồng chung nhưng adapter Robot chưa được nghiệm thu.
- Thay đổi interpreter phải giữ khả năng chạy/replay version cũ hoặc có ADR migration; không nạp graph mới vào run đang chạy.

## Alternatives considered

- Hard-code Skill 0 → 1 → 2: không đáp ứng Process động và dễ nhầm mốc test với kiến trúc sản phẩm.
- Chỉ tham chiếu Agent/Skill mutable: không đủ lịch sử và kiểm tra tính toàn vẹn.
- Ghi DB rồi gọi engine ngay trong HTTP mà không outbox: mất lệnh khi crash giữa hai bước.
- Để Client nhận Activity trực tiếp từ Temporal: tăng bề mặt truy cập hạ tầng và không thay thế quyền/journal phía PC.
- Tự giao lại khi lease hết hạn: có thể tạo hai tiến trình và lặp side effect.
