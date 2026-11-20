# Kế hoạch triển khai Agent CF

> Cập nhật: 2026-11-20 · Đã có ứng dụng Web/Server/Client chạy được, kiểm thử end-to-end Process động và nghiệm thu các menu cốt lõi.

[PC-004](tasks/runners/004-device-reconnect-metrics.md) sửa reconnect giữ PC, thêm device/proof Client 0.3.0, Kết nối/Hủy kết nối ở cột thao tác và CPU/RAM thật; migration 020–021, ADR 0010. Chưa coi đây là nghiệm thu toàn bộ menu PC/Agent API/runtime.

[RUN-010](tasks/runs/007-topic-directory-launch.md) bổ sung chạy Skill local bằng thư mục chủ đề đã có, root Project migration 019 và cùng topic qua các node; [BASE-008](tasks/base/007-input-scroll-responsiveness.md) giảm tải nền khi nhập/cuộn hộp thoại. Không đóng mapping tổng quát, vòng Agent API hoặc các mốc runtime chỉ từ fixture/topic UI.

[PROJ-007](tasks/projects/007-permanent-deletion.md) sửa Delete theo yêu cầu mới: xóa hẳn Project/Process gồm publication/lịch sử đã kết thúc, chặn Run chưa kết thúc; giữ file PC và catalog dùng chung. Skill/Agent chỉ bị chặn xóa khi còn Process sử dụng. Migration 018 và ADR 0008 giới hạn ngoại lệ DELETE, không mở quyền sửa lịch sử. Giữ nguyên trạng thái nghiệm thu menu/runtime tổng quát.

[PROJ-009](tasks/projects/009-derived-team.md) chuyển Team thành view PM + Agent được phân công trong version mới nhất đã lưu của mỗi Process. Bỏ quản lý Team thủ công, node chọn catalog Agent active trực tiếp; không thay mốc nghiệm thu runtime.

**Đã có:** thiết kế nền và khung Web/Server/Client + SQLite/migration 001–009 (BASE-002, DATA-001); trọn bộ cấu hình backend và catalog Settings, Skills/Tools, Agents (SET-001, SET-002, SKL-001, SKL-002, AGN-003); hệ thống ghép nối/heartbeat PC Runner, quản lý phiên và cây tiến trình/workspace/journal/tray (CLI-001, CLI-002, PC-001, CLI-003); các adapter runtime Codex (RTM-005), Antigravity (RTM-006 đã kiểm chứng transport, xử lý console buffer qua trích xuất SQLite trajectory, mapping model nghiêm ngặt từ chối fallback ngầm, thực thi Skill và resume phiên với CLI thật) và năng lực tìm kiếm Web cho Review (RTM-007); toàn bộ luồng điều phối ProcessRun/TaskRun/Attempt, API claim/settle/artifact an toàn và giao diện Web Form/List/Detail/Artifact Reader cho menu Runs (RUN-001 đến RUN-007); catalog Robots, version bất biến, gán PC tại node, worker thực thi và thống kê chất lượng theo version từ dữ liệu thực tế (ROB-001); trọn vẹn đặc tả tiêu chí duyệt chất lượng, vòng lặp Agent đánh giá/yêu cầu sửa có giới hạn (`max_revisions`), khử trùng quyết định, bảo toàn checkpoint artifact và luồng cố định Skill 0 → 1 → 2 có chặn hạ nguồn khi lỗi (AGN-001, AGN-002, RUN-007); cơ chế đối soát sau gián đoạn, từ chối kết quả muộn/hết hạn lease, ghi nhận observation hậu kỳ và cơ chế tạm dừng chờ người dùng, Continue an toàn (REL-001, REL-003); trọn vẹn cơ chế quản lý lịch chạy Schedule, chính sách lựa chọn PC, phiên bản ghim bất biến, cùng màn hình Tổng quan Overview từ dữ liệu thật, khối cảnh báo lỗi đỏ chưa xử lý, tiến độ dự án/mục tiêu và xếp hạng token Agent thực tế (PROC-004, OVW-001); cơ chế sao lưu snapshot online SQLite nhất quán, kiểm tra tính toàn vẹn và phục hồi dữ liệu/artifact kèm đối soát sau sự cố (DATA-002), hệ thống audit bất biến append-only, khử trùng tự động dữ liệu nhạy cảm và ma trận kiểm thử quyền xuyên hệ thống (REL-002); cùng bộ kiểm thử toàn diện End-to-End cho Process động đa tác vụ (Agent → Robot → Review Agent), bổ sung Skill động qua cấu hình/API, lỗi lan truyền và skipping hạ nguồn, timeout robot và context lỗi, khôi phục lease và can thiệp chờ người dùng. Kiểm thử tự động đạt 170 passed, 1 skipped (Python) và 19 passed (Web), hợp đồng OpenAPI đạt 74 schemas / 53 paths / 64 operations. Các menu "Overview", "Runs", và "Robots" cùng toàn bộ 4 mốc sử dụng đã hoàn thành nghiệm thu. **BASE-003 còn vướng:** SDK/worker/probe đã có, chờ bổ sung binary CLI hợp lệ để kiểm chứng Service/restart. Hướng dẫn cài đặt/chạy trên máy mới tại [setup](setup.md) và vận hành tại [docs/operations/backup-restore.md](../operations/backup-restore.md).

