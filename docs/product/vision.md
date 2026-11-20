# Tầm nhìn sản phẩm Agent CF

> Status: Draft  
> Last updated: 2026-11-13  
> Owner: Product

## Trạng thái hiện tại

Agent CF đang ở giai đoạn xác định sản phẩm và kiến trúc. Tài liệu này mô tả định hướng cần kiểm chứng, không khẳng định các khả năng bên dưới đã được triển khai. Repository hiện chưa có ứng dụng Agent CF có thể build hoặc chạy.

## Vấn đề cần giải quyết

Việc phối hợp nhiều AI agent thường bị phân tán giữa prompt, script, công cụ và log riêng lẻ. Người vận hành khó trả lời nhất quán các câu hỏi:

- Công việc lớn đang được chia thành những bước nào và phụ thuộc nhau ra sao?
- Agent nào chịu trách nhiệm cho từng bước và được phép dùng công cụ nào?
- Một lần chạy đang ở đâu, đã dùng đúng phiên bản process nào và lỗi tại bước nào?
- Có thể kiểm tra lại input, output và lịch sử thực thi mà không ghép dữ liệu từ nhiều nơi hay không?

Agent CF hướng tới việc tập trung các thông tin này thành một mô hình có thể thiết kế, chạy và quan sát được.

## Tầm nhìn

Agent CF là không gian điều phối công việc cho AI agent theo mô hình một công ty: người dùng tổ chức mục tiêu thành project, mô tả cách thực hiện bằng process có version, giao từng task cho agent và theo dõi từng lần chạy bằng lịch sử rõ ràng.

Mục tiêu là sản phẩm thật. HTML chỉ là bước thống nhất giao diện trước triển khai. [Quy trình YouTube hiện người dùng đang làm](use-cases/youtube-video.md) là use case đại diện: Agent dùng Codex/Antigravity điều khiển tool có sẵn, giám sát output, xử lý lỗi trong phạm vi cho phép và báo người dùng khi cần can thiệp. Không đặt điều kiện phải tự động end-to-end ngay từ đầu mới có giá trị.

Sản phẩm ưu tiên khả năng hiểu và kiểm soát việc thực thi trước mức độ tự động hóa. Người dùng phải biết hệ thống sắp làm gì, đang làm gì, đã làm gì và vì sao một lần chạy thành công hoặc thất bại.

