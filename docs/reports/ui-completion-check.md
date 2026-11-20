# Kiểm chứng giao diện Agent CF theo prototype

Ngày: 2026-11-17. Mẫu đối chiếu: [prototype đã review](../../demo/agent-cf-prototype/README.md). Hành vi lấy từ [requirements](../product/requirements.md); code sản phẩm nằm trong `apps/web`, không sửa hoặc chuyển dữ liệu mẫu từ `demo` vào DB ứng dụng.

## Phạm vi đã triển khai

- Sidebar tím, tám menu, điều hướng hash/deep link, tìm màn hình bằng Ctrl/Cmd+K, menu mobile, modal native có focus và Escape, bảng cuộn ngang. Các màn có loading, empty, validation/error và xác nhận thao tác.
- Agents: danh sách/tìm kiếm, Active/Archived, tạo/sửa Role, Model, Skills, Allowed tools, Archive/Restore/Delete, token tháng theo dữ liệu Server hoặc thông báo chưa có dữ liệu.
- Skills/Tools: catalog, version draft/published, xem và sửa draft, clone thành version mới, publish bất biến, cấu hình Tool và xem Agent được phép dùng.
- Settings: Providers & API, Models, Roles, General. Form API key dùng password, không lưu trình duyệt hoặc nạp lại secret. Test API gọi endpoint kiểm tra ở Server, chỉ trả HTTP status/lỗi an toàn; không xác nhận mọi model đều chạy được.
- PC: ghép nối một lần trong 10 phút, hạn mã theo giờ Việt Nam, trạng thái/tải/heartbeat, Disable/Enable/Revoke, current Run và TaskRun mở lịch sử. Dữ liệu hệ điều hành chưa được Client báo cáo thì hiển thị `—`. Trạng thái hiển thị quá hạn heartbeat không đổi lease hoặc giao lại việc.
- Projects: tạo/sửa, tìm kiếm, Active/Archived, Archive/Restore/Delete, Team riêng và PM bắt buộc, Targets có thời gian và số kết quả được duyệt. Xóa draft chưa dùng có thể xóa vật lý; mục đã có version published hoặc Run chuyển Archive để không phá trigger bất biến. Đây là giới hạn bảo toàn dữ liệu chặt hơn trường hợp “chưa có Run có thể xóa” trong requirements.
- Process editor: thêm/sửa/xóa/kéo Agent hoặc Robot, dependency, input/output schema và mapping JSON, chọn Agent thuộc Team, Skill, runtime hoặc RobotVersion/PC, lưu draft có revision CAS, Validate, Publish và tạo draft tiếp theo. Có cảnh báo khi rời editor chưa lưu. Snapshot published lấy metadata Agent/Skill/Robot và model chính xác từ catalog, kiểm tra cycle/reference/quyền Tool/tổ tiên mapping tại Server.
- Schedule: lưu lịch ghim version published, Start/Stop riêng với Run/Cancel. Form chạy dùng published version và input JSON bất kỳ; bỏ lựa chọn model/runtime đè snapshot và chủ đề Skill fixture hard-code khỏi form cũ.
- Runs: lọc Project/Process/Status/Run ID/ngày, cursor Previous/Next, 25/50/100 dòng, STT nối tiếp, tổng khớp/tổng số từ DB, tiến độ và thời gian. Tab Runs trong Project dùng lại module Runs và lọc phía Server.

Migration mới: `010_project_management.sql` thêm mô tả, PM/Team và thời gian/tiêu chí Targets. Không sửa migration đã có hoặc dữ liệu người dùng để kiểm thử.

## Kiểm tra và bằng chứng

Kết quả lần bàn giao cuối: **166 passed, 1 skipped** (Python; skip Temporal opt-in), **19 passed** (Web); TypeScript/build đạt; OpenAPI **73 schemas, 51 paths, 62 operations**; Edge smoke đạt **17 kiểm tra viewport** và các luồng ghi dữ liệu nêu dưới. Lần full suite cuối không còn lỗi backup; vẫn giữ ghi nhận các lần `WinError 145` trước đó để không che giới hạn môi trường.