**UI bổ sung 2026-11-17:** đã có [layout tám menu/mobile](tasks/base/003-web-navigation.md), [Projects](tasks/projects/001-project-management.md), [Team/Targets](tasks/projects/002-team-targets.md), [editor kéo thả](tasks/projects/processes/002-process-editor.md), [Agents](tasks/agents/003-agent-web.md), [Skills/Tools](tasks/skills/002-skills-web.md), [PC](tasks/runners/002-runner-web.md), [Settings](tasks/settings/003-settings-web.md) và [form Run/phân trang tổng quát](tasks/runs/006-generic-web-form.md), kết nối API local thật theo prototype. [Báo cáo UI](../reports/ui-completion-check.md) phân biệt bằng chứng trình duyệt với thực thi runtime.

**Làm tiếp:** [BASE-003](tasks/base/002-application-bootstrap.md#base-003) kiểm chứng Temporal Service/restart; hoàn tất hợp đồng publish [PROC-003](tasks/projects/processes/002-process-editor.md#proc-003); telemetry và nghiệm thu Client thật của [PC-002](tasks/runners/002-runner-web.md#pc-002). Review khi nối UI phát hiện [RTM-008](tasks/runtime/005-generic-snapshot-execution.md) (worker còn suy hành vi từ fixture), [RUN-008](tasks/runs/005-runtime-input-mapping.md) (mapping runtime) và [SET-004](tasks/settings/004-provider-secret-store.md) (secret store). Các task/menu đó không được tích hoàn thành chỉ nhờ có màn hình, HTTP hoặc test fixture.

## Tiến độ từng menu

[CLI-004](tasks/client/004-desktop-onboarding.md) có bộ cài và app CF Client chung, guided Connect PC, URL protocol, native tray, DPAPI và startup tùy chọn. Client gọn không cấu hình Server/tên PC; Web chỉ báo connected sau heartbeat. Không đóng toàn bộ menu PC hoặc runtime/API điều phối từ nghiệm thu onboarding này.

[SET-005](tasks/settings/005-ai-tool-models.md) và ADR 0007 tách Agent điều phối/API model khỏi model của Codex/Antigravity. Settings cho quản lý vài model CLI thường dùng; node chọn model đúng công cụ, không fallback API. Không tích hoàn thành vòng Agent API từ thay đổi catalog; review hiện có là tiêu chí xác định, RTM-008 giữ mở.

[SKL-004](tasks/skills/003-project-scope.md) bổ sung phạm vi nhiều Project/Global cho Skill, bảng/lọc và giới hạn lựa chọn trong Process; backend kiểm publish/Run mới. Không thay trạng thái nghiệm thu toàn bộ runtime hoặc các menu từ thay đổi catalog này.

Xác nhận phạm vi 2026-11-18: Web thay người điều khiển PC, giữ quy trình Skill và output gốc tại PC. [RTM-009](tasks/runtime/006-local-skill-pc-output.md) đã kiểm chứng demo Codex đọc file Skill bằng đường dẫn tuyệt đối, dùng tool tạo output thật trong `tests` và báo đường dẫn trên Web, không yêu cầu upload. Đây là phạm vi local-file/Codex; không đóng các backlog runtime/mapping/Temporal nêu trên hoặc nâng trạng thái toàn bộ menu từ một demo.

Chỉ tích `[x]` khi toàn bộ phạm vi menu theo [requirements](../product/requirements.md#yêu-cầu-theo-màn-hình) chạy với dữ liệu thật, các task liên quan đạt nghiệm thu và có bằng chứng trong file task. Prototype hoặc chạy riêng Skill 0 chưa đủ để tích hoàn thành menu.

- [x] **[Overview](tasks/overview/README.md)** — Lỗi, tiến độ Project/Target và token có nguồn dữ liệu thật; thiếu dữ liệu hiển thị rõ.
- [ ] **[Projects](tasks/projects/README.md)** — Quản lý Project, Team/Targets; [Processes](tasks/projects/processes/README.md) có editor, version, lịch chạy; tab Runs dùng lại lịch sử thật.
- [x] **[Runs](tasks/runs/README.md)** — Chạy, lịch sử, lọc, Logs, output, lỗi, timeout và Cancel; giữ dữ liệu sau khi mở lại Web.
- [ ] **[Agent điều phối](tasks/agents/README.md)** — Agent API giao việc/kiểm tra, Role/model API/Skill/Tool; vòng LLM API điều phối tổng quát chưa triển khai, xem RTM-008; số liệu có nguồn hoặc ghi rõ chưa có.
- [ ] **[Skills](tasks/skills/README.md)** — Danh mục Skill/Tools, version/snapshot, quyền và vòng đời archive/restore.
- [x] **[Robots](tasks/robots/README.md)** — Catalog/version, node thực thi và thống kê theo version từ kết quả thật.
- [ ] **[PC](tasks/runners/README.md)** — Ghép nối, heartbeat, trạng thái/tải, công việc đang chạy và quản lý quyền nhận việc.
- [ ] **[Settings](tasks/settings/README.md)** — Providers & Models API, Công cụ AI trên PC, Roles, General; cấu hình, kiểm tra kết nối và bảo vệ secret phía Server.

## Mốc sử dụng

- [x] **[Chạy Skill 0 qua Web](tasks/runs/003-skill0-web.md#run-006)** — Nhập chủ đề, chạy Codex/Antigravity, lưu và xem lại cốt truyện/log/lịch sử.
- [x] **[Skill 0 → 1 → 2 có Agent duyệt](tasks/runs/004-skill-chain.md#run-007)** — Truyền đúng kết quả, duyệt từng Part và giữ bản trước/sau review.
- [x] **[Khôi phục sau gián đoạn](tasks/execution/002-recovery.md#rel-001)** — Đối soát tiến trình/kết quả, không chạy trùng.
- [x] **[Chờ người dùng và Continue](tasks/execution/004-human-continue.md#rel-003)** — Tiếp tục đúng bước, giữ phần đã đạt.

## Thứ tự đến mốc dùng được đầu tiên

1. [Thiết kế nền](tasks/base/001-foundation-design.md#base-001) → [Process](tasks/projects/processes/001-process-definition.md) → [quyền nhận việc](tasks/execution/001-execution-permissions.md) → [lần chạy](tasks/runs/001-skill0-run-design.md) → [hợp đồng API](tasks/api/001-run-client-contract.md).
2. [Khung Web/Server/Client và Temporal](tasks/base/002-application-bootstrap.md) + [SQLite](tasks/data/001-sqlite-persistence.md).
3. [Kết nối Client](tasks/client/001-authenticated-connection.md), [quản lý tiến trình](tasks/client/002-process-execution.md), [adapter Codex](tasks/runtime/002-codex-adapter.md), [model](tasks/settings/001-runtime-models.md) và [Skill](tasks/skills/001-skill-catalog.md) → [điều phối/lịch sử](tasks/runs/002-run-execution-history.md).
4. [Form, kết quả và nghiệm thu Skill 0 qua Web](tasks/runs/003-skill0-web.md).
5. [Agent duyệt](tasks/agents/001-agent-review.md) + [search cho review](tasks/runtime/004-review-search.md) → [chuỗi ba Skill](tasks/runs/004-skill-chain.md).

Phụ thuộc chi tiết nằm trong từng task; khôi phục và Continue theo các đầu việc riêng ở trên.

## Nền tảng dùng chung

Đầu việc kỹ thuật: [BASE](tasks/base/README.md) · [DATA](tasks/data/README.md) · [API](tasks/api/README.md) · [Client](tasks/client/README.md) · [Runtime](tasks/runtime/README.md) · [Quyền, audit, recovery](tasks/execution/README.md).

Cách thêm task, ghi nghiệm thu và bàn giao: [hướng dẫn task](tasks/README.md). Phạm vi mở rộng: [use case YouTube](../product/use-cases/youtube-video.md).

- BASE-009 — Lưu và dùng ngay ngoài phiên bản Robot: [phạm vi/kiểm chứng](tasks/base/008-save-and-run.md). Không đóng RTM-008/RUN-008/BASE-003.
- BASE-011 — Thông báo chặn xóa trên Web dùng tên dữ liệu/ngữ cảnh và hướng xử lý; giữ chính sách xóa: [phạm vi/kiểm chứng](tasks/base/010-deletion-feedback.md). Không thay trạng thái nghiệm thu menu/runtime.

- PROC-006: [Bỏ thư mục ở node, kế thừa Project](tasks/projects/processes/005-project-working-directory.md); giữ Skill/output trên PC và snapshot lịch sử.
