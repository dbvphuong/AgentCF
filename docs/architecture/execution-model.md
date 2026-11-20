# Mô hình thực thi Agent CF

> Status: Design baseline  
> Last updated: 2026-11-16  
> Owner: Architecture

## Mục đích và trạng thái

Thiết kế cho hệ thống quản lý tổng và Process động, chưa triển khai ứng dụng. [Requirements](../product/requirements.md) giữ hành vi sản phẩm; [domain](domain-model.md) giữ quan hệ/snapshot; [ADR 0003](decisions/0003-process-engine-temporal.md) và [0005](decisions/0005-versioned-process-execution.md) giữ lựa chọn hạ tầng; [OpenAPI](../../openapi/openapi.yaml) giữ schema HTTP và enum máy đọc được. Skill 0–1–2 là dữ liệu test, không phải graph cố định của engine.

Baseline hỗ trợ DAG với node Agent/Robot, join tất cả dependency thành công, fan-out và song song theo capacity. Condition/loop, node Human, review từng Part và retry task tự động chưa thuộc baseline; các mốc sau phải mở rộng contract trước triển khai. Không coi prototype hoặc thử CLI là bằng chứng engine đã chạy.

## Kết nối Runner Client

Ghép nối một lần, credential thu hồi được và session nằm tại [contract Client](client-protocol.md). Runner kết nối outbound; heartbeat chỉ cho biết khả dụng, không chứng minh tiến trình đã dừng. Server đối chiếu năng lực, policy, Workspace và session trước claim; năng lực tự khai báo không tự tạo quyền.

## Điều kiện trước khi chạy

Luồng Skill local theo chủ đề dùng `topic_directory` và `request` trong input Run, tên chủ đề lấy từ tên thư mục. Server kiểm cùng PC/root và path nằm trong root snapshot; Client kiểm thư mục đã tồn tại/resolve trước spawn. Claim luôn giữ ngữ cảnh này cho mọi node, cwd vẫn root Project, bước sau đọc file trước theo Skill. Không dùng input mapping tổng quát để giả lập việc truyền file; xem [ADR 0009](decisions/0009-run-topic-context.md). Generic input/Run cũ giữ tương thích.

1. Project/Process active, cấu hình đã lưu, graph và quyền hợp lệ. Server tự chụp snapshot bất biến trong transaction tạo Run theo [ADR 0011](decisions/0011-save-and-run-current-configuration.md).
2. Người yêu cầu có quyền trên Project; input hợp JSON Schema, không nhận shell/đường dẫn executable.
3. Agent/Skill/Tool/Robot chưa archived; provider/model còn bật. Kiểm tra catalog hiện tại chỉ chặn sử dụng mới, không thay snapshot.
4. Runtime model ID, adapter và Skill bundle đã ghim; không tự fallback runtime/model.
5. Không buộc Runner online để tạo run. Run queued chờ Runner đến queue deadline; hết hạn khi chưa giao việc thì failed với `runner_unavailable`.

Catalog archive không tự hủy run đang chạy; thu hồi quyền bảo mật là hành động riêng có audit. Archive/Xóa Project/Process và Remove Runner bị chặn khi còn bất kỳ run chưa terminal, kể cả queued/reconciling. Xóa có xác nhận chỉ xóa lịch sử/phiên bản thuộc aggregate sau khi mọi Run/thực thi kết thúc, không tự Cancel và không đổi thành Archive; quyền cũ, receipt/inbox/outbox và artifact metadata thuộc aggregate được xóa cùng transaction theo [ADR 0008](decisions/0008-explicit-aggregate-deletion.md).

## Kích hoạt theo lịch

Save không Start, Start không Run ngay, Stop không Cancel, Cancel không Stop lịch. Lịch Manual/Daily/Weekly dùng giờ Việt Nam, lấy cấu hình Process hiện tại khi đến hạn và tự chụp snapshot Run; lưu không tự Run. API ghim snapshot cũ giữ tương thích. Schedule tạo run qua cùng use case/validation như manual; khóa khử trùng là `(schedule_id, scheduled_for)` với thời điểm UTC. Scheduler thuộc PROC-004, chưa triển khai ở task thiết kế này.

