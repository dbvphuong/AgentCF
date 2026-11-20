# Hợp đồng CF Client v1

> Status: Design baseline · 2026-11-16 · Chưa triển khai

[OpenAPI](../../openapi/openapi.yaml) là nguồn chuẩn cho HTTP payload, enum và response. Tài liệu này giữ thứ tự giao tiếp, bảo mật và quy tắc crash; không định nghĩa một bộ schema thứ hai. Quyết định tại [ADR 0005](decisions/0005-versioned-process-execution.md), state machine tại [execution](execution-model.md).

## Xác thực và ghép nối

Local desktop CLI-004: Web tạo mã dùng một lần 256-bit và tracking ID riêng; link agentcf chỉ mang origin Server và mã trong fragment, không nhận lệnh/đường dẫn thực thi. Client xác nhận, đổi mã lấy credential, mở session và gửi heartbeat. Web chỉ báo connected khi đã có heartbeat sau thời điểm tạo session. Credential desktop được DPAPI theo người dùng Windows; endpoint tracking/inspect không trả token. Khi thoát bình thường, Client đóng session sau khi drain việc hiện tại; heartbeat có stop_attempt_ids để dừng việc mất quyền. [Code và giới hạn CLI-004](../development/tasks/client/004-desktop-onboarding.md); không coi đây là kiểm chứng toàn bộ giao thức Design bên dưới.

Bổ sung local 2026-11-18: chooser file Skill dùng `POST /v1/runners/{runner_id}/skill-files`, Web đọc kết quả theo request ID. Heartbeat trả `skill_file_requests`; Client chỉ liệt kê thư mục/file `.md` trên chính PC và gửi metadata qua endpoint `/result` bằng credential/session hiện hành. Request có TTL 60 giây trong bộ nhớ, mất sau restart; lỗi/hết hạn cho phép mở lại hoặc dán đường dẫn. Không gửi nội dung file/ref, không tạo Run, không gọi CLI/model. Schema tại OpenAPI; bằng chứng triển khai tại [SKL-005](../development/tasks/skills/004-main-markdown-file.md). Phần Design baseline bên dưới vẫn giữ các yêu cầu giao thức tổng quát chưa nghiệm thu.

Người vận hành local có credential riêng scope operator, được bootstrap ngoài source khi triển khai. Không coi loopback là xác thực. Server tạo pairing code ngẫu nhiên tối thiểu 256 bit, chỉ dùng một lần, hạn 5 phút, lưu hash; operator chuyển code trực tiếp cho Client, không dùng query string/log. Đổi code tạo Runner và credential opaque riêng, Server giữ hash; Client giữ credential trong kho OS của người dùng, không trong repo hoặc Skill.

Credential Runner hạn mặc định 30 ngày, có thể revoke/rotate bởi operator; hết hạn phải ghép nối/rotate có chủ đích, không nhận việc bằng credential cũ. Scope engine tách khỏi operator/runner và chỉ có ở Server/worker. Authorization kiểm tra scope lẫn quyền trên Workspace/Project/Runner. Role của Agent và checkbox prototype không thay thế quyền này. Kho secret provider/runtime chi tiết chưa thiết kế ở đây; không gửi credential tài khoản Codex/Antigravity qua giao thức.

Runner tạo session sau mỗi lần khởi động/reconnect, gửi client version, machine fingerprint không nhạy cảm và capability ID/version. Server xác nhận tập capability cho phép; chưa xác nhận thì không dispatch. Session mới vô hiệu quyền session cũ, các Attempt chưa dừng sang reconciling. Heartbeat mang capacity và danh sách Attempt/journal đang thấy; không tự tạo quyền mới hoặc hoàn tất TaskRun. Runner disabled/credential revoked không mở session/claim/renew được.

## Nhận việc và khởi chạy

Skill có phạm vi catalog Global hoặc các Project được gán. Server kiểm phạm vi tại publish Process và tạo Run mới; Client không được dùng danh sách Skill trên Agent để suy ra quyền dùng cho Project khác. Thu hẹp phạm vi không sửa Run đang có hoặc lịch sử đã được tạo.

1. Client poll work hoặc nhận WebSocket hint. Hint chỉ có loại và ID tài nguyên, không có input/token/lệnh thực thi. Đường HTTP trong OpenAPI là đủ chạy baseline; chưa cần WebSocket server để nghiệm thu contract.
2. Claim bằng Runner credential + session ID + Idempotency-Key. Server CAS theo luật execution, trả Assignment với run/task/attempt/generation, token, expires_at/server_time, snapshot/input và manifest bundle IDs. Poll không reserve việc, claim mới tạo quyền.
3. Client kiểm scope, session/generation, version adapter, bundle digest, model availability, quyền Tool và đường dẫn staging local. Không tự thay runtime/model. Bundle từ endpoint Server đã cấp quyền. Với Skill local theo [ADR 0006](decisions/0006-local-skill-paths-and-pc-outputs.md), chỉ dùng đường dẫn tuyệt đối/PC/thư mục làm việc đã được cấu hình và publish; Client kiểm file trên đúng PC và ghi hash thực tế trước chạy. Không mở URL/đường dẫn từ input như một lệnh thực thi tùy ý.
4. Ghi journal bền vững với Attempt, generation, launch ID, request IDs và trạng thái planned trước spawn. Journal không ghi secret; có receipt/launch evidence và spool output an toàn ngoài Git. Một Attempt chỉ một launch, không spawn lại nếu journal cho thấy planned/running/unknown sau crash.
5. Chạy adapter đã allowlist. Adapter ghép argv từ cấu hình local và input hợp schema, không shell-eval input. Gửi started event có launch ID/process evidence. Từ lúc claim, Server đã coi quyền có thể được dùng; thiếu started event không cho phép giao lại.
6. Renew theo policy Server; mất khả năng renew thì Client yêu cầu dừng trước expiry với safety margin. Không bảo đảm tool/tiến trình con dừng ngay; ghi bằng chứng và báo observations khi reconnect. Server chặn token hết hạn/thu hồi và không giao lại mù.

