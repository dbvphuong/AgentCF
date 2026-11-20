# AGENTS.md

Tài liệu này quy định cách các coding agent làm việc trong repository Agent CF. Phạm vi áp dụng là toàn bộ repository. Nếu một thư mục có `AGENTS.md` riêng, file gần mã nguồn hơn được phép bổ sung hoặc ghi đè quy tắc cho phạm vi thư mục đó.

## 1. Mục tiêu làm việc

- Xây Agent CF thành hệ thống có thể phát triển lâu dài, dễ đọc và dễ thay đổi.
- Giữ code, test, hợp đồng và tài liệu đồng bộ trong cùng một thay đổi.
- Ưu tiên cấu trúc rõ ràng và giải pháp vừa đủ cho giai đoạn hiện tại.
- Không mô tả tính năng dự kiến như thể đã được triển khai.

## 2. Trạng thái repository hiện tại

- BASE-011: Các nhóm xóa trên Web hiển thị tiếng Việt với tên Model/Agent/Skill/Tool/Robot/Project/Process/PC liên quan; Run có giờ Việt Nam/trạng thái, không đưa ID kỹ thuật/raw JSON thay tên. Giữ chính sách/mã HTTP/giao dịch xóa; Robot có modal lỗi/thử lại, không đề xuất Archive. 135 integration tests liên quan, 23 Web tests, build và 10 browser flows đạt; Server local health/schema 23 và số hàng dữ liệu giữ nguyên sau nạp lại. Phạm vi/giới hạn tại `docs/development/tasks/base/010-deletion-feedback.md`.

- BASE-010: Sidebar dùng CF phẳng/wordmark SVG, tám icon nét 1.7 và hover/nhấn đổi màu không xê dịch; giữ tên menu/hash/command palette/nghiệp vụ. Build/TypeScript, 22 Web tests và browser fixture navigation/mobile/reduced-motion đạt. File logo cũ giữ nguyên, không đổi API/runtime. Bằng chứng và giới hạn tại `docs/development/tasks/base/009-sidebar-identity.md`.

- RTM-011: Client 0.3.2 gọi Skill local bằng prompt trực tiếp hai dòng “Gọi skill <path .md> / cho chủ đề <path>”; chỉ nối lưu ý node/lần chạy do người dùng nhập. Bỏ file yêu cầu trung gian và chỉ dẫn/JSON tự ghép; giữ cwd Project, quyền, timeout, model và kiểm tra file thật. Chi tiết `docs/development/tasks/runtime/008-direct-skill-invocation.md`; không tự đóng các lỗi CLI/model/mạng hoặc RTM-008/RUN-008/BASE-003.

- PROC-007: Migration 023 chuyển root node đã lưu sang Project đang trống khi các root hiện tại thống nhất; không ghi đè Project đã cấu hình, không đoán khi nhiều root và không sửa snapshot/file. Đã sửa lỗi thiếu thư mục của Project thực tế sau PROC-006; run-context 200/root đúng, schema 23, 42 regression tests đạt. Chi tiết `docs/development/tasks/projects/processes/006-legacy-project-root.md`.

- PROC-006: Node AI bỏ ô thư mục làm việc/output, current Run lấy cwd từ Project, kể cả node cũ có override. Khi Run chỉ chọn chủ đề; Skill quyết định vị trí output theo quy trình gốc. Snapshot/API lifecycle cũ giữ tương thích. Kiểm chứng tại `docs/development/tasks/projects/processes/005-project-working-directory.md`. Đối chiếu Codex: Web/config local cùng model Sol 6.1, nhưng Client gọi CLI npm 0.147.0 còn IDE dùng 0.164.0-alpha.11.1; không suy quyền tài khoản chung từ lỗi bản cũ.

- RTM-010: Client 0.3.1 thêm nhánh Skill local Antigravity (cwd/add-dir/print/quyền file/timeout/log/PID), dùng chung kiểm output thật và Skill không đổi; 100 Client tests đạt. Thử tạo file thật bằng Claude trong thư mục riêng đạt. Đã thay binary PATH agy 1.0.6 bằng 1.1.20 đang có trong `.gemini/bin` sau sao lưu và người dùng cho phép: nhận đúng Gemini High, nhưng headless còn lỗi mạng ở eligibility check/profile picture, chưa nghiệm thu Gemini. Giữ model node, từ chối fallback. Chi tiết `docs/development/tasks/runtime/007-antigravity-local-skill.md`; không đóng RTM-008/RUN-008/BASE-003.