PC node là ràng buộc bắt buộc. Manual Run/Schedule chỉ chọn Runner mặc định cho node không ghim PC; không ghi đè PC node. Robot bắt buộc ghim Runner, Agent có thể ghim hoặc chọn theo năng lực. Node A/B ghim hai PC thì run dùng hai PC; artifact chuyển qua Server bằng ID, không truyền đường dẫn local giữa máy. Node ghim PC offline chờ đến queue deadline, không tự chuyển máy.

Skill local theo [ADR 0006](decisions/0006-local-skill-paths-and-pc-outputs.md) bắt buộc ghim PC sở hữu `SKILL.md` và thư mục làm việc tuyệt đối. Runtime giữ quy trình Skill, tự dùng tool tạo/sửa file tại PC; Client kiểm file thay đổi thực tế và ghi metadata, không ghi phản hồi chat thành output thay runtime. Các node cùng PC tiếp tục dùng file gốc. Bản sao upload tùy chọn; thiếu preview trên Web không làm thất bại output hợp lệ trên PC. Chưa có đường truyền file giữa hai PC thì không giả định chúng chia sẻ filesystem.

## Tạo run

Một transaction tạo ProcessRun, input chuẩn hóa, snapshot digest, một TaskRun pending cho mỗi Task, audit và outbox `start_run`; run queued với revision 1. Khóa idempotency theo principal/operation/resource; cùng khóa và canonical request trả tài nguyên cũ, khác payload trả `409 idempotency_conflict`. Giữ khóa ít nhất suốt vòng đời tài nguyên và thời hạn lưu lịch sử. Không giữ transaction khi gọi engine/runtime.

## Trạng thái ProcessRun

| Trạng thái | Ý nghĩa và chuyển đổi |
|---|---|
| `queued` | Chưa claim Attempt; sang running, failed hoặc cancelling |
| `running` | Đã claim ít nhất một Attempt; sang succeeded, failed, cancelling hoặc reconciling |
| `reconciling` | Attempt chưa rõ tiến trình/kết quả; chặn dispatch mới toàn run; về running qua đối soát, sang cancelling khi hủy hoặc terminal sau đối soát và settle |
| `cancelling` | Không dispatch mới, chờ mọi Attempt xác định đã dừng |
| `succeeded` | Mọi TaskRun succeeded, output run hợp lệ |
| `failed` | Có lỗi, mọi TaskRun terminal, không còn Attempt chưa rõ kết quả |
| `cancelled` | Hủy đã xử lý, mọi TaskRun terminal, không còn Attempt chưa rõ kết quả |

Ba trạng thái cuối terminal, không chuyển ngược. Queued → failed cho lỗi khởi động/queue timeout. Filter Running của UI gồm queued/running/reconciling/cancelling; dòng hiển thị trạng thái cụ thể, không thêm menu. Human chờ duyệt khác với reconciling kỹ thuật.

## Trạng thái TaskRun

| Trạng thái | Ý nghĩa |
|---|---|
| `pending` | Chờ dependency hoặc chưa được đánh giá |
| `queued` | Đủ điều kiện, input đã giải quyết, chờ Runner |
| `running` | Đã claim độc quyền; chưa khẳng định đã spawn |
| `reconciling` | Mất quyền hoặc cần chứng minh tiến trình/kết quả; không cấp Attempt mới |
| `succeeded` | Tiến trình dừng thành công, output/artifact hợp lệ |
| `failed` | Lỗi xác định và tiến trình đã dừng, gồm timeout đã đối soát |
| `skipped` | Chưa claim, bị chặn bởi dependency lỗi/hủy |
| `cancelled` | Đã claim và đã xác định dừng sau yêu cầu hủy |