- Web: `npm.cmd --prefix apps/web test`, `npm.cmd --prefix apps/web run typecheck`, `npm.cmd --prefix apps/web run build`.
- Python: `.venv/Scripts/python.exe -m pytest -q`; regression mới ở `apps/server/tests/integration/projects/test_project_web.py`, kiểm tra persistence, Team/Targets, draft CAS, graph sai, snapshot bất biến, lịch ghim, khóa API không lộ trong response, thời gian pairing, lọc/phân trang Runs và vòng đời xóa.
- Contract: `node openapi/check-contract.cjs`. Các operation quản lý UI được đồng bộ từ schema của HTTP boundary, ghi rõ phạm vi `implemented-local`, không mô tả bearer authorization từ xa như tính năng đã có.
- Edge headless qua CDP: `node apps/web/tests/browser/smoke.cjs`, Server/SQLite riêng trong thư mục tạm và Vite proxy riêng. Tạo Skill/version/publish, Agent, Project, Target, Process, kéo node, publish/reload, Save/Start/Stop Schedule, tạo/hủy Run và pairing/Disable PC. Kiểm tra tám menu ở 1440px và 390px, cùng editor mobile; không có lỗi JavaScript và không tràn ngang toàn trang. Ảnh tại `runtime/ui-review/` (không đưa dữ liệu runtime vào Git).
- Đã xem ảnh Settings desktop và Agents mobile; sửa bảng mobile bị ép hẹp, dữ liệu Skill không hiển thị đúng từ API list, và thời gian pairing không hợp lệ cho trình duyệt.
- Có lần full suite và lần chạy riêng backup gặp `WinError 145` khi dọn thư mục tạm; chạy lại nhóm backup đạt 9/9. Không sửa hoặc làm yếu test backup để bỏ qua lỗi. Kết quả lần kiểm tra cuối được ghi ở task bàn giao.

## Giới hạn nghiệm thu

Kiểm thử trình duyệt tạo/hủy Run trước thực thi; không gọi Codex/Antigravity thật, không tiêu thụ token và không nghiệm thu lại toàn bộ runtime. [BASE-003](../development/tasks/base/002-application-bootstrap.md#base-003) vẫn cần kiểm chứng Temporal Service/restart.

UI và API editor đã có, nhưng chưa thể đánh dấu toàn bộ [PROC-003](../development/tasks/projects/processes/002-process-editor.md#proc-003) theo thiết kế nền: JSON Schema đầy đủ, fingerprint RFC8785, bundle delivery/verification và authorization operator từ xa chưa được chứng minh bởi thay đổi này. Endpoint tạo mới editor nhận header idempotency từ Web nhưng chưa deduplicate; draft save/publish có revision CAS. Không đồng nhất các request đó với contract Run có receipt.

Review mã worker hiện có cho thấy nhánh Agent còn chọn hành vi theo tên Skill/task và nhánh mặc định dùng đường Skill 0; mapping lưu trong editor chưa được claim resolver áp dụng đầy đủ. Theo dõi riêng tại [RTM-008](../development/tasks/runtime/005-generic-snapshot-execution.md) và [RUN-008](../development/tasks/runs/005-runtime-input-mapping.md). Không sửa ba Skill mẫu hoặc dùng kết quả UI để tuyên bố đã nghiệm thu generic runtime.

Credential provider của catalog hiện có chưa dùng secret store mã hóa thực sự dù tên cột là `api_key_ciphertext`; UI không trả/ghi log secret nhưng không giải quyết được bảo vệ dữ liệu tại rest. Theo dõi tại [SET-004](../development/tasks/settings/004-provider-secret-store.md). Chưa có remote authentication nên chỉ chạy Server theo loopback đã cấu hình.