- BASE-009: Web dùng Skill đã lưu và Process Lưu/Chạy, không yêu cầu Draft/Version/Publish. Robot giữ phiên bản và Lưu dùng ngay. Migration 022, snapshot Run bất biến, lịch theo cấu hình hiện tại; API cũ giữ tương thích. Xem [task](docs/development/tasks/base/008-save-and-run.md) và [ADR 0011](docs/architecture/decisions/0011-save-and-run-current-configuration.md).

- PC-004/ADR 0010: Client 0.3.0 có device identity/proof DPAPI; migration 020 unique active Workspace/device, pairing target reconnect giữ PC/config và rotate credential, session authenticated tự bind PC legacy, không xóa fingerprint khi thiếu. Hủy kết nối riêng với Xóa (chặn unfinished Run; reconnect chỉ chặn khi có Attempt đang thực thi dở dang, cho phép Run queued để nhận việc). Cột Thao tác có Kết nối/Hủy kết nối + Sửa/Xóa. Migration 021, Client đọc CPU/RAM thật từ Windows và hiển thị used/total RAM, offline ẩn sample cũ; heartbeat máy thật đã xác nhận giữ 1 PC và ID mới nhất. Bằng chứng/giới hạn `docs/development/tasks/runners/004-device-reconnect-metrics.md`.

- AGN-005: Agent là người phụ trách có thể làm nhiều việc, Skill là một việc; trong Process chọn Agent nào và Skill nào thì Agent đó làm Skill đó, không bắt gán cứng Skill ở catalog. Bỏ trường chọn Skill trong form tạo/sửa Agent; cột Skills trên bảng Agent điều phối chuyển thành view hiển thị (chỉ đọc) các Skill mà Agent đó đang phụ trách từ các node của phiên bản Process mới nhất đã lưu. Bỏ kiểm tra "Skill chưa được gán cho Agent" khi Validate và Publish Process. Bằng chứng tại `docs/development/tasks/agents/004-derived-agent-skills.md`.

- RUN-010/ADR 0009: Chạy Skill local theo thư mục chủ đề có sẵn (chọn qua Client hoặc dán path), yêu cầu riêng tùy chọn; các bước cùng topic, cwd vẫn root Project. Migration 019 thêm root Project, Publish giải quyết default PC/root rồi ghim snapshot; Client kiểm folder tồn tại/trong root trước spawn, inventory theo chủ đề, không tự mkdir/ghi chat thay file. Node bỏ ba ô mapping/schema chưa hoàn thiện, Nhiệm vụ bổ sung không bắt buộc. Generic JSON còn trong nâng cao. Bằng chứng `docs/development/tasks/runs/007-topic-directory-launch.md`; không đóng vòng Agent API/RTM-008/RUN-008/Temporal.
- BASE-008: Đo API local ~6–15 ms; giảm tải khi nhập/cuộn modal bằng pause video logo khi modal/tab ẩn/reduced-motion và bỏ blur backdrop, giữ logo/overlay. Browser kiểm input/frame và không gọi API khi gõ; phạm vi/giới hạn tại `docs/development/tasks/base/007-input-scroll-responsiveness.md`, không khẳng định mọi nguồn lag đã hết.

- SKL-006 (lịch sử; BASE-009 đã bỏ cột/nút Version trên Skill): Bảng Skills từng thêm cột Version, phân biệt Chưa có version, Chưa Publish/Draft vN và published mới nhất (kèm draft mới hơn). API Skill bổ sung ba metadata version nullable, modal Versions reload bảng sau lưu/publish; không tự publish hoặc đổi snapshot cũ. Bằng chứng tại `docs/development/tasks/skills/005-version-column.md`.

- PROJ-009: Team là view chỉ đọc từ PM và Agent trong node của version mới nhất đã lưu mỗi Process, khử trùng; không dùng membership thủ công cũ. Bỏ Manage team/Quản lý Team, node chọn trực tiếp mọi Agent active; publish kiểm catalog/quyền thay điều kiện membership. PUT Team cũ deprecated trả 422, giữ bảng cũ và snapshot/history; không migration. Bằng chứng tại `docs/development/tasks/projects/009-derived-team.md`.

- PROJ-008: Chi tiết Project đặt ← Projects bên trái cùng dòng mô tả/PM dưới tiêu đề, không thêm hàng; menu ⋯ giữ bên phải. Bằng chứng tại `docs/development/tasks/projects/008-back-navigation.md`.

