# Agent CF

Khi không xóa được, Web nêu tên dữ liệu đang liên kết và cách xử lý, thay thông báo ID kỹ thuật; Project/Process/PC chỉ rõ lượt chạy hoặc PC đang chặn. Điều kiện bảo vệ xóa giữ nguyên. Xem [BASE-011](docs/development/tasks/base/010-deletion-feedback.md).

Logo ở đầu sidebar dùng mẫu SVG chữ C mở ôm chữ F, có ô vuông tím và chữ Agent CF. Icon menu có nét đồng nhất, hỗ trợ focus bàn phím, mobile và giảm chuyển động. Xem [BASE-010](docs/development/tasks/base/009-sidebar-identity.md).

Client 0.3.2 gửi lời gọi Skill trực tiếp theo mẫu hai dòng; ô Yêu cầu riêng nối lưu ý của bạn phía sau, không tự thêm quy trình ngoài Skill. Xem [RTM-011](docs/development/tasks/runtime/008-direct-skill-invocation.md).

Migration 023 giữ thư mục làm việc đã lưu của Project cũ khi bỏ ô thư mục node; tự chuyển cấu hình thống nhất sang Project, không yêu cầu nhập lại. Xem [PROC-007](docs/development/tasks/projects/processes/006-legacy-project-root.md).

Thư mục làm việc của bước AI lấy từ Project; node không cần nhập thư mục. Chạy Process chọn chủ đề, Skill giữ quy trình và quyết định output trên PC. Xem [PROC-006](docs/development/tasks/projects/processes/005-project-working-directory.md).

Client 0.3.1 bổ sung chạy Skill local bằng Antigravity; output giữ trên PC, kiểm tra file thật/model/timeout. Phạm vi và giới hạn Gemini trên CLI đang cài: [RTM-010](docs/development/tasks/runtime/007-antigravity-local-skill.md).

Agent CF là hệ thống quản lý và vận hành các AI agent theo mô hình một công ty: Project chứa các Process, Process gồm các Task và mỗi Task có một Agent chịu trách nhiệm output.

Mục tiêu là giúp người vận hành theo dõi tiến độ dự án, giao trách nhiệm cho Agent, thiết kế Process trực quan, kiểm tra Runs/Logs và theo dõi token sử dụng.

> **Trạng thái:** Đã hoàn thành thiết kế nền, khung Web/Server/Client (BASE-002), SQLite migration 001–009, catalog Settings, Skills/Tools, Agents (SET-001/002, SKL-001/002, AGN-003), hệ thống ghép nối/heartbeat/tiến trình Runner (CLI-001/002/003, PC-001), các adapter runtime Codex (RTM-005), Antigravity (RTM-006 đã kiểm chứng transport, xử lý console buffer qua trích xuất SQLite trajectory, mapping model nghiêm ngặt từ chối fallback ngầm, thực thi Skill và resume phiên với CLI thật) cùng năng lực review search (RTM-007), toàn bộ hệ thống điều phối ProcessRun/TaskRun/Attempt, claim việc CAS, worker Client, API lịch sử/artifact an toàn và giao diện Web Runs (RUN-001 đến RUN-007), catalog Robots, version bất biến, node thực thi ghim PC, worker thực thi và thống kê theo version từ dữ liệu thực tế (ROB-001), toàn bộ đặc tả tiêu chí duyệt chất lượng, vòng lặp Agent đánh giá/yêu cầu sửa có giới hạn (`max_revisions`), khử trùng quyết định, bảo toàn checkpoint artifact và luồng cố định Skill 0 → 1 → 2 có chặn hạ nguồn khi lỗi (AGN-001, AGN-002, RUN-007), cơ chế đối soát sau gián đoạn (reconciliation), từ chối kết quả muộn/hết hạn lease, ghi nhận bằng chứng hậu kỳ (observation), cơ chế tạm dừng chờ người dùng và Continue an toàn (REL-001, REL-003), cùng toàn bộ hệ thống quản lý lịch chạy Schedule, chính sách lựa chọn PC, phiên bản ghim bất biến và màn hình Tổng quan Overview từ dữ liệu thật, khối cảnh báo lỗi đỏ chưa xử lý, tiến độ dự án/mục tiêu và xếp hạng token Agent thực tế (PROC-004, OVW-001), cùng bộ kiểm thử toàn diện E2E Process động (Agent → Robot → Review Agent, cấu hình Skill động, failure cascade, robot timeout, recovery, human continue) với 170 test tự động passed, 1 skipped (Python) và 19 passed (Web), hợp đồng OpenAPI đạt 74 schemas / 53 paths / 64 operations. Các mốc "Chạy Skill 0 qua Web", "Skill 0 → 1 → 2 có Agent duyệt", "Khôi phục sau gián đoạn", "Chờ người dùng và Continue" cùng các menu "Overview", "Runs" và "Robots" đã hoàn thành nghiệm thu. BASE-003 đã có SDK/worker/probe/launcher, đang chờ kiểm chứng Service/restart khi có binary Temporal CLI trên máy. Prototype và các thử nghiệm độc lập chưa phải mã production.

