# 0009 - Ngữ cảnh chủ đề chung cho lần chạy Skill local

- Status: Accepted
- Date: 2026-11-19

## Context

Người dùng mở thư mục Project trong CLI, gọi các Skill lần lượt cho cùng chủ đề đã có thư mục. Web cần thay thao tác giao việc, không bắt khai báo JSON, tự tạo lại thư mục hoặc đổi quy trình/output PC.

## Decision

- Project giữ root làm việc tùy chọn. Node có thể có cấu hình riêng; Publish giải quyết default rồi ghim vào snapshot, không đổi lịch sử sau khi sửa Project.
- Mỗi Run có thể chọn `topic_directory` và yêu cầu riêng. Server dẫn xuất tên chủ đề từ tên thư mục, kiểm path và yêu cầu cùng PC/root cho các bước local. Cwd vẫn là root, ngữ cảnh chủ đề đi cùng input của mọi node.
- Client mới kiểm thư mục đã tồn tại và resolve trong root trước gọi tool. Dùng Skill gốc/ref và file thật; không hard-code cách tạo sản phẩm theo tên Skill hay ghi chat thành output.
- Duyệt thư mục là thao tác metadata qua Client/heartbeat hiện có, không thực thi model/Run. Generic Process vẫn có JSON nâng cao; topic context không thay thế engine mapping tổng quát hoặc vòng Agent API còn thiếu.

## Consequences

- Người dùng chọn một thư mục chủ đề cho cả lần chạy. Không phải nhập lại từng node hoặc tự nối JSON cho quy trình trao đổi file này.
- Chủ đề phải là thư mục con root đã có; multi-PC/root cần cấu hình khác, không tự suy đường dẫn hoặc mở rộng sandbox. Kết quả và kiểm file thật nằm trên PC; Published snapshot tiếp tục bất biến.
- Input lưu trong Run nên retry/restart dùng lại đúng chủ đề; UI metadata phải phân biệt root làm việc với thư mục chủ đề.

## Alternatives considered

- Đổi cwd thành thư mục chủ đề: khác thao tác mở Project thủ công, có thể ảnh hưởng Skill/ref/tool config.
- Lặp chủ đề/mapping ở mọi node: dễ sai và gây gánh nặng cấu hình.
- Đọc đường dẫn PC bằng Server: sai máy khi chạy từ xa.
