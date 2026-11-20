# Review chéo thiết kế nền — 2026-11-16

## Phạm vi và kết quả

Hoàn tất phạm vi **Design** của BASE-001 → PROC-001 → REL-004 → RUN-001 → API-001 theo yêu cầu hệ thống quản lý tổng và Process động. Skill 0–1–2 chỉ là bộ test. Chưa triển khai ứng dụng, database/migration, Temporal/worker, CF Client, editor hoặc các menu. Không chạy lại CLI/Skill và không coi phép thử độc lập là nghiệm thu ứng dụng.

ADR 0001–0003 chuyển từ Proposed sang Accepted về thiết kế local trong phạm vi được giao; ADR 0005 ghi quyết định mới về snapshot/mapping/inbox/outbox/quyền. Giữ nguyên nội dung và lịch sử ADR 0004 đã Accepted: câu Temporal còn Proposed trong ADR 0004 phản ánh thời điểm quyết định DB; trạng thái hiện tại lấy từ ADR 0003 và bảng ADR trong overview, không sửa lại lịch sử DB.

## Mâu thuẫn và khoảng trống đã xử lý

| Trước review | Kết quả và nguồn chuẩn |
|---|---|
| Task nền chỉ mô tả Process Skill 0 | [Domain](../architecture/domain-model.md#định-nghĩa-process-động-và-snapshot): DAG cấu hình được, interpreter/format version; không hard-code Skill hoặc chủ đề |
| Agent/Skill mutable, snapshot còn mở | Snapshot tại publish gồm bundle digest, runtime/model/contract và policy; không secret, không thay catalog để tái dựng run cũ |
| Input/output/mapping chưa chốt | JSON Schema 2020-12, binding/JSON Pointer có kiểm tra nguồn tổ tiên; không expression/shell; schema HTTP tại [OpenAPI](../../openapi/openapi.yaml) |
| SQLite và Temporal chưa rõ ai ghi/nguồn trạng thái | Server là writer nghiệp vụ; Temporal history để điều phối/replay; Activity qua API nội bộ, inbox/outbox và CAS theo [ADR 0005](../architecture/decisions/0005-versioned-process-execution.md) |
| Ghi DB/gọi engine có thể chỉ thành công một bên | Transaction nghiệp vụ + outbox, relay ít nhất một lần, Workflow/command ID ổn định, receipt/inbox khi mất phản hồi |
| Hết lease/timeout có thể bị coi đã dừng và giao lại | [Execution](../architecture/execution-model.md): reconciling không terminal, không cấp lại Attempt; dừng best effort và bằng chứng đối soát |
| Claim trùng, crash sau spawn và kết quả muộn chưa có luật | Runner/session/generation, grant, journal trước spawn; receipt cùng ID; stale result bị chặn, observations chỉ giữ bằng chứng |
| PC node với Manual/Schedule chưa có ưu tiên | PC node ràng buộc; Manual/Schedule chỉ là mặc định; file qua artifact ID/Server, không local path giữa PC |
| Queued chưa có nhóm filter, archive chỉ xét running | Running filter gồm mọi trạng thái chưa terminal; chặn archive/remove trong queued/reconciling/cancelling theo requirements |
| Chọn model/Skill ở form có thể override version | Form cấu hình sửa draft/publish; Run chỉ chọn version/input/default Runner, không nhận model/Skill override |
| Output run tùy chỉnh dễ vượt REQ-RUN-05 | Giữ toàn bộ output của Task cuối theo Task ID; không custom output mapping trong baseline |
| Baseline thành công dễ lẫn review nội dung | Process dừng + output schema + artifact hợp lệ mới succeeded; Agent review/Target approval là mốc riêng |

Nguồn chuẩn đã đối chiếu: ADR 0001–0005, architecture overview, domain, execution, requirements/glossary, project structure, OpenAPI/Client protocol và năm file task. README/AGENTS, docs index, setup, plan và task triển khai bị ảnh hưởng đã đồng bộ. Không thay menu hoặc mục tiêu sản phẩm; Human/Continue, review từng Part, retry một phần và condition/loop không được mô tả là đã có trong baseline.

## Kiểm tra thực sự đã chạy

- `node openapi/check-contract.cjs`: cấu trúc OpenAPI hợp lệ; 51 schema biên dịch; 20 ca schema và 5 ca graph review đạt; 23 path, 26 operation có ID riêng, mutation có Idempotency-Key và API nội bộ scope engine.
- Các ca schema gồm Process chung một node, DAG fan-out/join, fixture ba Skill, loại node chưa hỗ trợ, shell field, timeout 0, runtime override, reconciling, thiếu output, exit khác 0, chưa xác nhận dừng và lệnh engine cố ghi trạng thái tùy ý. Graph review gồm chuỗi, fan-out/join, cycle và tham chiếu Task thiếu; đây là kiểm tra dữ liệu mẫu, không chạy engine.
- Kiểm tra liên kết Markdown/anchor và task dependency được chạy riêng; số liệu cuối ghi ở phần kết quả bên dưới.
- Đã tra tài liệu Temporal chính thức cho local development persistence và Activity idempotency (liên kết trong ADR 0003); [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785), [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901) và [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core) là căn cứ chọn canonical JSON/pointer/schema. Đây là xác minh tài liệu, không kiểm chứng SDK trên máy.

Tool kiểm tra chỉ cài dưới `runtime/design-review/` ngoài Git. Thử cài validator Python bằng pip thất bại do download bị ngắt/khóa file; sau đó dùng Swagger Parser/Ajv qua npm thành công. Không thay requirements/lockfile ứng dụng. Lệnh `npm` ban đầu bị PowerShell execution policy chặn; dùng `npm.cmd`, không đổi execution policy. Không cài hoặc chạy dịch vụ.

Phiên bản kiểm tra thực tế: `@apidevtools/swagger-parser@13.1.0`, `ajv@8.20.0`, `ajv-formats@3.0.1`, `yaml@2.9.1`. Script kiểm contract được giữ tại `openapi/check-contract.cjs`; dependency chỉ ở runtime. Các ca không thực thi adapter, không giả định ID fixture là runtime đã khả dụng.

Kết quả kiểm tra tài liệu: `.venv/Scripts/python.exe -X utf8 runtime/design-review/check_docs.py` (script rà soát cục bộ, ngoài Git) — không có đích liên kết/heading thiếu, mã phụ thuộc thiếu hoặc chu trình. Số file/liên kết/task được ghi ở lần kiểm tra cuối bên dưới; các đường link HTTP không nằm trong phép kiểm tra file local.

Lần kiểm tra cuối: **74 file Markdown, 695 liên kết local, 45 task**; không liên kết/anchor thiếu, không phụ thuộc thiếu, đồ thị phụ thuộc không chu trình. Contract kiểm tra lại đạt **51 schema, 20 ca schema, 5 ca graph, 23 path và 26 operation**. Tất cả menu/mốc sử dụng trong plan vẫn chưa hoàn thành.

## Giới hạn và việc tiếp theo

BASE-002/BASE-003 và DATA-001 mới tạo scaffold/hạ tầng/schema khi được giao. CLI-001/CLI-002/RUN-002 phải chứng minh CAS, journal, upload, revoke, timeout, cancel, outbox crash và kết quả muộn; static validation không chứng minh các bảo đảm runtime này. REL-001 kiểm chứng recovery, REL-002 audit/security xuyên luồng, REL-003/AGN-002 thiết kế Human/review/partial retry. Không hoàn tất menu hoặc mốc sử dụng chỉ vì năm task Design xong.

Topology Temporal được chọn chỉ cho local development có persistence file riêng; chưa có thiết kế production/backup được nghiệm thu. Python 3.14/SDK/binary compatibility và replay phải kiểm chứng tại BASE-003. Provider secret store, retention và vận hành nhiều PC vẫn có giới hạn theo tài liệu kiến trúc.
