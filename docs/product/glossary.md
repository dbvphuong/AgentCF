# Thuật ngữ Agent CF

> Status: Draft  
> Last updated: 2026-11-16  
> Owner: Product

## Cách sử dụng

Đây là nguồn chuẩn cho thuật ngữ nghiệp vụ của Agent CF. Tên tiếng Anh bên dưới được dùng trong code, API và database khi các thành phần đó được tạo. Tài liệu đang ở trạng thái Draft; mọi thay đổi thuật ngữ cần được đồng bộ với yêu cầu và mô hình domain.

## Thuật ngữ cốt lõi

### Workspace

Ranh giới logic nội bộ chứa dữ liệu và cấu hình dùng chung. Giao diện hiện phục vụ một công ty, không có màn Workspace hoặc bộ chuyển công ty. Thuật ngữ này không mặc nhiên yêu cầu một module UI hoặc kiến trúc nhiều tenant.

### Project

Phạm vi tổ chức cho một mục tiêu hoặc nhóm công việc liên quan. Project chứa các process và lịch sử các lần chạy thuộc process đó. Project không trực tiếp được thực thi.

### PM và Team

PM là Agent được chỉ định quản lý tổng thể một Project. Team là danh sách Agent tham gia Project, không phải nhóm tài khoản người dùng. PM không thay thế Agent chịu trách nhiệm từng Task và không được suy ra từ tên Role. Một Agent có thể tham gia nhiều Project.

### Target

Mục tiêu tuần hoặc tháng của Project, có khoảng thời gian, số lượng mục tiêu, số kết quả được duyệt và tiêu chí nghiệm thu. Run thành công chưa đồng nghĩa kết quả được duyệt. Prototype cho nhập số kết quả qua form; cơ chế PM tự duyệt chưa được triển khai.

### Process

Định danh lâu dài của một quy trình. Process có cấu hình hiện tại có thể Lưu/Chạy và các snapshot lịch sử; không chứa trạng thái của một lần chạy.

Không dùng `workflow`, `pipeline` hoặc `job` như từ đồng nghĩa với `Process` trong tài liệu kỹ thuật.

### ProcessVersion

Bản chụp cụ thể của Process, chứa định nghĩa task, quan hệ phụ thuộc và cấu hình cần thiết để chạy. Là snapshot nội bộ tự tạo khi chạy. API draft/publish cũ giữ tương thích; Web không yêu cầu quản lý chúng. Một `ProcessRun` luôn tham chiếu đúng snapshot bất biến của lần chạy.

### Task

Định nghĩa một đơn vị công việc trong `ProcessVersion`. Task mô tả mục đích, input cần nhận, agent chịu trách nhiệm, tool được phép dùng và quan hệ phụ thuộc. Task không chứa trạng thái thực thi.

### Dependency

Quan hệ có hướng giữa hai task, thể hiện task đích chỉ đủ điều kiện chạy sau khi task nguồn hoàn thành thành công. Tập dependency của một ProcessVersion phải tạo thành đồ thị không chu trình.

Trong giao diện trực quan, dependency có thể được biểu diễn bằng một cạnh (`edge`).

### Agent

Tên kỹ thuật của **Agent điều phối** trên giao diện: Agent dùng model API thay người giao việc cho Codex/Antigravity, kiểm tra đã hoàn thành chưa, có lỗi không và kết quả đúng yêu cầu không; khi cần yêu cầu làm tiếp/sửa hoặc chờ người dùng. Agent có Role, model API, hướng dẫn, Skills và tập Tool được phép dùng. Model API chọn từ Settings → Providers & Models API. Catalog không tự chứng minh vòng gọi API điều phối đã được triển khai.

Agent là định nghĩa; nó không đồng nghĩa với tiến trình hệ điều hành đang chạy.

### Công cụ AI thực thi

Codex CLI hoặc Antigravity chạy trên PC, nhận nhiệm vụ và trực tiếp đọc Skill, gọi tool, tạo/sửa file. Trên Settings dùng tên **Công cụ AI trên PC**. Tên kỹ thuật vẫn là runtime/adapter. Đây không phải Agent điều phối API và không lấy model mặc định từ Agent.

