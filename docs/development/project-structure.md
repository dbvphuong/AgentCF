# Cấu trúc source code Agent CF

> Status: Draft  
> Last updated: 2026-11-17  
> Owner: Engineering

## Phạm vi

Cấu trúc theo [kế hoạch](implementation-plan.md) đã có ứng dụng Web/Server/Client, SQLite migration và các module thực thi. Web có tám menu, Projects/Team/Targets và editor Process kết nối API local theo [báo cáo UI](../reports/ui-completion-check.md). Cây bên dưới là bản đồ tổ chức, không khẳng định mọi lớp/thư mục đã tồn tại hoặc toàn bộ sản phẩm đạt production. Chỉ tạo thư mục khi có nội dung thực tế; giữ nguyên các nội dung độc lập và prototype hiện có.

Công nghệ được quản lý tại [ADR stack](../architecture/decisions/0001-application-stack.md), cách chạy Client tại [ADR CF Client](../architecture/decisions/0002-cf-client-windows.md). ADR 0001–0003 đã Accepted về thiết kế nền local ngày 2026-11-16; phạm vi triển khai và giới hạn kiểm chứng ở từng task. Snapshot/outbox/quyền theo [ADR 0005](../architecture/decisions/0005-versioned-process-execution.md).

## Cơ sở tổ chức

- **Monorepo:** Web, Server và CF Client ở cùng repository để đồng bộ hợp đồng và tài liệu; mỗi ứng dụng có cấu hình, dependency và test riêng.
- **Server phân lớp theo Clean Architecture, chia theo nghiệp vụ trong từng lớp:** nghiệp vụ độc lập với HTTP, database và kết nối máy thực thi; code cùng tính năng có tên module nhất quán giữa các lớp.
- **Web theo tính năng:** các phần của Projects, Runs, Agents… được đặt gần nhau trong `features/`.
- **Python dùng src layout:** package ứng dụng nằm dưới `src/`, test nằm ngoài package.

