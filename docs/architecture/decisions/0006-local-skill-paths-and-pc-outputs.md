# 0006 - Skill từ đường dẫn local và output gốc trên PC

- Status: Accepted
- Date: 2026-11-18

## Context

Người dùng xác nhận Web thay người điều khiển Codex/Antigravity/tool, giữ nguyên quy trình Skill. Skill có thể tạo ảnh, sửa hoặc tạo nhiều loại file; output gốc phải ở PC để các bước sau sử dụng trực tiếp. Người dùng chọn cách nhập/dán đường dẫn tuyệt đối tới `SKILL.md`, không upload/copy nội dung lên Web. Demo chạy tại `E:\PhuongCH\AI\AgentCF\tests`.

## Decision

- Bổ sung chế độ Skill local bên cạnh Skill nội dung/bundle hiện có. Version local giữ đường dẫn tuyệt đối `source_path` và PC sở hữu `source_runner_id`; node ghim cùng PC và `working_directory` tuyệt đối. Server không mở file trên đĩa của PC hoặc biến đường dẫn đó thành URL tải file.
- Publish đóng băng tham chiếu đường dẫn, PC, cấu hình runtime và thư mục chạy. Mỗi Attempt đọc **file gốc tại đường dẫn đó ở thời điểm chạy**, giữ tài nguyên tương đối bên cạnh Skill; Client ghi hash nội dung thực tế đã đọc. Sửa file gốc ảnh hưởng lần chạy sau, không viết lại bằng chứng lịch sử. Đây là ngoại lệ có chủ đích đối với yêu cầu đóng băng toàn bộ nội dung bundle trong ADR 0005; các chế độ cũ giữ nguyên.
- Client gọi runtime bằng công cụ của runtime và quyền ghi trong thư mục làm việc, để Skill tạo/sửa file theo quy trình gốc. Phản hồi chat hoặc `--output-last-message` chỉ là báo cáo/log, không được lưu thay output nghiệp vụ để giả làm Skill đã gọi tool.
- Output gốc được giữ tại PC. Client gửi metadata tham chiếu PC/đường dẫn/kích thước/hash và trạng thái; upload bản sao lên Server là tùy chọn, không phải điều kiện thành công của chế độ local. Không coi đường dẫn trên PC A là file sẵn có trên PC B.
- Thiếu Skill, sai PC, thư mục không hợp lệ hoặc runtime không hỗ trợ phải lỗi rõ ràng; không fallback sang Skill snapshot inline, runtime khác hoặc tự tạo nội dung thay runtime. Việc phát hiện file output và điều kiện nghiệm thu phải dựa trên file thực tế.

## Consequences

- Người dùng dùng lại cấu trúc thư mục/tool/Skill hiện có, có thể tiếp tục thao tác bằng ứng dụng trên PC.
- Không hứa tái lập nguyên trạng file ngoài hệ thống: hash tại Attempt là bằng chứng nội dung đã dùng, không bảo đảm file tại đường dẫn chưa thay đổi sau đó.
- Cần kiểm chứng từng adapter cho thao tác file/tool thật; thành công với Codex chưa chứng minh Antigravity hay mọi tool khác đã hoạt động.
- Quyền filesystem và quy trình ngoài thư mục làm việc cần cấu hình/kiểm chứng riêng; không tự mở rộng quyền hoặc sửa Skill để vượt sandbox.

## Alternatives considered

- Upload và lưu mọi output trên Web: không giữ quy trình dùng tool/file trên PC.
- Copy nội dung Skill thành prompt rồi lưu phản hồi cuối thành file: không chứng minh runtime thực thi thao tác của Skill.
- Chọn file bằng browser upload: browser không cung cấp đường dẫn tuyệt đối đáng tin cậy trên PC Client. Người dùng chọn ô nhập/dán đường dẫn.