### Model API và Model thực thi

**Model API** thuộc Provider API và dùng cho Agent điều phối. **Model thực thi** là tên/ID model mà công cụ AI trên PC sử dụng, quản lý riêng theo Codex/Antigravity và bật/tắt tại Settings → Công cụ AI trên PC. Hai danh mục có identity độc lập, kể cả khi tên model giống nhau. Model xuất hiện trong danh mục không bảo đảm tài khoản CLI có quyền dùng. Xem [ADR 0007](../architecture/decisions/0007-orchestration-agents-and-ai-tools.md).

### Role

Nhãn vai trò và mô tả nhiệm vụ chung của Agent, quản lý tại Settings → Roles. Một Role có thể được nhiều Agent dùng chung; mỗi Agent chọn một Role nhưng giữ tên, model, Skill và lịch sử token riêng. Role hiện nhằm dễ hiểu nhiệm vụ và chuẩn bị phân quyền về sau. Các trường Permissions chỉ là cấu hình dự kiến trong prototype, chưa áp dụng kiểm soát quyền. Role không phải quyền tài khoản người dùng và không tự quyết định ai là PM của một Project.

### Tool

Khả năng bên ngoài mà agent có thể yêu cầu khi thực hiện task, ví dụ đọc dữ liệu hoặc gọi một dịch vụ. Việc agent nhìn thấy tool trên giao diện không thay thế kiểm tra quyền tại phía thực thi đáng tin cậy.

Tool là công cụ nội bộ của Skill/Agent, quản lý trong Skills → Tools. Không dùng Tool như từ đồng nghĩa với Robot.

### Robot và RobotVersion

Robot là chương trình độc lập thực hiện một công việc và trả output hoặc lỗi. RobotVersion là một bản phát hành cụ thể, bất biến của Robot. Trang Robots quản lý danh mục, version và thống kê; không gán Agent hoặc PC tại đây.

Khi thêm node Robot vào Process, người dùng chọn RobotVersion, Agent chịu trách nhiệm output, PC thực thi và input. PM chỉ quản lý tổng thể Project. Một RobotVersion có thể được dùng ở nhiều node với Agent/PC khác nhau.

Success rate tính riêng cho mỗi RobotVersion: số lần thành công chia cho tổng số lần thành công và thất bại. Timeout tính là thất bại; hủy hiển thị riêng, không đưa vào mẫu số. Version mới bắt đầu chưa có dữ liệu, không hiển thị 0%; version cũ giữ lịch sử và thống kê.

### Skill

Bộ hướng dẫn cho một loại công việc, có thể kèm mẫu, tài liệu hoặc script và tiêu chuẩn output. Skill được nhiều Agent sử dụng; không phải Agent hay Tool. Task ghi nhận Agent chịu trách nhiệm và Skill/version đã dùng để truy vết kết quả.

### PC (tên trên giao diện)

Mục quản lý máy thực thi và Runner Client. Tên `PC` dùng trên UI; khái niệm domain và tên kỹ thuật vẫn là Runner, Runner Client và Machine.

### Runner

Danh tính thực thi đã đăng ký với Workspace. Runner nhận một task đủ điều kiện, chạy agent tương ứng và trả về kết quả hoặc lỗi. Runner không sở hữu business rule của Process và không phụ thuộc vào chi tiết giao diện.

### Runner Client

Phần mềm được cài trên máy tính người dùng để hiện thực một Runner. Runner Client chủ động thiết lập kết nối outbound tới control plane, gửi heartbeat, nhận TaskRun và thực thi trong phạm vi quyền được cấp.

**CF Client** là tên gọi sản phẩm của thành phần này. Client có thể gọi runtime Codex/Antigravity và tool có sẵn qua adapter. Client không đồng nghĩa với model AI hoặc Windows Service; thiết kế cách chạy Windows nằm trong [ADR CF Client](../architecture/decisions/0002-cf-client-windows.md).

### Agent runtime và Adapter