Bản [HTML prototype](demo/agent-cf-prototype/README.md) là mẫu UI/UX đã review. Ứng dụng thật tại `apps/web` đã có sidebar tím và tám menu, thêm Projects/Team/Targets, editor Process, Agents, Skills/Tools, PC, Settings nối API local; xem [kiểm chứng và giới hạn UI](docs/reports/ui-completion-check.md). UI có mặt không đồng nghĩa toàn bộ menu đạt nghiệm thu nghiệp vụ: còn kiểm chứng Temporal, thực thi Skill snapshot/mapping tổng quát và secret store provider.

**Tiếp tục trên máy khác:** bắt đầu tại [docs/README.md](docs/README.md), sau đó đọc [kế hoạch và trạng thái bàn giao](docs/development/implementation-plan.md). [Use case YouTube](docs/product/use-cases/youtube-video.md) ghi lại quy trình thật người dùng đang làm; hệ thống hướng tới Agent điều khiển tool có sẵn, xử lý lỗi trong phạm vi cho phép và báo người dùng khi cần.

## Phạm vi sản phẩm

**Kết nối PC:** Web → PC → Connect PC → nhập thông tin → Mở CF Client. Nếu chưa cài, tải **CF Client Setup.exe**, cài rồi bấm mở lại; Client chỉ xác nhận kết nối, không có form Server/tên PC. Web báo thành công khi Client gửi heartbeat thật. App gọn nằm ở khay hệ thống, có startup Windows tùy chọn; Task Manager → Details có **CF Client.exe**. `run-client.bat` mở Client chung, `run-skill0-test.bat` vẫn là demo riêng. [CLI-004](docs/development/tasks/client/004-desktop-onboarding.md).

Chỉ **Project** có Ngừng hoạt động/Kích hoạt lại. Skills, Tools, Agents, Robots, Roles và Process không có nút/bộ lọc Archive/Restore; mục chưa cần dùng được để nguyên. [Phạm vi BASE-007](docs/development/tasks/base/006-project-only-lifecycle-controls.md).

Giao diện ưu tiên tên và số phiên bản; ID nội bộ/hash nằm trong **Chi tiết kỹ thuật** mặc định đóng, có sao chép khi cần tra lỗi. Mã ghép nối, đường dẫn file và Model ID dùng để cấu hình runtime vẫn hiện ở nơi cần thao tác. [Phạm vi kiểm tra BASE-006](docs/development/tasks/base/005-visible-identifiers.md).

Skills có phạm vi **Global** hoặc nhiều **Project** được tích chọn khi tạo/sửa; bảng có cột và bộ lọc Project. Process chỉ chọn Skill của Project hiện tại và Global; Server kiểm tra lại khi publish/chạy mới. Skill cũ giữ Global sau nâng cấp. [Chi tiết SKL-004](docs/development/tasks/skills/003-project-scope.md).

Form Thêm/Sửa Skill cho nhập đường dẫn hoặc **Chọn file .md chính** trên PC đã chọn qua Client. Chỉ lưu đường dẫn và PC, không upload nội dung/ref; CLI đọc file gốc khi chạy. Đổi file giữ version published, tạo/sửa draft để publish riêng. [SKL-005](docs/development/tasks/skills/004-main-markdown-file.md).

Menu gồm **Overview, Projects, Runs, Agent điều phối, Skills, Robots, PC, Settings**. Process và sơ đồ node nằm trong Project; Team và Targets cũng thuộc từng Project. Role quản lý tại Settings, Tool nội bộ quản lý trong Skills. Agent là nhân sự có thể làm nhiều việc, Skill là một việc; trong Process chọn Agent nào và Skill nào thì Agent đó làm việc đó, không bắt gán cứng Skill ở catalog. Bỏ chọn Skill trong form Agent; cột Skills ở bảng Agent điều phối hiển thị các Skill đang được phụ trách trong các Process. [AGN-005](docs/development/tasks/agents/004-derived-agent-skills.md).