- PROJ-007/ADR 0008: Xóa Project/Process xóa hẳn cả published/lịch sử đã kết thúc, không tự Archive; chặn khi còn Run chưa kết thúc, người dùng dừng và chờ trước. Migration 018 cho ngoại lệ DELETE giới hạn từng hàng/connection, giữ bất biến khi sửa; cleanup artifact Server sau commit có retry, giữ file PC/catalog dùng chung và audit xóa. Skill/Agent chỉ bị chặn khi còn node Process draft/published dùng; khi không còn dùng được xóa cả version/snapshot/membership, Agent xóa bỏ gán PM/Team. Bằng chứng tại `docs/development/tasks/projects/007-permanent-deletion.md`.

- PROJ-006: Projects báo kết quả thao tác bằng toast góc phải tự đóng 6 giây; thành công hoặc lỗi API, quy tắc Delete hiện theo PROJ-007. Kiểm chứng UI fixture tại `docs/development/tasks/projects/006-action-feedback.md`.

- PROJ-005: Projects thêm bộ lọc Tất cả; xóa cứng Project gỡ liên kết `skill_projects` trong transaction, giữ Skill/version/file và phạm vi còn lại, không tự chuyển Global. Quy tắc Project có lịch sử/publication đã đổi tại PROJ-007. Bằng chứng tại `docs/development/tasks/projects/005-filter-delete.md`.

- CLI-004: CF Client desktop chung và bộ cài Windows x64 đã có; `run-client.bat` mở Client, demo Skill 0 vẫn riêng. Web Connect PC mở agentcf link/tải installer, chờ xác nhận + session/heartbeat thật; migration 017 tracking pairing/os_name. Client gọn không ô Server/tên PC, quản lý trên Web Center; native tray/single-instance/DPAPI/HKCU startup tùy chọn. Build bằng `infra/build-client.ps1` (bundle CPython + launcher .NET), không cần Python trên máy đích. Bằng chứng và giới hạn tại `docs/development/tasks/client/004-desktop-onboarding.md`; chưa ký số/auto-update, chưa nghiệm thu Windows sạch hoặc toàn bộ runtime/Agent API, không đóng RTM-008/RUN-008/BASE-003.

- SET-005/ADR 0007 tách Agent điều phối (Model API) và công cụ AI thực thi Codex/Antigravity (model CLI). Migration 015 & 016 thêm và nạp đầy đủ ai_tool_models; Settings gom 2 dòng cho 2 công cụ Codex CLI và Antigravity, bấm Chọn model mở modal checklist đa chọn tích các model dùng trong Process (chọn tất cả / bỏ chọn tất cả), tự động ẩn các model không tích khỏi node dropdown để giao diện gọn gàng; cập nhật tự động model mới nhất một chạm (`/sync`), cấu hình hàng loạt (`/configure`), và kiểm tra chẩn đoán công cụ trên PC (`/check`). Node dùng tool_model_id, không lấy model API hoặc đoán từ tên; snapshot/Run validation và Client dispatch đúng adapter. Chi tiết `docs/development/tasks/settings/005-ai-tool-models.md`. Vòng LLM API điều phối tổng quát còn thiếu, review tiêu chí xác định không chứng minh đã có vòng đó; giữ RTM-008 mở.

- PROC-005: Form node có Nhiệm vụ (prompt nguyên văn), Runtime/Model riêng, PC theo nguồn Skill đã lưu (BASE-009); task key tự sinh, trường kỹ thuật trong phần nâng cao. Quản lý Team thủ công ban đầu đã bỏ theo PROJ-009, node chọn Agent active trực tiếp. Migration 014 gán Runtime tùy chọn cho Model; Server kiểm override nhưng giữ Agent/published snapshot. Bằng chứng tại `docs/development/tasks/projects/processes/004-node-task-form.md`; không coi fixture publish là CLI/model thật đã nghiệm thu.

- SKL-005: Form Thêm/Sửa Skill và tạo từ editor có đường dẫn/chọn file `.md` chính qua Client của PC đã chọn; không upload nội dung/ref. Lưu nguồn nguyên tử vào draft, giữ version published. Cho phép tên file `.md` bất kỳ; browse metadata ngắn hạn qua heartbeat, không chạy model. Phạm vi và kiểm chứng tại `docs/development/tasks/skills/004-main-markdown-file.md`.

- PC-003: Menu PC giữ Connect PC phía trên; mỗi dòng Sửa tên/Xóa kết nối. Migration 013 giữ identity lịch sử, thu hồi credential/session và tắt lịch liên quan, chặn xóa khi còn run liên quan chưa terminal. File trên PC giữ nguyên; chi tiết tại `docs/development/tasks/runners/003-edit-remove.md`.