Agent runtime là chương trình thực thi Agent, ví dụ Codex hoặc Google Antigravity. Agent nghiệp vụ là cấu hình nhân viên/trách nhiệm; runtime là cách thực hiện công việc, Model là cấu hình mô hình trong runtime khi được hỗ trợ. Không dùng ba khái niệm thay thế nhau.

Adapter là lớp tích hợp giữa Agent CF và runtime/tool hiện có: chuyển input/lệnh, sự kiện, output và lỗi. Tool người dùng có sẵn chưa mặc nhiên là Robot hay Tool của Skill; phân loại sau khi kiểm kê cách dùng và cách gọi.

### Can thiệp của người dùng

Điểm công việc cần người dùng duyệt, bổ sung hướng dẫn hoặc quyết định khi Agent không xử lý được. Là nhu cầu sản phẩm đã ghi nhận; không đồng nghĩa run thất bại hoặc được phép tự retry. Trạng thái kỹ thuật và cơ chế tiếp tục chưa chốt.

### Machine

Máy vật lý hoặc máy ảo nơi Runner Client hoạt động. Thông tin hệ điều hành và năng lực của Machine giúp lập lịch nhưng không biến Machine thành một Task hoặc Agent.

### Heartbeat

Tín hiệu định kỳ từ Runner Client cho biết kết nối và khả năng nhận việc. Thiếu heartbeat quá ngưỡng làm Runner chuyển sang trạng thái offline; không tự động chứng minh task đang chạy đã thất bại hoặc an toàn để chạy lại.

### ProcessRun

Một lần thực thi cụ thể của một `ProcessVersion`, được tạo với input và lịch sử trạng thái riêng. Sửa Process sau khi ProcessRun bắt đầu không làm thay đổi lần chạy đó.

Trong ngữ cảnh đã rõ, có thể gọi ngắn là `run`; khi có nguy cơ nhầm lẫn phải dùng `ProcessRun`.

### TaskRun

Bản ghi thực thi của một Task trong phạm vi một ProcessRun. TaskRun lưu trạng thái, thời điểm, input được giải quyết, output hoặc lỗi của task tương ứng.

### Attempt

Một lần thử thực thi cụ thể của TaskRun. Khái niệm này cho phép mô hình hóa retry mà không ghi đè lịch sử lần thử trước. MVP chưa yêu cầu retry tự động nhưng không được thiết kế theo cách ngăn cản việc bổ sung Attempt sau này.

## Thuật ngữ dữ liệu và vận hành

### Input

Dữ liệu được cung cấp khi bắt đầu ProcessRun hoặc được truyền vào TaskRun từ input của run và output của task phụ thuộc. Hợp đồng dùng JSON Schema 2020-12, mapping khai báo bằng binding/JSON Pointer theo domain model và OpenAPI.

### Output

Kết quả có cấu trúc do TaskRun hoặc ProcessRun tạo ra. Log không được coi là output nghiệp vụ.

### Log

Thông tin chẩn đoán phát sinh trong quá trình thực thi. Log không được chứa secret hoặc toàn bộ payload nhạy cảm và không thay thế output có cấu trúc hay audit event.

**Runs** là màn theo dõi các ProcessRun; **Logs** là bảng log bên trong chi tiết một Run, không dùng hai tên này thay nhau.

### Tokens

Chỉ số sử dụng của Agent, giao diện hiện theo dõi một tổng token tháng cho mỗi Agent và tổng các Agent trên Overview. Không có Cost/Budget hoặc quy đổi tiền. Cách lấy usage, chốt kỳ và chống đếm trùng cần được thiết kế khi tích hợp model; không suy ra token từng Project từ tổng toàn cục của Agent.

### Trạng thái xử lý cảnh báo

Đánh dấu một lỗi đã được người vận hành xử lý để không tiếp tục nổi bật ở Overview. Thông tin này độc lập với Status của Run: một Run Failed vẫn giữ Failed và toàn bộ lịch sử, có thể mở lại cảnh báo.

### Error

Kết quả thất bại có mã hoặc loại lỗi, thông điệp có ngữ cảnh và chi tiết an toàn để chẩn đoán. Lỗi không được bị nuốt im lặng.

### Status