Form node có **Agent điều phối**, **Công cụ AI thực thi** (Codex CLI/Antigravity), **Model thực thi**, **Nhiệm vụ**, Quản lý Team và PC theo Skill published. Task key tự sinh; mapping/schema/timeout nằm trong Cấu hình nâng cao. Settings tách **Providers & Models API** của Agent và **Công cụ AI trên PC** để thêm/sửa/bật vài model CLI thường dùng; model CLI không lấy từ Agent hay provider API. [SET-005](docs/development/tasks/settings/005-ai-tool-models.md), [ADR 0007](docs/architecture/decisions/0007-orchestration-agents-and-ai-tools.md).

Vai trò đích của Agent điều phối là dùng API để giao việc và kiểm tra tiến độ/lỗi/chất lượng thay người. Việc đổi tên/tách catalog chưa triển khai vòng LLM API điều phối tổng quát; review hiện có dùng bộ tiêu chí xác định. Giới hạn tại [RTM-008](docs/development/tasks/runtime/005-generic-snapshot-execution.md).

Projects có cột Mô tả riêng, trạng thái **Đang hoạt động / Không hoạt động** xanh/đỏ, bộ lọc thêm **Tất cả** và menu ⋯ cho chỉnh sửa, nhân bản, bật/tắt sử dụng và xóa có xác nhận. **Xóa** xóa vĩnh viễn cả version published và lịch sử thuộc Project, giữ catalog dùng chung/file trên PC; chỉ chặn khi còn Run chưa kết thúc, cần dừng và chờ trước khi xóa. Skill/Agent chỉ chặn xóa khi còn Process sử dụng; chi tiết [PROJ-007](docs/development/tasks/projects/007-permanent-deletion.md). Nhân bản chép toàn bộ cấu hình/Team/Process/version/Targets (giữ số liệu), luôn tắt lịch ở bản sao và không chép lịch sử chạy; chi tiết tại [PROJ-003](docs/development/tasks/projects/003-project-table-actions.md).

Kết quả thao tác trong Projects hiện ở góc phải trong 6 giây: thành công hoặc lỗi, không âm thầm chuyển Xóa thành Không hoạt động; xem [PROJ-006](docs/development/tasks/projects/006-action-feedback.md) và quy tắc mới tại PROJ-007.

Trong chi tiết Project, **← Projects** nằm bên trái cùng dòng mô tả/PM dưới tiêu đề, không thêm hàng điều hướng; xem [PROJ-008](docs/development/tasks/projects/008-back-navigation.md).

**Team** chỉ hiển thị PM và Agent đã phân công trong node của các Process, tự tổng hợp và bỏ trùng. Chọn Agent trực tiếp khi tạo node, không cần Manage team; xem [PROJ-009](docs/development/tasks/projects/009-derived-team.md).

Bảng **Skills → Version** hiển thị bản Published mới nhất và draft đang có; Skill chưa Publish được ghi rõ để biết vì sao chưa chọn được trong node. Xem [SKL-006](docs/development/tasks/skills/005-version-column.md).

**PC:** Client 0.3.0 nhận diện máy ổn định, kết nối lại giữ PC đang dùng. Cột Thao tác có **Kết nối/Hủy kết nối**, Sửa và Xóa riêng; CPU/RAM lấy từ Windows, có dung lượng RAM dùng/tổng. Xem [PC-004](docs/development/tasks/runners/004-device-reconnect-metrics.md).

**Chạy theo chủ đề:** cấu hình thư mục Project một lần, lưu/publish các node Skill, rồi bấm Chạy và chọn hoặc dán thư mục chủ đề đã có. Mọi bước dùng chung chủ đề, giữ cwd Project và output trên PC; Nhiệm vụ bổ sung có thể để trống. Xem [RUN-010](docs/development/tasks/runs/007-topic-directory-launch.md). Web giảm tải nền khi nhập/cuộn hộp thoại theo [BASE-008](docs/development/tasks/base/007-input-scroll-responsiveness.md).

