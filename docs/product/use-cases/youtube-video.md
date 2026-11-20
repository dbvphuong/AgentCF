# Use case: Sản xuất video YouTube

> Status: Draft  
> Last updated: 2026-11-16  
> Owner: Product

## Nhu cầu người dùng đã mô tả

Người dùng hiện làm thủ công, kết hợp Codex, Google Antigravity (gọi tắt agy), Gemini, các Skill và tool có sẵn. Muốn xây hệ thống thật; dựng HTML trước vì cần nhìn rõ cách quản lý. Không dừng ở bản mockup và không yêu cầu toàn bộ quy trình tự động ngay từ đầu.

Tool đã có: bình thường người dùng nạp input, chạy tool, lấy output. Nhu cầu chính là Agent điều khiển/giám sát các tool đó. Tool lỗi thì Agent xử lý nếu nằm trong khả năng và quyền đã cấp; không xử lý được thì báo người dùng. Chưa có tên chương trình, lệnh chạy, đường dẫn hoặc hợp đồng input/output của từng tool trong repository; không tự suy đoán các giá trị này.

Xác nhận 2026-11-18: Web thay người giao việc/điều khiển PC; **quy trình Skill giữ nguyên**, output thật vẫn nằm trên PC, gồm ảnh, file chỉnh sửa, file/thư mục mới và các loại kết quả khác. Skill local dùng đường dẫn tuyệt đối tới file gốc, nhập/dán trên Web; demo dùng thư mục `tests` trên PC hiện tại. Quy tắc chuẩn nằm tại [requirements](../requirements.md#giữ-quy-trình-và-output-trên-pc).

## Luồng hiện đang làm

| Bước | Cách làm người dùng mô tả | Điểm cần giữ khi thiết kế |
|---|---|---|
| 1. Plan chủ đề | Skill phân tích YouTube, đề xuất chủ đề; người dùng chỉnh/duyệt vì chất lượng chưa ổn định | Có người can thiệp, không tự duyệt plan bằng nhãn thành công của Agent |
| 2. Cốt truyện | Gọi Skill trên Agent tạo cốt truyện | Lưu bản dùng làm gốc cho các ngôn ngữ |
| 3. Nội dung dài | Tool chạy nhiều luồng vào Gemini, tiếp tục các part bằng thao tác “1”; người dùng dùng cách này do tốc độ/quota khi viết bằng Agent | Giữ tích hợp tool hiện có, quản lý đủ part/ngôn ngữ |
| 4. Dọn và review | Tool dọn nội dung, sau đó Agent dùng Skill review | Giữ nội dung trước/sau và nhận xét review |
| 5. Voice | Tool tạo giọng bằng ElevenLabs | Gắn audio đúng bản nội dung/ngôn ngữ |
| 6. Timeline | Tool tạo phụ đề/timeline, người dùng gọi “str” | Cần xác nhận có phải SRT và cấu trúc file thực tế; không tự chốt định dạng |
| 7. Prompt media | Agent dùng Skill tạo prompt ảnh/video | Gắn prompt với cảnh và nội dung tương ứng |
| 8. Media | Tool đưa prompt vào Flow tạo ảnh/video | Theo dõi đầu vào, đầu ra và phần bị lỗi/thiếu |
| 9. Dựng video | Tool nhận MP3, ảnh, video để dựng | Thu output video và lỗi của tool |
| 10. Thumbnail | Skill tạo ảnh bằng Agent | Khả năng ảnh/model/skill thực tế phải kiểm chứng |
| 11. Đăng | Người dùng tự đăng, dùng GPM quản lý đăng nhập; dự kiến sau này dùng tool và tự bấm bước cuối | Đăng tự động chưa có; giữ người dùng xác nhận cuối |

Bảng là mô tả nghiệp vụ, không khẳng định mọi bước đã có API hoặc adapter tự động. Chưa quyết định một video là một ProcessRun hay một batch nhiều ngôn ngữ là một ProcessRun.

## Ý nghĩa với Agent CF

- Agent quản lý công việc có thể dùng runtime Codex, Antigravity hoặc adapter khác; tên Agent nghiệp vụ không đồng nghĩa tạo một ứng dụng AI mới từ đầu.
- Robot trên UI là chương trình độc lập; tool người dùng gọi ở đây cần kiểm kê trước để xác định bọc thành Robot hay Tool nội bộ của Skill. Chưa tự phân loại tất cả.
- Giữ sự khác biệt giữa chương trình chạy xong, output hợp lệ và chất lượng được duyệt.
- Có khả năng chờ người dùng, nhận hướng dẫn bổ sung và tiếp tục đúng phần được phép.
- Thiết kế cần cho phép giữ kết quả đạt và xử lý lại phần lỗi, không buộc chạy lại cả video/batch. Hợp đồng retry/resume/version chưa chốt.
- Mọi lần xử lý lỗi phải có giới hạn, lịch sử và báo cáo; không tự retry vô hạn hoặc tự sửa chương trình/tool ngoài quyền.
- Tổng token tháng là yêu cầu UI hiện tại. Usage thực tế của CLI/tài khoản có thể không đầy đủ; không hứa hiển thị đủ chỉ từ việc gọi được Agent.

## Thử nghiệm đầu tiên cần thiết

Mốc tích hợp đầu tiên của ứng dụng là chạy riêng Skill 0 bằng Codex qua Web, lưu và xem lại cốt truyện ([RUN-006](../../development/tasks/runs/003-skill0-web.md#run-006)); không yêu cầu Agent tự gọi tool ghi file để công nhận mốc này. Luồng ba Skill có Agent duyệt được triển khai tiếp ở [RUN-007](../../development/tasks/runs/004-skill-chain.md#run-007). Phạm vi chuẩn tại [requirements](../requirements.md#cấu-hình-node-dùng-runtime-local), thứ tự tại [plan](../../development/implementation-plan.md#thứ-tự-đến-mốc-dùng-được-đầu-tiên).

Với thử nghiệm tích hợp **tool bên ngoài** tiếp theo, chọn một tool hiện có, một bộ input an toàn và một runtime Codex hoặc Antigravity đã kiểm chứng trên PC. Chứng minh Web giao việc → CF Client gọi Agent → Agent gọi tool → thu output/log → hiển thị kết quả. Thử lỗi rõ ràng để Agent báo lại khi không xử lý được. Không dùng bước đăng video làm thử nghiệm đầu tiên có side effect.

Chọn tool và runtime cần dựa vào môi trường thực tế, không mặc định có sẵn ở máy khác. [Kế hoạch triển khai](../../development/implementation-plan.md) quy định các mốc tiếp theo.

## Thông tin cần bổ sung trước khi thử tool thật

- Tool nào thử trước; executable/script/API, cách gọi, input mẫu và output mong đợi.
- Chạy tự động được tới đâu, có cần cửa sổ, browser/profile, bước xác nhận hoặc phiên đăng nhập không.
- Phiên bản CLI Codex/Antigravity, cách đăng nhập, Skill và các dependency ngoài repository.
- Dấu hiệu hoàn thành, lỗi, timeout; tool có lệnh hủy và hỗ trợ chạy lại an toàn không.
- Đơn vị công việc: video/ngôn ngữ/part/cảnh; cách định danh và quản lý file trên nhiều máy.
- Những lỗi Agent được tự xử lý, giới hạn lần thử/thời gian và trường hợp phải hỏi người dùng.

Không đưa tài khoản, khóa, cookie hoặc profile GPM thật vào tài liệu/repository.