Web thay người điều khiển Codex/Antigravity/tool trên PC và giữ nguyên quy trình Skill. Output gốc ở PC để tiếp tục làm việc bằng tool/file hiện có; upload hay preview trên Web là tùy chọn. Chi tiết cấu hình Skill bằng đường dẫn tuyệt đối và thư mục làm việc nằm tại [requirements](requirements.md#giữ-quy-trình-và-output-trên-pc).

## Người dùng mục tiêu

### Người thiết kế process

Người chuyển một quy trình công việc thành các task, khai báo quan hệ phụ thuộc, chọn agent và kiểm tra process trước khi chạy.

### Người vận hành

Người khởi chạy process, theo dõi tiến độ, xem lỗi, hủy lần chạy và sử dụng lịch sử để xử lý sự cố.

Trong MVP, hai trách nhiệm trên có thể do cùng một người đảm nhiệm. Vai trò phân quyền chính thức chưa thuộc phạm vi đã chốt.

## Giá trị cốt lõi

- **Trực quan:** cấu trúc và trạng thái process có thể hiểu được mà không cần đọc code thực thi.
- **Có thể truy vết:** mỗi lần chạy gắn với đúng version, input, kết quả và lịch sử trạng thái của nó.
- **Có kiểm soát:** agent và tool được khai báo rõ; hành động có side effect không được thực thi ngoài quyền được cấp.
- **Tách định nghĩa khỏi thực thi:** chỉnh sửa process không làm thay đổi lịch sử hoặc hành vi của run đã bắt đầu.
- **Phát triển từng bước:** MVP giải quyết một luồng hoàn chỉnh trước khi bổ sung tự động hóa và vận hành phân tán.

## Kết quả mong muốn của MVP

MVP cần giúp một người dùng hoàn thành một luồng xuyên suốt:

1. Tạo project để tập hợp công việc liên quan.
2. Tạo process gồm các task và quan hệ phụ thuộc hợp lệ.
3. Giao mỗi task cho một agent đã được cấu hình.
4. Cài và ghép nối Runner Client trên máy tính sẽ thực thi công việc.
5. Cố định một version của process và khởi chạy thủ công với input.
6. Theo dõi trạng thái của process run, từng task run và Runner thực thi.
7. Xem output hoặc lỗi sau khi chạy và hủy một run đang hoạt động.

Yêu cầu chi tiết và tiêu chí nghiệm thu nằm trong [Yêu cầu MVP](requirements.md).

## Phạm vi MVP

### Trong phạm vi

- Quản lý Project gồm PM, Team, Process và Targets theo tuần/tháng; theo dõi tiến độ theo kết quả được duyệt.
- Thiết kế process dạng đồ thị task có hướng, không chu trình.
- Quản lý version để một run luôn tham chiếu một định nghĩa bất biến.
- Khai báo agent và gán agent cho task.
- Quản lý Skills và Tools nội bộ; Agent được gán cho Task luôn chịu trách nhiệm output, kể cả khi dùng Skill hoặc Robot.
- Cấu hình Providers & API, Models, Roles và các mặc định chung trong Settings; Agent chọn model và Role từ danh mục.
- Overview tập trung vào lỗi cần xử lý, tiến độ Projects và token Agents. Theo dõi token, không quản lý chi phí tiền hoặc ngân sách.
- Quản lý Robot độc lập theo version; thêm node Robot vào Process rồi chọn Agent chịu trách nhiệm và PC thực thi. Tool nội bộ của Skill tách riêng khỏi Robot.
- Khởi chạy thủ công và truyền input cho process.
- Đặt lịch chạy theo thời gian cho một ProcessVersion đã publish và xem phiên dự kiến kế tiếp.
- Đăng ký, theo dõi trạng thái và thu hồi Runner Client cài trên máy người dùng.
- Thực thi task theo quan hệ phụ thuộc; các task đủ điều kiện có thể chạy song song.
- Theo dõi trạng thái, thời điểm, output và lỗi của run.
- Hủy run đang hoạt động theo cơ chế best effort.
- Giới hạn tool của agent tại phía thực thi đáng tin cậy và lưu dấu vết thực thi tối thiểu.

### Ngoài phạm vi MVP

- Lịch phức tạp theo calendar, trigger từ sự kiện hoặc webhook.
- Nhánh điều kiện/vòng lặp tổng quát và process lồng nhau.
- Retry tự động tổng quát cho task có side effect.
- Chỉnh sửa lịch sử hoặc resume tùy ý một run đã kết thúc.
- Phân quyền tài khoản người dùng chi tiết và quy trình phê duyệt thay đổi. Team trong Project là danh sách Agent tham gia, vẫn thuộc định hướng giao diện hiện tại.
- Điều phối nhiều cụm runner, tự động mở rộng và tối ưu lịch chạy.
- Marketplace cho agent, process hoặc tool.
- Báo cáo hiệu suất và SLA nâng cao.

Các mục ngoài phạm vi chỉ là hướng có thể xem xét, không phải cam kết lộ trình.

Chờ người dùng duyệt và làm lại phần lỗi là nhu cầu mới đã ghi nhận từ use case thật. Chúng nằm ở mốc sau thử tích hợp đầu tiên; trạng thái, quyền và cách giữ lịch sử cần thiết kế riêng. Không còn loại bước duyệt của người dùng khỏi toàn bộ sản phẩm như định hướng ban đầu. Thứ tự nằm trong [kế hoạch triển khai](../development/implementation-plan.md).

## Nguyên tắc đánh giá MVP

MVP được xem là có giá trị khi có thể chứng minh bằng một kịch bản mẫu rằng:

- Người dùng tạo và hiểu được một process nhiều task mà không sửa code.
- Process không hợp lệ bị từ chối trước khi chạy với lỗi có ngữ cảnh.
- Run giữ nguyên version đã chọn dù process tiếp tục được chỉnh sửa.
- Người vận hành xác định được task đang chạy, task lỗi và nguyên nhân lỗi.
- Lịch sử phân biệt rõ định nghĩa (`Process`, `Task`) với lần thực thi (`ProcessRun`, `TaskRun`).

Các chỉ số định lượng sẽ được bổ sung sau khi có prototype và kịch bản thử nghiệm với người dùng.

## Ràng buộc và giả định cần kiểm chứng

- Giao diện phục vụ một công ty, không có màn Workspace hoặc bộ chuyển công ty. Workspace trong mô hình kỹ thuật chỉ là ranh giới logic nội bộ, chưa chốt mô hình nhiều đơn vị.
- Người dùng khai báo provider/model trong Settings. Adapter thực thi, giao thức backend và cách lưu secret chưa được quyết định.
- Stack, database, queue và ranh giới deployment chỉ được chốt bằng ADR.
- [HTML prototype](../../demo/agent-cf-prototype/README.md) dùng để kiểm chứng luồng và thuật ngữ, không phải cam kết kiến trúc frontend.

## Câu hỏi mở

- Đối tượng dùng MVP đầu tiên là cá nhân kỹ thuật hay nhóm vận hành có nhiều vai trò?
- Agent là cấu hình nội bộ của Agent CF hay tham chiếu tới agent nằm ngoài hệ thống?
- Mức input/output nào cần được lưu, che dữ liệu hoặc đặt thời hạn lưu giữ?
- Cơ chế PM tự động review/báo cáo, bằng chứng nghiệm thu Target và công thức xếp hạng Agent/Project sẽ được thiết kế thế nào? Prototype hiện nhập số kết quả được duyệt bằng form.
- Thứ tự triển khai engine, Runner Client thật và adapter mẫu sẽ được chốt khi lập kế hoạch kỹ thuật; prototype hiện chỉ mô phỏng.

## Tài liệu liên quan

- [Thuật ngữ](glossary.md)
- [Yêu cầu MVP](requirements.md)
- [Mô hình domain](../architecture/domain-model.md)
- [Mô hình thực thi](../architecture/execution-model.md)