Trạng thái vòng đời của một thực thể. Vòng đời kỹ thuật sơ bộ nằm trong [Mô hình thực thi](../architecture/execution-model.md). Filter UI có thể nhóm nhiều trạng thái nhưng không sửa giá trị của Run; quy tắc nhóm nằm trong [yêu cầu theo màn hình](requirements.md#yêu-cầu-theo-màn-hình). Trạng thái kỹ thuật chưa có trong prototype không được coi là đã triển khai.

### Publish

Chuyển một ProcessVersion draft hợp lệ thành version bất biến có thể được dùng để tạo ProcessRun. Publish không tự động đồng nghĩa với chạy, dù giao diện có thể cung cấp thao tác kết hợp “publish and run”.

### Schedule

Cấu hình thời gian tạo ProcessRun tự động cho một ProcessVersion đã publish. Schedule xác định thời điểm kế tiếp và cách chọn Runner: một Runner cụ thể hoặc tự động chọn Runner phù hợp. Thay đổi ProcessVersion không âm thầm thay đổi version mà Schedule đang tham chiếu.

### Cancel

Yêu cầu dừng một ProcessRun đang hoạt động. Hủy là best effort: hệ thống phải ngăn công việc mới bắt đầu và yêu cầu dừng công việc đang chạy, nhưng side effect đã hoàn tất không được tự động hoàn tác.

### Retry

Thực hiện lại TaskRun bằng một Attempt mới theo chính sách xác định. Retry không được ghi đè Attempt trước và cần xét idempotency đối với hành động có side effect. Retry tự động nằm ngoài MVP.

### Timeout

Giới hạn thời gian thực thi. Khi vượt giới hạn, hệ thống yêu cầu dừng và thu hồi quyền; chỉ kết thúc Attempt failed/timeout sau khi có bằng chứng dừng. Chưa rõ kết quả giữ reconciling; timeout không hoàn tác side effect.

### Idempotency

Tính chất cho phép lặp lại một thao tác với cùng định danh mà không tạo thêm side effect ngoài ý muốn. Đây là điều kiện cần cân nhắc trước khi cho phép retry tự động.

### Permission

Quyền cho phép một chủ thể thực hiện hành động hoặc truy cập tài nguyên. Permission phải được kiểm tra tại ranh giới thực thi đáng tin cậy, không chỉ bằng cách ẩn hoặc hiện thành phần UI.

### AuditEvent

Bản ghi bất biến về một hành động quan trọng: ai hoặc thành phần nào đã làm gì, với tài nguyên nào, vào thời điểm nào và kết quả ra sao. AuditEvent không được chứa secret và không đồng nghĩa với log chẩn đoán.

## Quan hệ tóm tắt

```text
Workspace
├── Project
│   ├── PM và Team ──> Agent
│   ├── Target
│   └── Process
│       ├── ProcessVersion
│       │   ├── Task
│       │   └── Dependency
│       ├── Schedule ──> ProcessVersion
│       └── ProcessRun ──> ProcessVersion
│           └── TaskRun ──> Task
│               └── Attempt
├── Agent
│   ├── Role và Model
│   ├── Skill/version ──> Tool
│   └── allowed Tool
├── Robot ──> RobotVersion (Task tham chiếu)
└── Runner ── Runner Client ── Machine
```

Quan hệ và bất biến chi tiết nằm trong [Mô hình domain](../architecture/domain-model.md).

## Từ cần tránh hoặc dùng có điều kiện

| Từ | Quy ước |
|---|---|
| Workflow | Không dùng thay cho Process; chỉ dùng khi trích dẫn khái niệm của hệ thống bên ngoài. |
| Pipeline | Không dùng thay cho Process; chỉ dùng cho thuật ngữ riêng đã được định nghĩa, ví dụ CI pipeline. |
| Job | Không dùng thay cho ProcessRun hoặc TaskRun; chỉ dùng nếu một hạ tầng bên ngoài có khái niệm job riêng. |
| Flow | Chỉ dùng để nói về cách trình bày trực quan của Process, không phải một entity domain độc lập. |
| Server | Dùng cho máy hoặc dịch vụ hạ tầng cụ thể; không dùng thay cho Runner. |