Terminal là succeeded/failed/skipped/cancelled. Chuyển đổi: pending → queued/skipped/failed; queued → running/skipped/failed; running → reconciling hoặc terminal; reconciling chỉ sang terminal sau chứng minh dừng trong baseline; không hồi sinh quyền đã hết hạn. Pending → failed cho mapping input lỗi; queued → failed cho queue timeout/config/permission. Không sửa kết quả terminal.

## Attempt và kết quả chưa rõ

Attempt có claimed/running/reconciling/succeeded/failed/cancelled; ba giá trị cuối terminal. Claim tạo Attempt và quyền cùng transaction; started event hợp lệ mới chuyển claimed → running và đặt Started. Bằng chứng journal có thể bổ sung Started qua đối soát. Baseline tối đa một Attempt/TaskRun; mô hình 0..n dành cho retry có kiểm soát sau này.

`stop_reason` lưu riêng cancel_requested/timeout/credential_revoked/lease_expired. Lease hết hạn hoặc mất heartbeat không kết thúc Attempt. PID đơn lẻ không đủ chứng minh dừng: cần session, launch ID, thời điểm tạo process/cây tiến trình, journal và kết quả thu được. Mất journal sau restart giữ reconciling, không phỏng đoán failed rồi retry. REL-001 triển khai recovery đầy đủ; baseline giữ bằng chứng và chặn giao lại.

## Luật lập lịch

- Task gốc queued khi run được điều phối. Task phụ thuộc chỉ queued khi mọi nguồn succeeded; mapping được giải quyết/validate và lưu input/digest trước claim.
- Nguồn failed/skipped/cancelled làm downstream skipped. Nhánh độc lập đã chạy có thể hoàn tất, không tự hủy theo kiểu fail-fast. Lỗi chưa rõ làm run reconciling, chặn claim mới nhưng không mặc định giết nhánh đang chạy.
- Nhiều TaskRun có thể queued; claim kiểm tra capacity Runner nguyên tử, không bảo đảm thứ tự node độc lập. Local mặc định capacity 1, nâng theo cấu hình/kiểm chứng adapter.
- Mapping input lỗi tạo `input_mapping_invalid` trước dispatch. Output run tập hợp toàn bộ output Task cuối theo Task ID (REQ-RUN-05), không custom output mapping; chỉ tính khi toàn graph succeeded. Schema output run lỗi thì run failed dù mọi TaskRun succeeded.

## Hoàn tất run

Run chỉ terminal khi mọi TaskRun terminal và không còn tiến trình chưa xác định. Cancel được chấp nhận trước transaction hoàn tất run thì kết quả tổng cancelled; task đã hoàn tất giữ kết quả thực tế. Nếu run terminal trước thì Cancel trả `409 run_terminal`.

Thành công cần đủ: adapter xác nhận tiến trình đã dừng, exit thành công và output hợp cấu hình/schema. Với output local, Client kiểm file thực tế trên PC cùng hash/đường dẫn; không yêu cầu upload. Nếu cấu hình yêu cầu bản sao artifact trên Server thì bản sao đó phải upload/finalize và đúng digest. Không suy từ exit 0, lời model nói đã xong hoặc chỉ có file cũ cùng tên. Agent review/Target approval riêng với succeeded baseline.

## Quyền nhận việc và chống chạy trùng

Claim là CAS trên TaskRun queued + run cho phép dispatch + Runner/session hiệu lực + capacity + policy. Tạo Attempt, generation tăng, lease/token hash, audit và TaskRun running cùng transaction. Quyền ràng buộc Workspace/Runner/session/run/task/attempt/generation; token không đi qua log, WebSocket hoặc Temporal history. Server từ chối ở `now >= expires_at` theo giờ Server.

Mặc định thiết kế: heartbeat 15s, offline sau 45s, lease 60s, renew mỗi 15s; execution timeout 1800s, queue timeout 86400s. Đây là policy local cấu hình được, chưa đo tải; timeout nguyên dương cố định trong snapshot/run. Renew không kéo dài execution deadline, renew muộn không hồi sinh lease. Client dùng khoảng thời gian còn lại với monotonic clock/safety margin, không dùng đồng hồ PC để tăng quyền.

