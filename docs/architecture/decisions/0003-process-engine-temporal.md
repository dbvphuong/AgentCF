# 0003 - Temporal cho điều phối Process và can thiệp của người dùng

- Status: Accepted
- Date: 2026-11-13
- Last updated: 2026-11-16

## Context

Process gồm các bước Agent/tool có thể chạy lâu trên PC. Người dùng đã có tool và dùng Codex/Antigravity làm runtime Agent. Engine cần điều phối bước, giữ lịch sử, xử lý gián đoạn và chờ người dùng can thiệp.

Yêu cầu cụ thể: Process hoàn thành 3/5 node rồi gặp vấn đề; người dùng xử lý và bấm Continue để làm tiếp tại bước vướng, giữ kết quả đã đạt. Có thể có nhiều Process cùng chờ xử lý. Không đồng nhất tạm dừng chờ người dùng với Failed/Cancelled đã kết thúc.

## Decision

Chấp thuận **Temporal với Python SDK** cho thiết kế Process động. BASE-001 hoàn thiện hướng đã có trong phạm vi người dùng giao ngày 2026-11-16; chưa có tích hợp hoặc kiểm chứng engine.

- Temporal điều phối vòng đời ProcessRun: dependency, chờ kết quả ngoài hệ thống, timer và quyết định của người dùng. Topology local được chốt bên dưới; Human/Continue vẫn là mốc mở rộng riêng.
- FastAPI phục vụ web và các ranh giới giao tiếp. Bộ điều phối dùng worker riêng; CF Client thực thi Codex/Antigravity/tool trên PC.
- Công việc có I/O/side effect thực hiện qua Activity và lớp tích hợp phù hợp; Workflow không trực tiếp gọi tool, model, database nghiệp vụ hoặc Windows.
- Graph trên UI phải được kiểm tra và cố định ProcessVersion trước khi ánh xạ sang thực thi. Temporal không tự biến sơ đồ React Flow thành chương trình chạy.
- Client nhận việc qua Server theo [contract](../client-protocol.md); không là Temporal Worker và không kết nối PC tới Temporal.
- Chưa thêm Celery/Redis cho cùng nhiệm vụ điều phối; LangGraph chưa cần trong phương án đầu. Có thể đánh giá riêng nếu sau này cần xây vòng suy luận Agent thay cho hoặc bổ sung runtime hiện có.

## Human và Continue

1. Giữ kết quả của các node đã đạt; lưu node đang vướng, lý do, phần đã chạy và yêu cầu người dùng xử lý.
2. Node phụ thuộc không được chạy tiếp khi chưa giải quyết vấn đề. Với các nhánh đang chạy song song, phạm vi tạm dừng phải được thiết kế rõ, chưa mặc định cưỡng chế dừng mọi tiến trình.
3. Người dùng xem thông tin, khắc phục hoặc bổ sung hướng dẫn và chọn Continue trên web. Phần Human tập hợp yêu cầu can thiệp là hướng UI tiếp theo, chưa có trong prototype hiện tại.
4. Server kiểm tra quyền và tính hợp lệ, lưu quyết định rồi gửi thông điệp cho Workflow đang chờ, dự kiến dùng Signal/Update. Hợp đồng cụ thể chưa chốt.
5. Tiếp tục chờ tool đang chạy hoặc tạo lần thử mới cho node lỗi phải là hai trường hợp phân biệt; không tự chạy lại chỉ vì nhận Continue.
6. Continue trùng phải được khử trùng. Run đã kết thúc không được đổi ngược trạng thái bằng nút Continue; chạy lại phải có lịch sử riêng theo thiết kế được duyệt.

Tên trạng thái kỹ thuật khi chờ, timeout chờ người dùng và chính sách thay đổi input vẫn cần cập nhật đồng bộ domain/execution/API trước khi triển khai. Nhãn Needs attention mới là định hướng trình bày, không phải enum đã chốt.

## Consequences

- Có nền tảng quản lý quy trình dài và chờ quyết định bên ngoài thay vì tự viết toàn bộ cơ chế điều phối.
- Có thêm Temporal Service, worker và công việc vận hành, backup, giám sát; local dùng development server có file bền vững riêng; production self-host/managed cần quyết định triển khai sau.
- Workflow phải tuân thủ tính xác định khi replay và quy tắc nâng cấp code; version engine khác với ProcessVersion của sản phẩm.
- Phải cấu hình retry rõ ràng cho từng loại Activity. Bước tạo voice/media/đăng video không được tự retry mù; cần định danh chống trùng, kiểm tra kết quả cũ và đối soát.
- Temporal không khôi phục được tiến trình trên PC một cách tự động, không bảo đảm side effect bên ngoài chỉ xảy ra một lần, không hoàn tác tác vụ khi Cancel. CF Client/adapter vẫn phải giải quyết các vấn đề này.
- Chỉ lưu metadata/tham chiếu artifact trong lịch sử điều phối; không đưa video/audio lớn hoặc secret vào Workflow history.

## Alternatives considered

| Phương án | Ưu điểm | Lý do chưa chọn cho engine chính |
|---|---|---|
| Celery + Redis | Hàng đợi công việc, chuỗi/nhóm task và chạy song song | Phải xây thêm quản lý chờ người dùng, tiếp tục, đối soát và lịch sử toàn Process |
| LangGraph | Luồng Agent có trạng thái, checkpoint và human-in-the-loop | Khả thi, nhưng nhu cầu trước mắt nghiêng về vận hành tool ngoài hệ thống; vẫn cần hạ tầng giao việc và quản lý PC |
| Engine tự viết | Toàn quyền, ít thành phần ban đầu | Chi phí duy trì state machine, gián đoạn, chống trùng và recovery dễ tăng mạnh |