- BASE-007 bỏ nút/bộ lọc Archive/Restore ngoài Project trên Web (Skills/Tools/Agents/Robots/Roles/Process). Project giữ nguyên Ngừng hoạt động/Kích hoạt lại. Backend/API/trạng thái dữ liệu cũ và bảo vệ Delete/lịch sử giữ tương thích, không tự khôi phục hay xóa dữ liệu. Bằng chứng tại `docs/development/tasks/base/006-project-only-lifecycle-controls.md`.
- BASE-006 giảm ID kỹ thuật trên Web: bảng/form ưu tiên tên và số version; ID/hash/output JSON nằm trong disclosure Chi tiết kỹ thuật mặc định đóng, có sao chép. Giữ nguyên dữ liệu/API/URL và Model ID cấu hình, mã ghép nối, đường dẫn file. Phạm vi/kiểm chứng tại `docs/development/tasks/base/005-visible-identifiers.md`; không thay runtime hoặc hợp đồng backend.
- SKL-004 bổ sung phạm vi Skill Global hoặc nhiều Project (migration 012); form tích chọn, cột/bộ lọc Project, danh sách Skill trong Process theo phạm vi và tạo Skill từ editor chọn sẵn Project. Backend kiểm publish/Run mới, bảo toàn lịch sử; clone thêm liên kết với Skill riêng, không nhân đôi catalog. Skill có trước migration giữ Global. Bằng chứng tại `docs/development/tasks/skills/003-project-scope.md`.
- RTM-009 bổ sung chế độ Skill local: version giữ đường dẫn tuyệt đối `SKILL.md` và PC sở hữu, node giữ PC/thư mục làm việc; Codex dùng tool tạo/sửa file thật, Client báo metadata đường dẫn/hash, không bắt upload và không ghi chat thay output. Chuẩn sản phẩm tại requirements và ADR 0006; phạm vi/kiểm chứng tại `docs/development/tasks/runtime/006-local-skill-pc-output.md`. Demo hiện hành làm việc trong `tests`; giữ ba Skill gốc, archive Process demo upload cũ và giữ lịch sử. Không suy ra Antigravity/tool bất kỳ hoặc toàn bộ runtime tổng quát đã nghiệm thu.
- PROJ-004 bổ sung script tạo Project test Skill 0 qua HTTP, PC test chỉ nhận version được cấu hình và `run-skill0-test.bat`; nhánh Skill 0 đọc instruction/standard/Agent snapshot và timeout của node, Codex spool log khi output dài. Hướng dẫn tại `docs/development/setup.md#project-test-skill-0-bằng-codex-cli`; trạng thái/bằng chứng tại `docs/development/tasks/projects/004-skill0-test-project.md`. Không coi runner test này là daemon production hoặc đóng RTM-008/RUN-008/BASE-003.
- Agent CF đang ở giai đoạn khởi tạo; đã có ứng dụng Web/Server/Client chạy được, kiểm thử end-to-end Process động và nghiệm thu các menu cốt lõi.
- PROJ-003 bổ sung bảng Projects có mô tả riêng, trạng thái xanh/đỏ bằng tiếng Việt, menu ⋯ và xác nhận theo tên hành động; API nhân bản nguyên tử toàn bộ cấu hình với ID riêng, Targets giữ số liệu, lịch bản sao tắt và không chép lịch sử thực thi. Phạm vi/kiểm chứng tại `docs/development/tasks/projects/003-project-table-actions.md`; không nhân đôi danh mục Agent/Skill/Robot/PC hoặc sửa Project gốc.
- Windows có `run.bat` ở root gọi `infra/start-local.ps1` để mở Server/Web local, kiểm tra readiness, log và dừng tiến trình do launcher sở hữu; cách dùng tại `docs/development/setup.md#chạy-nhanh-trên-windows`, bằng chứng BASE-005. Launcher phục vụ UI, không tự chạy Temporal/worker/Client.
- Bổ sung UI theo prototype ngày 2026-11-17: tám menu với sidebar tím/mobile, Projects/Team/Targets, editor graph draft/validate/publish, catalog Agents/Skills/Tools/Settings, PC pairing và Schedule/Run dùng dữ liệu local thật; migration 010. Bằng chứng tại `docs/reports/ui-completion-check.md`. Review UI phát hiện các khoảng trống runtime tổng quát (`RTM-008`, `RUN-008`) và secret store provider (`SET-004`); không dùng việc có UI hoặc test fixture để đánh dấu toàn bộ menu/production đã nghiệm thu. BASE-003 vẫn cần kiểm chứng Temporal Service/restart.
- ADR 0001–0003 đã `Accepted` về thiết kế nền local; ADR 0005 chốt Process động/snapshot/mapping, outbox/inbox và quyền thực thi. ADR 0004 giữ quyết định SQLite nghiệp vụ; ADR 0003 chọn Temporal development server có file riêng cho local. Đã có `openapi/openapi.yaml`, contract Client và ví dụ thiết kế; BASE-001/PROC-001/REL-004/RUN-001/API-001 hoàn tất Design. Đã triển khai khung Web/Server/Client (BASE-002), SQLite schema/migration 001–009 (DATA-001, ROB-001, AGN-002, REL-001/003, PROC-004, OVW-001), catalog Settings/Skills/Agents (SET-001/002, SKL-001/002, AGN-003), hệ thống ghép nối/heartbeat/tiến trình Runner (CLI-001/002/003, PC-001), các adapter runtime Codex (RTM-005), Antigravity (RTM-006 đã kiểm chứng transport, xử lý console buffer qua trích xuất SQLite trajectory, mapping model nghiêm ngặt từ chối fallback ngầm, thực thi Skill và resume phiên với CLI thật) cùng năng lực tìm kiếm Web cho review (RTM-007), toàn bộ hệ thống điều phối ProcessRun/TaskRun/Attempt, claim việc CAS, worker Client, API lịch sử/artifact an toàn và giao diện Web Runs (RUN-001 đến RUN-007), catalog Robots, version bất biến, node thực thi ghim PC, worker thực thi và thống kê theo version từ dữ liệu thực tế (ROB-001), toàn bộ đặc tả tiêu chí duyệt chất lượng, vòng lặp Agent đánh giá/yêu cầu sửa có giới hạn (`max_revisions`), khử trùng quyết định, bảo toàn checkpoint artifact và luồng cố định Skill 0 → 1 → 2 có chặn hạ nguồn khi lỗi (AGN-001, AGN-002, RUN-007), cơ chế đối soát sau gián đoạn (reconciliation), từ chối kết quả muộn/hết hạn lease, ghi nhận bằng chứng hậu kỳ (observation), cơ chế tạm dừng chờ người dùng và Continue an toàn (REL-001, REL-003), toàn bộ hệ thống quản lý lịch chạy Schedule, chính sách lựa chọn PC, phiên bản ghim bất biến và màn hình Tổng quan Overview từ dữ liệu thật, khối cảnh báo lỗi đỏ chưa xử lý, tiến độ dự án/mục tiêu và xếp hạng token Agent thực tế (PROC-004, OVW-001), cùng cơ chế sao lưu snapshot online SQLite nhất quán, kiểm tra toàn vẹn và phục hồi kèm đối soát quan hệ mồ côi (DATA-002), hệ thống audit append-only bất biến, che dấu tự động secret và kiểm thử ma trận quyền xuyên suốt toàn hệ thống (REL-002), cùng bộ kiểm thử toàn diện E2E Process động (Agent → Robot → Review Agent, cấu hình Skill động, failure cascade, robot timeout, recovery, human continue) với test tự động đạt 170 passed, 1 skipped (Python) và 19 passed (Web), kiểm tra hợp đồng OpenAPI đạt 74 schemas, 53 paths, 64 operations. BASE-003 đã có SDK/worker/probe/launcher, chưa kiểm chứng Service/restart do vướng tải binary Temporal CLI trên máy hiện tại. Hướng dẫn chạy và kết quả tại `docs/development/setup.md`, `docs/reports/foundation-bootstrap-check.md` và `docs/operations/backup-restore.md`. Các mốc "Chạy Skill 0 qua Web", "Skill 0 → 1 → 2 có Agent duyệt", "Khôi phục sau gián đoạn", "Chờ người dùng và Continue" cùng các menu "Overview", "Runs" và "Robots" đã hoàn thành nghiệm thu.
- Đã có script chẩn đoán tại `apps/client/scripts/probe_local_runtime.py`, unit test và Skill fixture tại `tests/fixtures/runtime-probe/`. Codex đạt Skill thử/resume; Antigravity đạt Skill/resume qua CMD tương tác, còn giới hạn print/pipe. Đọc `docs/reports/local-runtime-check.md` trước khi tích hợp; không coi script chẩn đoán là Client production. `tests/.agents/skills/` chứa ba Skill nghiệp vụ do người dùng cung cấp, không tự sửa để vượt qua checkpoint.
- Đã thử Skill 0 thực tế bằng Codex và xuất artifact cốt truyện dưới `tests/3.Thật tệ khi làm mẹ đơn thân/`; cơ chế thành công là CLI `--output-last-message`, chưa chứng minh model tự gọi tool ghi file. Bằng chứng và giới hạn tại `docs/reports/local-skill0-check.md`; chưa có luồng ba Skill hoặc Web chạy thật.
- `llm-level-2/` là nội dung giáo trình độc lập, không mặc nhiên thuộc ứng dụng Agent CF.
- `demo/` chứa tài sản/thử nghiệm, không mặc nhiên là mã production.
- `doc/` hiện được dành cho nội dung tài liệu/thử nghiệm hiện hữu; tài liệu chuẩn hiện tại nằm trong `docs/` ở root.
- Không di chuyển, xóa hoặc chỉnh sửa các nội dung độc lập trên nếu yêu cầu không nêu rõ.