Hành vi và tiêu chí theo từng màn được quản lý tại [Yêu cầu sản phẩm và giao diện](docs/product/requirements.md#yêu-cầu-theo-màn-hình). Đây là định hướng tạm đã review để triển khai tiếp; prototype chưa có backend, engine PM, thống kê token thật hoặc cơ chế phân quyền thực thi.

## Mô hình nghiệp vụ cốt lõi

```text
Company (một công ty)
├── Project
│   ├── PM, Team và Targets
│   └── Process → ProcessVersion → Task (node) → Agent chịu trách nhiệm
│                              └── ProcessRun → TaskRun
├── Agents → Role, Model và Skills
├── Skills → Tools nội bộ
├── Robots → RobotVersion
├── PC (Runner Client trên máy thực thi)
└── Settings
```

- **Project** đại diện cho một mục tiêu hoặc phạm vi công việc lớn.
- **Process** là một quy trình có thể thiết kế dưới dạng flow.
- **Task** là một bước trong ProcessVersion, thể hiện bằng node Agent hoặc Robot; mỗi node có Agent chịu trách nhiệm output.
- **Agent** là thực thể chịu trách nhiệm thực hiện task.
- **Run** là một lần thực thi process; mỗi task trong run có trạng thái và lịch sử riêng.
- **Runner** là danh tính thực thi kỹ thuật; giao diện quản lý máy dùng tên **PC**.

Tên gọi chính thức và định nghĩa chi tiết được quản lý trong [glossary](docs/product/glossary.md).

## Định hướng kỹ thuật

Kiến trúc gồm Web quản lý, Server điều phối và CF Client trên PC gọi Agent/tool. [Tài liệu kiến trúc chính](docs/architecture/overview.md) tổ chức theo arc42, dẫn tới các phần chi tiết và quyết định. [Bản đồ docs](docs/README.md) chỉ rõ nơi đọc yêu cầu, tiến độ, hướng dẫn và báo cáo kiểm chứng.

Đề xuất công nghệ được quản lý tại [ADR stack](docs/architecture/decisions/0001-application-stack.md), [ADR CF Client Windows](docs/architecture/decisions/0002-cf-client-windows.md) và [ADR Temporal](docs/architecture/decisions/0003-process-engine-temporal.md). ADR 0001–0003 đã `Accepted` về thiết kế nền local, chưa triển khai. [ADR 0005](docs/architecture/decisions/0005-versioned-process-execution.md) chốt Process động, snapshot và quyền thực thi; Skill 0–1–2 chỉ là bộ test. Đã có [OpenAPI](openapi/openapi.yaml) và [contract Client](docs/architecture/client-protocol.md); [review thiết kế](docs/reports/foundation-design-review.md) ghi bằng chứng và giới hạn. Human/Continue vẫn cần thiết kế chi tiết ở mốc riêng; chưa thêm Celery/Redis hoặc LangGraph cho cùng nhiệm vụ. Thứ tự và điều kiện kiểm chứng nằm tại [kế hoạch triển khai](docs/development/implementation-plan.md).

**Database nghiệp vụ giai đoạn local đã chốt SQLite** theo [ADR 0004 — Accepted](docs/architecture/decisions/0004-sqlite-business-database.md); đã có schema/migration 001–009, persistence test dưới `apps/server/migrations`, cơ chế sao lưu snapshot online nhất quán và đối soát sau phục hồi (DATA-002), hệ thống audit append-only bất biến và kiểm thử quyền (REL-002) với hướng dẫn vận hành tại [docs/operations/backup-restore.md](docs/operations/backup-restore.md). ADR này ghi rõ ranh giới truy cập qua Server, hướng chuyển PostgreSQL và tách riêng persistence của Temporal.

## Cấu trúc repository dự kiến

Định hướng monorepo gồm `apps/web`, `apps/server` và `apps/client`, mỗi ứng dụng có cấu hình và test riêng. Cây thư mục chi tiết và quy tắc phụ thuộc được quản lý tại [cấu trúc source code](docs/development/project-structure.md).

Web chia theo tính năng/menu; Server chia module nghiệp vụ trong từng lớp. Khi sửa một tính năng, tra [bảng menu và vị trí code](docs/development/project-structure.md#tra-cứu-menu-và-tính-năng) và tuân thủ ranh giới module để hạn chế ảnh hưởng sang phần khác.

Chỉ tạo thư mục khi có nội dung; chưa scaffold ứng dụng hoặc tạo sẵn `services/`, `packages/`. Prototype và các nội dung độc lập hiện hữu giữ nguyên.

## Bắt đầu phát triển

**Mở Web local trên Windows:** sau khi cài dependency, double-click [run.bat](run.bat). Launcher khởi động Server/Web, đợi kết nối sẵn sàng rồi mở `http://127.0.0.1:5173`. Giữ cửa sổ launcher khi sử dụng; nhấn Enter trong cửa sổ đó để dừng cả hai. [Chi tiết](docs/development/setup.md#chạy-nhanh-trên-windows).

**Project test Skill 0:** [run-skill0-test.bat](run-skill0-test.bat) mở PC test riêng sau khi Server/Web đã chạy. Bản demo hiện hành dùng file `SKILL.md` theo đường dẫn tuyệt đối và PC đã chọn; node cấu hình thư mục làm việc, Codex dùng tool tạo/sửa output thật trên PC, Web hiển thị đường dẫn. Xem [cách chạy](docs/development/setup.md#project-test-skill-0-bằng-codex-cli), [RTM-009](docs/development/tasks/runtime/006-local-skill-pc-output.md) và [yêu cầu giữ quy trình/output PC](docs/product/requirements.md#giữ-quy-trình-và-output-trên-pc). Lịch sử demo upload cũ ở [PROJ-004](docs/development/tasks/projects/004-skill0-test-project.md). Runner này không thay thế daemon production hoặc đóng backlog runtime tổng quát.

Đã có manifest dependency và [hướng dẫn cài môi trường](docs/development/setup.md) cho Python 3.14, Node.js 24 và npm 11. Dùng `.venv` trong project; tận dụng cache của máy khi cài.

Đã có entrypoint, cấu hình và lệnh chạy Server/Web/Client theo [hướng dẫn chạy](docs/development/setup.md), gồm UI nghiệp vụ kết nối API và điều phối Run. Migration tự áp dụng khi khởi động Server; kiểm thử UI dùng DB tạm riêng, không seed dữ liệu demo vào DB đang sử dụng.

## Nguyên tắc tài liệu

- Một thông tin chỉ có một nguồn chuẩn; tài liệu khác liên kết tới nguồn đó thay vì sao chép.
- Code và tài liệu liên quan phải được cập nhật trong cùng một thay đổi.
- API được mô tả bằng OpenAPI; database thực tế được xác định bởi schema/migration trong code.
- Quyết định kiến trúc quan trọng phải có ADR.
- Tài liệu phải phân biệt rõ trạng thái hiện tại, đề xuất và kế hoạch tương lai.

Quy tắc chi tiết cho người và coding agent được quy định tại [AGENTS.md](AGENTS.md).

Mục lục và hướng dẫn đọc tài liệu nằm tại [docs/README.md](docs/README.md).

## Lộ trình gần nhất

Theo dõi tại [tiến độ và kế hoạch](docs/development/implementation-plan.md): tính năng đã có gì, còn thiếu gì và thứ tự triển khai. Chi tiết nằm trong [thư mục task theo module](docs/development/tasks/README.md), mỗi đầu việc một file chứa task con, phụ thuộc, nghiệm thu và bằng chứng. Thêm tính năng hoặc sửa bug tại đúng module; không dồn checklist vào kế hoạch tổng. Mã task giữ cố định khi chuyển file. Báo cáo thử nghiệm riêng không đồng nghĩa menu/luồng ứng dụng đã hoàn thành.

## License

Chưa xác định. Phải bổ sung file license trước khi phân phối công khai hoặc nhận đóng góp bên ngoài.


Menu PC giữ Connect PC phía trên; mỗi dòng có Sửa tên/Xóa kết nối. Xóa giữ file và lịch sử, thu hồi kết nối, tắt lịch liên quan và chặn khi còn run liên quan chưa kết thúc. [PC-003](docs/development/tasks/runners/003-edit-remove.md).

BASE-009: Web dùng Skill đã lưu và Process Lưu/Chạy, không yêu cầu Draft/Version/Publish. Robot giữ phiên bản và Lưu dùng ngay. Migration 022, snapshot Run bất biến, lịch theo cấu hình hiện tại; API cũ giữ tương thích. Xem [task](docs/development/tasks/base/008-save-and-run.md) và [ADR 0011](docs/architecture/decisions/0011-save-and-run-current-configuration.md).