Claim mất phản hồi vẫn có thể đã được nhận, không reclaim cho bên khác. Retry cùng request ID trả cùng Attempt/token khi còn hạn (response cache được mã hóa; token chính chỉ lưu hash); hết hạn trả lỗi và giữ reconciling. Client ghi journal trước spawn, một launch/Attempt; crash giữa journal/spawn là chưa rõ kết quả, không tự spawn lại.

| Tình huống | Xử lý mong muốn |
|---|---|
| Hai Runner claim cùng TaskRun | Một thắng; bên còn lại 409, không Attempt thứ hai |
| Claim/started/event trùng ID và payload | Receipt cũ; không lặp spawn/chuyển trạng thái |
| Cùng ID khác payload | 409 idempotency_conflict |
| Renew đúng session/generation, còn hạn | Gia hạn đến giới hạn deadline, trả expiry Server |
| Lease hết hạn hoặc credential/session thu hồi | Chặn claim/renew/complete, dừng best effort, Attempt reconciling |
| Timeout/hủy đang chạy | Lưu stop_reason; chưa chứng minh dừng thì reconciling/cancelling |
| Result trước Cancel | Task giữ kết quả thật; tổng run theo transaction hoàn tất |
| Result sau expiry/thu hồi/terminal | 409 stale_execution; chỉ observations được lưu bằng chứng |
| Result lặp sau receipt thành công | Cùng request trả receipt cũ sau kiểm tra principal/identity dù lease đã đóng; khác payload bị từ chối |
| PC reconnect | Session mới không kế thừa lease; báo observations, không nhận lại Attempt |
| Spawn xong chưa báo started | Đối soát journal; không coi claimed là chưa chạy |

## Timeout

Queue deadline tính từ khi run/TaskRun queued. Execution deadline từ claim, không lùi khi renew/reconnect. Hết hạn ghi yêu cầu dừng/thu hồi quyền. Chưa claim thì failed; đã claim mà chưa biết dừng thì reconciling. Chỉ ghi failed/timeout terminal sau bằng chứng dừng rồi downstream skipped. Timeout không hoàn tác side effect.

## Hủy

Ghi cancel request/audit/outbox và run cancelling cùng transaction. Chặn claim mới; pending/queued thành skipped; yêu cầu dừng Attempt đã claim. Task hoàn thành tự nhiên trước thu hồi giữ kết quả thật. Chưa rõ tiến trình còn chạy thì giữ cancelling cùng attention_reason, không đóng run giả.

## Thất bại

Error có code, message an toàn, correlation ID và field path khi validation; phân biệt validation/configuration, permission, execution, artifact/output invalid, timeout và infrastructure. Không ghi secret hoặc toàn payload nhạy cảm vào log. HTTP error schema tại OpenAPI; lỗi nghiệp vụ sau claim nằm trong Attempt/event.

## Retry

Không retry task tự động trong baseline; sửa nguyên nhân rồi tạo run/key mới. Relay/HTTP/Activity retry cùng ID để hoàn tất cùng thao tác, không tạo Attempt mới. REL-003/AGN-002 phải thiết kế retry giới hạn, review/checkpoint riêng; không dùng Activity retry để gọi lại tool có side effect.

## Ranh giới DB và engine

Server là writer duy nhất của SQLite nghiệp vụ. Relay là supervised loop trong process Server, thuộc infrastructure, đọc/ack outbox qua persistence của Server; không gắn vòng đời HTTP request. Worker chạy process riêng, gọi API nội bộ scope engine, không mở file DB. Workflow tính quyết định xác định từ descriptor graph và sự kiện; input/output lớn ở Server. SQLite giữ trạng thái công bố, Temporal giữ lịch sử điều phối/replay; UI chỉ đọc Server.