Khi trạng thái trên thay đổi, cập nhật mục này và `README.md` trong cùng commit/PR.

Để tiếp tục trên máy khác, bắt đầu tại `docs/README.md` và `docs/development/implementation-plan.md`. Nhu cầu thực tế được ghi tại `docs/product/use-cases/youtube-video.md`; không suy ra rằng tool, đăng nhập Codex/Antigravity hoặc cấu hình trên PC cũ đã có trên máy mới. Đọc tài liệu kế hoạch không tự cấp phép triển khai ngoài task người dùng giao.

## 3. Thứ tự ưu tiên khi thực hiện task

1. Đọc yêu cầu của người dùng và các `AGENTS.md` áp dụng cho file sẽ sửa.
2. Kiểm tra code, test, cấu hình và tài liệu hiện có trước khi quyết định.
3. Xác định nguồn chuẩn của thông tin bị thay đổi.
4. Thực hiện thay đổi nhỏ nhất nhưng hoàn chỉnh.
5. Cập nhật mọi tài liệu và hợp đồng bị ảnh hưởng trong cùng thay đổi.
6. Chạy kiểm tra phù hợp và báo cáo trung thực kết quả.

Không tự mở rộng phạm vi sang tái cấu trúc, đổi công nghệ hoặc sửa nội dung không liên quan.