## Log, output và artifact

Output gốc ở PC thực thi theo quy trình Skill. Chế độ local báo tham chiếu PC/đường dẫn/kích thước/hash file thật; các node cùng PC dùng thư mục làm việc đã cấu hình để tiếp tục. Không bắt buộc upload output hoặc render ảnh/file trên Web. Upload bên dưới là cơ chế chuyển bản sao khi cấu hình yêu cầu; không được coi metadata đường dẫn là một file đã upload hoặc một file có sẵn ở PC khác.

Event gửi theo request ID, thứ tự local sequence và occurred_at; Server cấp recorded_at/run sequence. Khử trùng theo `(attempt_id, event_id)`; cùng ID khác payload trả conflict. Log được che secret, phân trang/cursor, không nhúng payload đầy đủ. Event `started` cần quyền hiện hành; event `log` không được thay đổi output/status. Sau mất quyền chỉ endpoint observations được nhận bằng chứng.

Client đăng ký artifact metadata trong quyền Attempt rồi PUT byte theo Artifact ID, Server kiểm size/SHA-256 và finalize nguyên tử. Retry PUT cùng nội dung an toàn; khác nội dung cùng ID trả conflict; không overwrite artifact đã finalize. Không nhận filename làm đường dẫn lưu. Web GET qua quyền operator, Client chỉ tải input/bundle/artifact trong assignment hoặc upload của mình. Staging ngăn traversal/symlink/archive escape; không thực thi file chỉ vì nó nằm trong bundle.

Complete cần process_stopped, outcome, output hoặc error và artifact IDs nếu có upload. Server kiểm token/session/generation/deadline, schema, quyền artifact và receipt trước commit; outcome succeeded cần exit_code 0, output hợp lệ và đủ kết quả theo cấu hình. Với local output, Client phải kiểm file thực tế; danh sách artifact upload có thể rỗng. Không tự sửa output hoặc đánh success từ lời model.

## Hủy, timeout và kết quả đến muộn

Server trả stop_requested/stop_reason qua renew hoặc work/heartbeat; Client dừng cây tiến trình best effort. Nếu token đã bị thu hồi hoặc hết hạn, Complete bị từ chối; Client gửi observations chứa launch/process evidence, output/error/artifact tham chiếu đã có. Observation trả accepted chỉ là đã lưu bằng chứng, không đồng nghĩa TaskRun thành công. Server/engine reconcile phải kiểm bằng chứng, scope và audit trước cập nhật trạng thái.

Runner có session mới được gửi observation của Attempt thuộc chính Runner đó dù session cũ không còn hiệu lực; credential phải còn hợp lệ. Credential bị revoke thì không nhận báo cáo bằng credential cũ, cần operator cho phép ghép nối/đối soát; giữ trạng thái chưa rõ. Không có API cho Client tự tuyên bố an toàn để retry hoặc tự tạo Attempt mới.

## Quy tắc retry và lỗi

Mọi mutation trừ exchange pairing code cần Idempotency-Key; exchange dùng code một lần và mất phản hồi cần operator cấp code mới, không tạo Runner trùng bằng đoán kết quả. Principal/operation/resource + key + canonical body xác định receipt. Tra receipt sau xác thực principal/ownership, trước validation lease hiện tại cho mutation đã commit; không dùng receipt cũ để cấp quyền đã hết hạn. Claim/renew response hết hạn trả stale_execution và hướng đối soát.

HTTP 401 credential sai/hết hạn, 403 thiếu scope/quyền, 404 tài nguyên không thuộc phạm vi/không tồn tại, 409 xung đột revision/idempotency/stale_execution/terminal, 422 input/schema invalid, 429 capacity/rate limit, 503 hạ tầng tạm thời. Mỗi lỗi có code/message/correlation ID, field errors khi thích hợp; không echo token/secret. Retry 429/503 dùng cùng key và backoff, không chạy runtime lần nữa.

Timestamp RFC3339 UTC; ID opaque, digest SHA-256 lowercase hex. Protocol version v1 trong URL, schema/definition/interpreter version riêng. Client không hỗ trợ version thì từ chối trước spawn và báo lỗi có ngữ cảnh. Các default thời gian thuộc execution model và Assignment, không hard-code ở adapter.

## Giới hạn

Contract chưa chứng minh pairing, OS secret store, journaling, upload, process stop hoặc reconnect chạy thật. CLI-001/CLI-002, DATA-001/RUN-002 hiện thực phần tối thiểu; REL-001 kiểm chứng recovery rộng; REL-002 bổ sung audit/security đầy đủ. Antigravity/Robot chỉ chạy khi adapter tương ứng được kiểm chứng. Human/Continue và API CRUD hoàn chỉnh của mọi menu thuộc các task riêng, chưa được coi là đã thiết kế hết bởi API-001.