Đây là cách áp dụng cho Agent CF dựa trên [hướng dẫn kiến trúc của Microsoft](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures), [FastAPI về chia module](https://fastapi.tiangolo.com/tutorial/bigger-applications/) và [Python Packaging về src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/). Không có một template của hãng quy định nguyên cây thư mục cho bộ React/Python/Windows Client này.

## Cây thư mục dự kiến

```text
AgentCF/
├── apps/
│   ├── web/
│   │   ├── src/
│   │   │   ├── app/             # Khởi tạo, router, layout
│   │   │   ├── features/        # Projects, Runs, Agents...
│   │   │   │   ├── overview/
│   │   │   │   ├── projects/
│   │   │   │   │   ├── team/
│   │   │   │   │   ├── targets/
│   │   │   │   │   └── processes/ # Editor Lưu/Chạy, lịch chạy
│   │   │   │   ├── runs/        # Chi tiết Run, TaskRun, Logs
│   │   │   │   ├── agents/
│   │   │   │   ├── skills/
│   │   │   │   │   └── tools/
│   │   │   │   ├── robots/
│   │   │   │   ├── runners/     # Menu PC; tên kỹ thuật theo glossary
│   │   │   │   └── settings/
│   │   │   │       ├── providers/
│   │   │   │       ├── models/
│   │   │   │       ├── roles/
│   │   │   │       └── general/
│   │   │   └── shared/          # UI và tiện ích dùng chung
│   │   ├── tests/
│   │   └── package.json
│   │
│   ├── server/
│   │   ├── src/agent_cf_server/
│   │   │   ├── domain/          # Thực thể và quy tắc nghiệp vụ
│   │   │   ├── application/     # Tạo run, hủy, duyệt, điều phối
│   │   │   ├── infrastructure/  # Database, kết nối PC, lưu file
│   │   │   ├── api/             # HTTP và WebSocket
│   │   │   └── bootstrap/       # Khởi tạo API, worker, scheduler
│   │   ├── tests/
│   │   ├── migrations/
│   │   └── pyproject.toml
│   │
│   └── client/
│       ├── src/agent_cf_client/
│       │   ├── connection/     # Ghép nối, heartbeat, reconnect, metadata chọn file Skill trên PC
│       │   ├── execution/      # Chạy tiến trình, hủy, thu output
│       │   ├── adapters/       # Codex, agy và tool hiện có
│       │   └── desktop/        # Tray, tích hợp Windows
│       ├── tests/
│       └── pyproject.toml
│
├── openapi/                     # Hợp đồng HTTP API
├── infra/                       # Cấu hình triển khai
├── docs/                        # Tài liệu chuẩn
├── demo/                        # Prototype và thử nghiệm hiện có
├── README.md
├── run.bat                      # Launcher Windows: Server + Web local
└── AGENTS.md
```

Sơ đồ chỉ trình bày phần liên quan tới sản phẩm. Các nội dung độc lập hiện hữu như `doc/` hoặc giáo trình không bị di chuyển/xóa để khớp sơ đồ. Không tạo sẵn `services/` hoặc `packages/` khi chưa cần; một worker chạy riêng vẫn có thể dùng cùng package Server và entrypoint riêng.

Các phép thử [RTM-001](tasks/runtime/001-local-verification.md#rtm-001)/[RTM-002](tasks/runtime/001-local-verification.md#rtm-002) đã có `apps/client/scripts/probe_local_runtime.py` cho chẩn đoán, `apps/client/tests/unit/adapters/` cho test và `tests/fixtures/runtime-probe/` cho workspace Skill thử dùng chung. `tests/.agents/skills/` là bộ Skill nghiệp vụ người dùng cung cấp; chưa phải catalog production hoặc dữ liệu runtime. Kết quả chạy cục bộ đặt dưới `runtime/` đã được Git bỏ qua; xem [báo cáo kiểm chứng](../reports/local-runtime-check.md).

Trong `docs/`, [kiến trúc chính](../architecture/overview.md) dùng arc42; `development/` giữ plan và hướng dẫn dùng lại, `reports/` giữ kết quả kiểm chứng theo thời điểm. Task chi tiết tổ chức tại `development/tasks/<module>/`: README module → file đầu việc → checklist task con. Các thư mục `agents/`, `runs/`, `projects/processes/`, `skills/`, `settings/`, `client/`, `runtime/`, `runners/`, `robots/`, `overview/` bám phần sở hữu nghiệp vụ; `base/`, `data/`, `api/`, `execution/` nhóm trách nhiệm kỹ thuật, không tạo menu/module code mới. Xem [quy ước tìm và cập nhật task](tasks/README.md). Bản đồ đầy đủ và vai trò từng tài liệu nằm tại [docs README](../README.md); không tạo thêm thư mục/file rỗng để đủ mẫu.

## Tra cứu menu và tính năng

Project test Skill 0 có script chuẩn bị catalog/Project/Process qua HTTP và PC test tại `apps/client/scripts/skill0_test_project.py`; launcher `run-skill0-test.bat` ở root. Credentials/log điều phối nằm trong `runtime/skill0-test-project/` (ngoài Git); output nghiệp vụ ở thư mục làm việc trên PC theo Skill. Chế độ file gốc và kiểm tra output nằm trong `apps/client/src/agent_cf_client/execution/local_skill.py`; đây là công cụ test cho một Process, không phải daemon production. Xem [RTM-009](tasks/runtime/006-local-skill-pc-output.md); lịch sử demo upload tại [PROJ-004](tasks/projects/004-skill0-test-project.md).

Từ [checklist từng menu](implementation-plan.md#tiến-độ-từng-menu) hoặc [nền tảng dùng chung](implementation-plan.md#nền-tảng-dùng-chung), mở README của module rồi file đầu việc cần làm. Bảng cấu trúc dưới đây là nguồn vị trí code; task ID, dependency và bằng chứng hoàn thành được giữ trong file đầu việc tại [tasks/](tasks/README.md), không lặp checklist task tại đây hoặc ở plan tổng.

Các đường dẫn Web dưới đây tính từ `apps/web/src/features/`. Tên module Server là thư mục bên trong từng lớp `domain/`, `application/`, `infrastructure/`, `api/` của `apps/server/src/agent_cf_server/`; chỉ tạo ở lớp có trách nhiệm thực tế. Đây là ánh xạ tổ chức code dự kiến; hành vi của từng màn vẫn lấy từ [yêu cầu theo màn hình](../product/requirements.md#yêu-cầu-theo-màn-hình), tên kỹ thuật lấy từ [glossary](../product/glossary.md).

| Menu / phần giao diện | Thư mục Web | Module Server liên quan | Phạm vi code |
|---|---|---|---|
| Overview | `overview/` | `overview/` đọc tổng hợp từ các module nguồn | Ghép dữ liệu tổng quan; quy tắc và dữ liệu gốc thuộc module sở hữu |
| Projects | `projects/` | `projects/` | Danh sách, chi tiết và thông tin Project |
| Project → Team, Targets | `projects/team/`, `projects/targets/` | `projects/` | Thành viên và mục tiêu thuộc Project |
| Project → Process, editor Lưu/Chạy, Schedule | `projects/processes/` | `processes/` | Cấu hình Process/Task hiện tại, snapshot Run nội bộ và lịch chạy |
| Runs; tab Runs trong Project; Logs; chi tiết lỗi mở từ Overview | `runs/` | `runs/` | Theo dõi ProcessRun/TaskRun, log và thao tác trên lần chạy |
| Chạy theo thư mục chủ đề trên PC | `runs/RunForm.tsx`, `shared/PcPathInput.tsx`; Client `execution/local_skill.py` | `runs/`, `domain/processes/topic.py`, Project root trong `projects/` | Chọn/dán folder có sẵn, ghim root và truyền cùng ngữ cảnh cho các bước |
| Agent điều phối | `agents/` | `agents/` | Cấu hình Agent API giao việc/kiểm tra và usage theo Agent |
| Skills → Tools | `skills/`, `skills/tools/` | `skills/`, `skills/tools/` | Skill và danh mục Tool nội bộ |
| Robots | `robots/` | `robots/` | Danh mục Robot, version và thống kê |
| PC | `runners/` | `runners/` | Quản lý Runner, Machine và trạng thái kết nối Client |
| Connect PC / CF Client desktop | `runners/ConnectPc.tsx`; Client `desktop/`, `connection/` | `runners/`, `api/client_download.py` | Mở/cài Client, tracking pairing/heartbeat; build bằng `infra/build_client.py` và `infra/client/Bootstrap.cs` |
| Settings → Providers & Models API; Công cụ AI trên PC; Roles; General | `settings/` (`AiTools.tsx` cho model CLI) | `settings/`, `api/ai_tool_models.py` | Model API của Agent tách catalog model Codex/Antigravity; `ai_tool_models` sở hữu model CLI |

Process nằm trong Project trên Web; Server tách `processes/` để giữ riêng nghiệp vụ định nghĩa Process với quản lý Project. PC dùng tên thư mục `runners/` theo thuật ngữ kỹ thuật. Không tạo menu Processes hoặc Tools riêng từ cách chia module này.

## Ranh giới thay đổi giữa các tính năng

- Mỗi tính năng sở hữu UI, state và mã gọi API của nó. Màn hình khác cần hiển thị tính năng đó thì dùng điểm xuất công khai của module, không chép code hoặc import file nội bộ. Ví dụ tab Runs trong Project dùng phần hiển thị do `runs/` cung cấp.
- Mỗi module công bố điểm truy cập nhỏ, rõ ràng: Web dùng `index.ts` để xuất component/hook cần dùng bên ngoài; Server dùng use case hoặc interface có tên rõ. Đổi chi tiết nội bộ phải giữ hợp đồng đã công bố hoặc cập nhật các nơi gọi trong cùng thay đổi.
- Web phụ thuộc theo chiều `app → features → shared`. Các feature chỉ sử dụng điểm xuất công khai của nhau khi cần, không tạo phụ thuộc vòng. `shared/` không import ngược feature; route và sidebar được ghép tại `app/`.
- Server giữ chiều phụ thuộc giữa các lớp như phần dưới. Trong mỗi lớp, chia theo module nghiệp vụ; một module không truy cập bảng dữ liệu hoặc repository cụ thể của module khác. Nhu cầu phối hợp đi qua use case/interface công khai và được ghép dependency tại `bootstrap/`.
- Đặt quy tắc tại module sở hữu nghiệp vụ. Ví dụ Overview đọc tiến độ Project và trạng thái Run từ nguồn tương ứng; không tự viết lại cách tính Target hay vòng đời Run. Phần đọc tổng hợp của Overview không bắt buộc có `domain/overview/`.
- Code dùng chung chỉ đưa vào `shared/` hoặc thành phần hạ tầng chung khi có nhu cầu thực tế; không chuyển nghiệp vụ riêng vào đó để né ranh giới module.
- Mục tiêu là phần lớn chỉnh sửa nằm trong feature liên quan, không bảo đảm mọi thay đổi chỉ chạm một thư mục. Đổi API, schema, quyền hoặc quy tắc dùng chung phải cập nhật hợp đồng, migration, nơi sử dụng và test liên quan theo ma trận tác động trong [AGENTS.md](../../AGENTS.md#7-quy-tắc-thay-đổi-tài-liệu).

## Quy tắc đặt code

### Web

- `app/` ghép route, layout và provider cấp ứng dụng.
- `features/` dùng các tên trong bảng tra cứu. Bên trong mỗi feature, chỉ chia `components/`, `hooks/`, `api/` hoặc `state/` khi có nội dung; màn hình/tab riêng thuộc feature nào thì đặt trong feature đó. Không tạo thư mục rỗng để đủ mẫu.
- `shared/` chỉ nhận code thực sự được dùng chung; không chứa business rule chạy Process hoặc trở thành nơi gom mọi tiện ích.
- Web hiển thị trạng thái do server cung cấp, không tự định nghĩa lại vòng đời Run.

### Server

- `domain/`: ProcessVersion, TaskRun và các luật nghiệp vụ; không import FastAPI, ORM hoặc adapter kết nối.
- `application/`: các use case, điều phối và interface cần cho lưu trữ/giao việc; phụ thuộc `domain/`.
- `infrastructure/`: hiện thực các interface bằng database, lưu trữ artifact hoặc kết nối Client.
- `api/`: nhận request/sự kiện, validation tại ranh giới, chuyển sang use case; không chứa luật nghiệp vụ thay cho domain.
- `bootstrap/`: nạp cấu hình, ghép dependency và entrypoint. Worker chạy độc lập vòng đời request; Temporal là engine đã chọn cho thiết kế local theo [ADR 0003](../architecture/decisions/0003-process-engine-temporal.md). Adapter Temporal thuộc infrastructure, không để domain phụ thuộc SDK; Workflow/Activity đặt tại `infrastructure/runs/temporal/`; entrypoint worker và khởi tạo supervised relay của Server ở `bootstrap/`. Activity gọi interface API nội bộ Server, không mở SQLite nghiệp vụ hoặc gọi PC trực tiếp.
- Ngay khi triển khai một nghiệp vụ, đặt code trong module tương ứng ở từng lớp theo bảng tra cứu, ví dụ `domain/runs/`, `application/runs/`, `infrastructure/runs/`, `api/runs/`. Không dồn tất cả tính năng vào các file chung như `services.py` hoặc `routes.py`; không tạo module/lớp chưa có nội dung thực tế.

Chiều phụ thuộc chính: `application → domain`; `api` và `infrastructure` sử dụng các interface/use case ở phía trong; `bootstrap` ghép các thành phần cụ thể. Domain không phụ thuộc lớp ngoài.

### CF Client

- `connection/` quản lý kết nối server và gửi/nhận sự kiện; không tự quyết định luật nghiệp vụ Process.
- `execution/` quản lý công việc cục bộ, cây tiến trình, hủy/timeout và thu kết quả.
- `adapters/` hiện thực cách gọi Codex, Google Antigravity và tool có sẵn; không mặc định viết lại các tool đó.
- `desktop/` xử lý tray/phiên Windows, tách khỏi logic thực thi để có thể test độc lập.
- Client không import code nội bộ của Server; giao tiếp bằng hợp đồng có version. Web cũng không import package Python của Server/Client.
- Client chia theo năng lực thực thi thay vì sao chép menu Web. Tích hợp runtime/tool cụ thể nằm trong adapter riêng dưới `adapters/`; thay adapter không được buộc sửa UI hoặc luật nghiệp vụ Process.

## Hợp đồng, test và dữ liệu runtime

- `openapi/openapi.yaml` là nguồn chuẩn HTTP API khi được tạo; code client sinh tự động phải sinh từ nguồn chuẩn, không sửa tay. [Contract Client](../architecture/client-protocol.md) giữ handshake, journal, quyền và retry; HTTP trong OpenAPI là kênh chuẩn, WebSocket chỉ thông báo. Chưa sinh client code hoặc có handler triển khai.
- Mỗi ứng dụng có `tests/` và lệnh kiểm tra riêng. Test domain không cần khởi động FastAPI, database hoặc Codex thật; test tích hợp adapter được phân biệt với unit test.
- Đường dẫn test phản ánh module để dễ tìm: Web dùng `apps/web/tests/features/<feature>/`; Server dùng `apps/server/tests/unit/<layer>/<module>/` và `apps/server/tests/integration/<module>/`; Client dùng `apps/client/tests/unit/<capability>/` và `apps/client/tests/integration/<capability>/`. Ví dụ unit test luật Run ở `apps/server/tests/unit/domain/runs/`. Kiểm thử luồng qua nhiều module đặt trong `tests/integration/` của ứng dụng liên quan, không ép vào một feature. Chỉ tạo các thư mục khi có test thực tế.
- Migration thuộc Server. `infra/` chỉ chứa cấu hình triển khai cần thiết, không chứa business logic.
- DB nghiệp vụ local dùng SQLite theo [ADR 0004](../architecture/decisions/0004-sqlite-business-database.md). Khi triển khai, phần truy cập DB thuộc `infrastructure/` của Server và giữ các ranh giới module đã nêu; file DB/phụ trợ nằm trong dữ liệu runtime ngoài Git, Web/Client không mở trực tiếp file DB. Chưa có schema hoặc migration thực tế.
- Input/output video, audio, log runtime, credential và profile trình duyệt lưu ngoài source được theo dõi bằng git. Đường dẫn được cấu hình theo máy, không hard-code ổ đĩa của máy cũ.
- Chỉ tách package dùng chung khi có nhu cầu rõ; không chia sẻ toàn bộ domain Server sang Client để tránh ràng buộc triển khai.

## Khi scaffold hoặc thay đổi cấu trúc

Tạo từng phần theo mốc triển khai; bổ sung `__init__.py`, entrypoint, cấu hình build/test và dependency khi thật sự có code. Môi trường chuẩn bị dùng Python 3.14 với pip/venv, Node.js 24 với npm; phiên bản dependency được quản lý bằng manifest và lock theo [setup](setup.md). ORM và công cụ đóng gói chưa được chọn. Các `pyproject.toml` trong cây là dự kiến khi đóng gói package; hiện dependency Python nằm trong `requirements.txt` của từng ứng dụng. Khi cấu trúc thực tế thay đổi, cập nhật tài liệu này, README và hướng dẫn chạy trong cùng thay đổi; quyết định kiến trúc lớn phải có ADR.