`docs/development/implementation-plan.md` giữ checklist hoàn thành từng menu, các mốc sử dụng, thứ tự triển khai và liên kết module. Theo dõi chi tiết tại `docs/development/tasks/<module>/`: README module chỉ mục các đầu việc, mỗi file Markdown là một đầu việc với task con có ID, phụ thuộc, nghiệm thu và bằng chứng. Khi được giao task, mở đúng file đầu việc, nguồn spec/ADR và phụ thuộc liên quan trước khi code; không cần đọc toàn bộ task của dự án. Khi hoàn tất, cập nhật trạng thái cùng file/test, lệnh thực sự đã chạy và giới hạn tại file đầu việc; cập nhật plan tổng khi menu/mốc đạt đủ phạm vi nghiệm thu hoặc tiến độ/ưu tiên bị ảnh hưởng. Hoàn thành một task không tự hoàn thành menu. Phân biệt thử nghiệm độc lập với tích hợp ứng dụng; không tick feature/menu chỉ vì prototype hoặc probe chạy được. Thêm tính năng/sửa lỗi vào đúng module/file liên quan với mã mới; đầu việc độc lập tạo file riêng và thêm vào README module. Không đổi/tái sử dụng mã cũ, dồn mọi task vào plan tổng hoặc chép lại spec vào file task. Quy ước chi tiết tại [hướng dẫn task](docs/development/tasks/README.md). Nếu việc chưa đủ rõ để tạo task có thể nghiệm thu, hỏi người dùng trước khi thực hiện phần liên quan.

## 4. Nguồn chuẩn duy nhất

Khi các file tương ứng được tạo, sử dụng bảng sau để tránh lặp và mâu thuẫn:

| Loại thông tin | Nguồn chuẩn |
|---|---|
| Mục tiêu và phạm vi sản phẩm | `docs/product/vision.md` |
| Thuật ngữ nghiệp vụ | `docs/product/glossary.md` |
| Yêu cầu và quy tắc nghiệp vụ | `docs/product/requirements.md` |
| Kiến trúc chính theo arc42 | `docs/architecture/overview.md` |
| Quan hệ và vòng đời domain | `docs/architecture/domain-model.md` |
| Quy tắc chạy process/task | `docs/architecture/execution-model.md` |
| Quyết định kiến trúc | `docs/architecture/decisions/` |
| HTTP API | `openapi/openapi.yaml` |
| Database thực tế | Schema và migration trong code |
| Cấu hình runtime | Config schema trong code và `.env.example` |
| Lệnh build/test/lint | Script của workspace/package |
| Thay đổi theo phiên bản | `CHANGELOG.md` hoặc changeset khi được áp dụng |