| Ranh giới lỗi | Kết quả thiết kế |
|---|---|
| Transaction tạo run fail | Không để run/task/outbox dở dang |
| DB commit, engine chưa nhận | Outbox pending, relay retry cùng ID |
| Engine nhận, relay crash trước ack | Workflow ID/command ID khử trùng |
| Activity commit, mất phản hồi | Inbox trả receipt cũ, không lặp audit/dispatch |
| Worker crash/replay | Interpreter/command ID giữ nguyên, không gọi PC trực tiếp |
| Client event đã lưu, signal chậm | UI đọc DB; outbox retry theo sequence |
| Engine revision cũ | 409 revision_conflict; đọc snapshot/event mới rồi tính lại |

API nội bộ nhận command ID, expected revision và action đóng queue_tasks/expire/settle/reconcile. Server kiểm tra lại invariant. Settle tự tính trạng thái/output, không nhận enum terminal tùy ý. Reconcile cần observation ID và bằng chứng đã validate/audit, không cho Web/Client tự gọi. Apply, inbox receipt, revision, audit/outbox cùng transaction. Relay gửi thứ tự per run; Workflow bỏ duplicate ID, buffer sequence chưa liên tục; digest không khớp thì dừng chẩn đoán.

## Gián đoạn và khôi phục

BASE-003 kiểm chứng persistence/restart engine; RUN-002/CLI-001 triển khai bảo vệ tối thiểu hai phía; REL-001 đối soát đầy đủ. Baseline đã quy định giữ tình trạng chưa rõ/bằng chứng và chặn giao lại, chưa nghiệm thu recovery tự động. Outbox không tự khôi phục chương trình PC; fencing không bảo đảm exactly-once side effect của tool ngoài Agent CF.

## Can thiệp, xử lý ngoại lệ và phạm vi resume

Agent chẩn đoán trong quyền, không tự sửa chương trình/tăng quyền/retry side effect. Human/Continue tương lai cần ID quyết định, quyền, khử trùng, giữ TaskRun/artifact đã đạt và phân biệt tiến trình cũ với Attempt mới. Chưa có endpoint Continue/node Human trong baseline. REL-003 hoàn thiện trạng thái chờ trước triển khai; reconciling không phải duyệt nội dung, terminal không chuyển ngược.

## Audit và quan sát

Event bất biến có ID, sequence per run, type, run/task/attempt identity, occurred_at (PC) và recorded_at (Server). Không dùng giờ PC quyết định lease. UI poll/query cursor; WebSocket chỉ invalidate, mất thông báo vẫn đọc lại. Logs riêng với audit/output, không làm kết quả nghiệp vụ.

Started khi có bằng chứng bắt đầu; Ended khi terminal; Duration từ Started tới Ended/hiện tại, thiếu thì `—`. Timestamp API RFC3339 UTC, UI giờ Việt Nam. Đánh dấu cảnh báo đã xử lý không sửa trạng thái Run/log. Artifact lưu theo Attempt, không ghi đè bản cũ.

## Kịch bản cần kiểm thử khi triển khai

Một node thành công/lỗi; DAG chuỗi/join/fan-out; schema/mapping sai; graph cycle; sửa catalog/draft sau publish; queue timeout; hủy trước/sau claim; timeout có/không có bằng chứng dừng; claim/renew/result trùng; quyền hết hạn/thu hồi; kết quả muộn; mất phản hồi sau commit/spawn; restart DB/engine/Client. [Review thiết kế](../reports/foundation-design-review.md) chỉ ghi đối chiếu tài liệu, chưa phải test ứng dụng.

Condition/loop bị từ chối trong baseline. Skill 0–1–2 chỉ test binding/version/mapping; review từng Part cần AGN-002/RUN-007, không đạt chỉ bằng DAG ba node.

## Câu hỏi cần ADR hoặc thiết kế tiếp theo

Production Temporal, backup/restore hai kho, secret store/provider adapter chi tiết, retention/redaction đầy đủ, Human/review/partial retry và nâng cấp interpreter đang chạy. Snapshot/mapping, lease, topology local, nguồn trạng thái, PC ưu tiên và queued filter đã chốt trong baseline.