Các phương án đều có thể đáp ứng nếu xây thêm; đây là đánh đổi về trách nhiệm và công sức, không khẳng định Temporal giải quyết mọi phần của sản phẩm.

## Điều kiện hoàn thiện quyết định trước scaffold

BASE-001 đã chốt thiết kế local dưới đây, chưa chạy lệnh dựng hạ tầng:

- Cùng PC có Web, FastAPI Server (chứa outbox relay), Temporal development server, worker Python và CF Client, với vòng đời process riêng. Relay là supervised loop trong Server, không thuộc request; engine/worker chạy riêng nên đóng request hoặc Web không dừng công việc. Temporal chỉ bind loopback; không mở cho Client. HTTP không TLS chỉ dùng loopback khi thử local; qua mạng phải có HTTPS/WSS.
- Temporal development server dùng `server start-dev --db-filename <file-riêng>` với đường dẫn tuyệt đối trong dữ liệu runtime ngoài Git. Không dùng in-memory cho kiểm tra restart. File engine tách hoàn toàn SQLite nghiệp vụ do Server sở hữu. Đây là topology local development, không phải triển khai production.
- Một Workflow cho một ProcessRun, ID `process-run/<run_id>`, task queue `agent-cf-process-v1`. Không reuse Workflow ID sau khi đóng; retry Workflow tự động tắt. Workflow giữ ID/revision và tham chiếu nhỏ, không chứa payload/artifact lớn hoặc secret.
- Worker chạy bộ thông dịch DAG có version. Workflow không truy cập DB; Activity gọi API nội bộ Server bằng credential riêng. Relay chuyển outbox sang start/signal engine. API nội bộ được mô tả trong OpenAPI, Web/Client không có scope gọi.
- Ghi Run/TaskRun/audit/outbox cùng transaction; không có distributed transaction với Temporal. DB fail thì không gửi lệnh; commit mà engine chưa nhận thì outbox còn chờ; engine nhận nhưng relay chưa đánh dấu thì gửi lại cùng ID. Activity commit mà mất phản hồi thì inbox trả lại kết quả. SQLite nghiệp vụ là nguồn chuẩn trạng thái công bố; chi tiết tại [ADR 0005](0005-versioned-process-execution.md) và [execution](../execution-model.md#ranh-giới-db-và-engine).
- Retry Activity chỉ dùng cho lệnh Server có inbox/idempotency; không spawn runtime trực tiếp trong Activity. Runtime/task retry tắt trong baseline. Activity timeout không tạo quyền chạy Attempt mới trên PC.

Tài liệu chính thức xác nhận CLI development server hỗ trợ file SQLite riêng cho phát triển local: [setup CLI](https://github.com/temporalio/documentation/blob/main/docs/cli/setup-cli.mdx), [self-hosted guide](https://docs.temporal.io/self-hosted-guide). Activity cần idempotency khi retry: [Activity definition](https://docs.temporal.io/activity-definition). Đây là căn cứ thiết kế; BASE-003 vẫn phải kiểm chứng phiên bản binary/SDK, Python 3.14, restart và replay thực tế.

## Điều kiện kiểm chứng khi triển khai

Các tiêu chí dưới đây kiểm chứng khả năng thực tế, không phải toàn bộ điều kiện đầu vào của [BASE-001](../../development/tasks/base/001-foundation-design.md#base-001). Theo [plan](../../development/implementation-plan.md): [BASE-003](../../development/tasks/base/002-application-bootstrap.md#base-003) kiểm tra hạ tầng Service/worker và lưu trữ; [RUN-002](../../development/tasks/runs/002-run-execution-history.md#run-002)/[RUN-006](../../development/tasks/runs/003-skill0-web.md#run-006) kiểm tra giao việc và mốc Skill 0; [REL-001](../../development/tasks/execution/002-recovery.md#rel-001) kiểm tra gián đoạn/đối soát; [AGN-002](../../development/tasks/agents/001-agent-review.md#agn-002)/[RUN-007](../../development/tasks/runs/004-skill-chain.md#run-007) kiểm tra review và chuỗi Skill; [REL-003](../../development/tasks/execution/004-human-continue.md#rel-003) kiểm tra Human/Continue. Chưa đạt tiêu chí nào phải ghi rõ giới hạn ở task đó, không suy từ nhãn Accepted.

- Một tool thật chạy lâu, trả log/output và kết quả review hợp lệ.
- Server/worker restart khi chờ không làm mất tiến độ đã lưu.
- PC mất kết nối rồi trở lại được đối soát, không tạo thêm tác vụ ngoài ý muốn.
- Process dừng ở 3/5, người dùng xử lý và Continue tại bước vướng; 3 kết quả trước giữ nguyên.
- Gửi Continue hai lần không gây chạy trùng; hủy và kết quả đến muộn được xử lý nhất quán.
- Chứng minh chính sách retry không tạo trùng side effect hoặc tiêu hao quota ngoài ý muốn.

## References

- [Temporal Workflows](https://docs.temporal.io/workflows)
- [Temporal Activities](https://docs.temporal.io/activities)
- [Python message passing và chờ quyết định](https://docs.temporal.io/develop/python/message-passing)
- [Self-hosted Temporal](https://docs.temporal.io/self-hosted-guide)
- [Celery Canvas](https://docs.celeryq.dev/en/stable/userguide/canvas.html)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