Không chép nguyên nội dung từ nguồn chuẩn sang file khác. Hãy tóm tắt ngắn và liên kết đến nguồn chuẩn.

Tổ chức `docs/` theo [bản đồ tài liệu](docs/README.md). Kiến trúc dùng một file chính `docs/architecture/overview.md` theo 12 mục arc42; domain/execution là phần chi tiết được liên kết, ADR giữ lý do và trạng thái quyết định. Requirements và glossary vẫn là nguồn chuẩn riêng, không chép lại để lấp các mục arc42. Kế hoạch/hướng dẫn dùng lại thuộc `docs/development/`; báo cáo kiểm chứng và snapshot theo thời điểm thuộc `docs/reports/`. Không tạo file rỗng hoặc danh sách tài liệu Planned chỉ để đủ template. Đổi cấu trúc tài liệu phải cập nhật liên kết, không thay phạm vi sản phẩm, lịch sử ADR hoặc trạng thái task đã có bằng chứng.

## 5. Quy tắc kiến trúc

Cho đến khi ADR và cấu trúc dự án chính thức được tạo:

- Không coi stack đề xuất trong `README.md` là stack đã được phê duyệt.
- Không thêm framework hoặc dependency lớn nếu không cần cho yêu cầu hiện tại.
- Mọi lựa chọn khó đảo ngược hoặc ảnh hưởng nhiều module phải có ADR.
- Tách domain/business logic khỏi UI, HTTP handler và code hạ tầng.
- Frontend không được tự định nghĩa lại quy tắc nghiệp vụ đã thuộc backend/domain.
- Worker/runner không được phụ thuộc vào chi tiết giao diện.
- Thiết kế process phải có version; một lần chạy phải tham chiếu đúng version đã khởi chạy.
- Giữ `Process` (định nghĩa) tách biệt với `ProcessRun` (lần chạy), và `Task` tách biệt với `TaskRun`.
- Permission phải được kiểm tra ở phía thực thi đáng tin cậy, không chỉ ẩn/hiện trên UI.
- Hành động có side effect cần tính đến retry, timeout, idempotency và audit log.

## 6. Quy ước code

Các formatter, linter và compiler config trong repository luôn là nguồn chuẩn về style. Khi chúng chưa tồn tại:

- Dùng tên tiếng Anh trong code, API và database; dùng tiếng Việt hoặc tiếng Anh nhất quán trong từng tài liệu.
- Ưu tiên tên theo domain: `project`, `process`, `task`, `agent`, `run`, `runner`, `tool`.
- Không dùng đồng thời các từ `workflow`, `pipeline` hoặc `job` để thay cho khái niệm trên nếu glossary chưa định nghĩa quan hệ.
- Tránh file/module đa trách nhiệm và abstraction chưa có nhu cầu thực tế.
- Đặt code và test theo [bảng tính năng và cấu trúc source](docs/development/project-structure.md#tra-cứu-menu-và-tính-năng). Giữ thay đổi trong module sở hữu nghiệp vụ khi có thể; sử dụng điểm truy cập công khai khi phối hợp module, không import nội bộ hoặc tạo phụ thuộc vòng. Thay đổi hợp đồng dùng chung phải cập nhật các nơi bị ảnh hưởng trong cùng thay đổi.
- Không hard-code secret, token, mật khẩu, endpoint riêng tư hoặc dữ liệu nhạy cảm.
- Không ghi secret hay toàn bộ payload nhạy cảm vào log.
- Validation phải nằm tại ranh giới nhận dữ liệu; lỗi phải có ngữ cảnh và không bị nuốt im lặng.
- Comment giải thích lý do hoặc ràng buộc, không kể lại điều code đã thể hiện rõ.

## 7. Quy tắc thay đổi tài liệu

Mỗi thay đổi phải kiểm tra ma trận tác động sau:

| Thay đổi | File cần kiểm tra/cập nhật |
|---|---|
| Thêm hoặc đổi tính năng | Requirements, tests, README/changelog nếu ảnh hưởng người dùng |
| Đổi thuật ngữ | Glossary và tất cả nơi sử dụng thuật ngữ |
| Đổi business rule | Requirements, domain model, tests |
| Đổi API | OpenAPI, client sinh tự động, integration tests |
| Đổi database | Migration/schema, data model, tests |
| Đổi kiến trúc | Architecture overview và ADR |
| Đổi vòng đời process/task | Execution model và tests |
| Đổi permission/security | Security docs, requirements và tests |
| Thêm biến môi trường | Config schema, `.env.example`, configuration docs |
| Đổi cách cài/chạy | README và development setup |
| Đổi cấu trúc repository | README, project structure và file này |

Nếu tài liệu đích chưa tồn tại, hãy tạo nó khi thay đổi thực sự cần một nguồn chuẩn; không tạo file rỗng chỉ để đủ cấu trúc.

## 8. ADR

Tạo ADR cho các quyết định như chọn framework chính, database, queue, ranh giới service, cơ chế version flow hoặc mô hình thực thi.

Không cần ADR cho chỉnh sửa cục bộ, thay đổi dễ đảo ngược hoặc quyết định đã được cấu hình/linter biểu đạt đầy đủ.

Định dạng tối thiểu:

```markdown
# NNNN - Tên quyết định

- Status: Proposed | Accepted | Superseded
- Date: YYYY-MM-DD

## Context

## Decision

## Consequences

## Alternatives considered
```

Không sửa lịch sử của ADR đã `Accepted` để làm như quyết định cũ chưa từng tồn tại. Tạo ADR mới và đánh dấu ADR cũ là `Superseded`.

## 9. Kiểm thử và xác minh

- Mọi thay đổi hành vi phải có test ở tầng thấp nhất đủ chứng minh hành vi đó.
- Sửa bug cần có regression test khi hạ tầng test cho phép.
- Không xóa hoặc làm yếu test chỉ để pipeline pass.
- Chạy các lệnh lint, type-check, test và build do package liên quan định nghĩa.
- Nếu repository chưa có lệnh kiểm tra, thực hiện kiểm tra khả dụng phù hợp và ghi rõ phần chưa thể xác minh.
- Không tuyên bố thành công nếu lệnh chưa chạy hoặc đã thất bại.

Với flow execution, tối thiểu cần xét các trường hợp: thành công, lỗi, retry, timeout, hủy, nhánh điều kiện, chạy song song và khôi phục sau gián đoạn khi các khả năng này được triển khai.

## 10. An toàn khi chỉnh sửa

- Giữ nguyên thay đổi có sẵn của người dùng và không ghi đè nội dung không thuộc task.
- Không chạy lệnh xóa/reset hàng loạt hoặc thao tác dữ liệu thật khi chưa được yêu cầu rõ ràng.
- Không commit file secret, `.env` thật, credential, database dump hoặc log chứa dữ liệu nhạy cảm.
- Không chỉnh trực tiếp file được sinh tự động; sửa nguồn rồi chạy generator.
- Migration đã phát hành không được sửa lại; tạo migration mới.
- Các thao tác agent/tool có side effect phải có cơ chế quyền, xác nhận hoặc audit phù hợp với mức rủi ro.

## 11. Definition of Done

Một task chỉ được coi là hoàn thành khi:

- Yêu cầu và tiêu chí nghiệm thu đã được đáp ứng.
- Code nằm đúng module, không tạo dependency trái kiến trúc.
- Test liên quan đã được thêm/cập nhật và chạy thành công, hoặc giới hạn được báo rõ.
- API, migration, cấu hình và generated artifacts đã đồng bộ nếu bị ảnh hưởng.
- Tài liệu trong ma trận tác động đã được kiểm tra và cập nhật.
- Không chứa secret, log debug thừa hoặc file tạm.
- Phần bàn giao nêu rõ file đã đổi, kiểm tra đã chạy và rủi ro/công việc còn lại.

## 12. Khi thông tin mâu thuẫn

Ưu tiên theo thứ tự:

1. Yêu cầu hiện tại, rõ ràng của người dùng.
2. `AGENTS.md` gần file được sửa nhất.
3. Hợp đồng máy có thể kiểm tra: schema, migration, OpenAPI, test và config.
4. ADR đang ở trạng thái `Accepted`.
5. Tài liệu kiến trúc/sản phẩm theo bảng nguồn chuẩn.
6. `README.md` và mô tả tổng quan.

Khi phát hiện mâu thuẫn, không âm thầm chọn một phiên bản. Hãy sửa nguồn lỗi trong phạm vi task hoặc báo rõ mâu thuẫn nếu cần quyết định từ chủ dự án.
