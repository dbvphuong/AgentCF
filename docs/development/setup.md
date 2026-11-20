# Môi trường và cách chạy Agent CF local

> Last updated: 2026-11-17

Tài liệu này hướng dẫn chi tiết cách thiết lập, cài đặt và vận hành hệ thống Agent CF trên một máy tính mới từ đầu.

## Chạy các Skill cho một chủ đề có sẵn

Client 0.3.3 trên Windows ưu tiên native `codex.exe`, hoặc binary trong extension OpenAI của VS Code nếu PATH ngoài IDE không có; wrapper npm chỉ là fallback. Tránh gọi wrapper cũ không nhận model mới trong khi IDE đã hỗ trợ. Đường dẫn adapter cấu hình tường minh vẫn được ưu tiên; xem [RTM-012](tasks/runtime/009-codex-native-e2e.md).

Client 0.3.2 gửi trực tiếp `Gọi skill <path .md>` xuống dòng `cho chủ đề <path thư mục>`. Ô Yêu cầu riêng cho lần chạy nối nguyên văn lưu ý của bạn, ví dụ “Tuy nhiên viết 200–300 từ thôi nhé.”; để trống thì giữ mẫu hai dòng. Nhiệm vụ bổ sung ở node cũng chỉ nối khi có nội dung; không chép lại quy trình Skill.

Project cũ đã đặt thư mục ở node được migration 023 chuyển sang Project nếu chỉ có một root thống nhất; không cần nhập lại. Project đã có root được giữ nguyên. Khi nhiều thư mục khác nhau, chọn root mong muốn một lần trong Sửa Project; hệ thống không tự đoán theo vị trí Skill hoặc chủ đề.

Antigravity cần CLI nhận đúng Model ID (Gemini High: `gemini-3.8-flash-high`). Nếu giao diện có model mà CLI không nhận, kiểm tra `Get-Command agy` và `agy --version`: có thể tồn tại nhiều bản binary khác nhau. Client 0.3.1 bổ sung nhánh chạy file local; xem [RTM-010](tasks/runtime/007-antigravity-local-skill.md) để biết kiểm chứng và giới hạn môi trường hiện tại.

1. Trong **Sửa Project**, đặt **Thư mục Project trên PC** là thư mục thường mở trong Codex, ví dụ `E:\PhuongCH\AI\AgentCF\tests`.
2. Trong Process, cấu hình các node theo thứ tự Skill cần chạy; chọn Agent, Skill đã lưu, công cụ/model. **Nhiệm vụ bổ sung** để trống nếu không có yêu cầu khác. PC lấy theo Skill, thư mục làm việc lấy từ Project, không nhập tại node; Lưu rồi Chạy Process.
3. Bấm **Run** của Process, chọn hoặc dán đường dẫn thư mục chủ đề đã chuẩn bị bên trong Project, nhập yêu cầu riêng nếu có rồi **Chạy Process**. Client cần online để duyệt thư mục; dán path vẫn được, Client kiểm folder tồn tại trước thực thi.
4. Các bước dùng chung chủ đề, giữ cwd Project và đọc file bước trước theo Skill. Xem đường dẫn thật ở Runs → Kết quả trên PC. Không cần cấu hình mapping/schema cho luồng này.

Xem phạm vi và kiểm chứng tại [RUN-010](tasks/runs/007-topic-directory-launch.md); luồng này không chứng minh vòng Agent API hoặc mọi công cụ đã được nghiệm thu.

## Chạy nhanh trên Windows

Sau khi đã cài dependency ở mục 2, double-click **`run.bat` ở thư mục gốc repository**. Có thể chạy từ PowerShell bằng `./run.bat`.

- Tự khởi động Server `http://127.0.0.1:8000`, Web `http://127.0.0.1:5173` và mở trình duyệt sau khi health/proxy đã sẵn sàng.
- Giữ cửa sổ launcher khi sử dụng; **nhấn Enter trong cửa sổ đó để dừng Server và Web do launcher khởi động**. Đóng tab trình duyệt không dừng ứng dụng.
- SQLite vẫn lưu ở `runtime/server/agent_cf.sqlite3` theo cấu hình Server mặc định; khởi động lại không xóa dữ liệu. Server tự áp dụng migration còn thiếu. Launcher không tự cài dependency hoặc nạp `.env`; các biến môi trường cấu hình DB/artifact đã thiết lập được giữ nguyên.
- Đây là chế độ xem/quản lý UI local: Temporal tắt trong các tiến trình do launcher tạo; worker và PC Client chạy riêng khi cần thực thi Run. Không tự ghép nối PC hoặc gọi model.
- Nếu cả Server/Web của Agent CF đang chạy và health/proxy hợp lệ, launcher mở lại Web, không tạo bản chạy trùng hoặc dừng tiến trình có sẵn. Nếu cổng thuộc dịch vụ khác hoặc chỉ một phía đang chạy, launcher báo lỗi thay vì chiếm cổng.
- Log mỗi lần chạy nằm trong `runtime/local/<thời-điểm>-<id>/` gồm `server.out.log`, `server.err.log`, `web.out.log`, `web.err.log`. Khi khởi động lỗi, đường dẫn được in trong cửa sổ launcher.

`run.bat -CheckOnly` chỉ kiểm tra Python/Node/dependency, không mở dịch vụ hay thay DB. Có thể dùng `run.bat -ServerPort 8001 -WebPort 5174` khi cần đổi cổng; URL và proxy được đổi đồng bộ. `run.bat -NoBrowser` bỏ bước tự mở trình duyệt.

---

## Project test Skill 0 bằng Codex CLI

Project **TEST - Tạo cốt truyện Skill 0 bằng Codex CLI** có Workspace riêng, Provider/Model/Role, Agent làm PM/thành viên, Skill local đã publish, Process một bước và PC riêng. Bản demo hiện hành dùng **file Skill gốc**, giữ nguyên quy trình và output trên PC; bản demo upload cũ được archive, giữ lịch sử. Codex dùng phiên đăng nhập CLI trên máy; Provider trong Settings chỉ là metadata catalog, không dùng nút Test API để kiểm tra đăng nhập CLI.

1. Mở `run.bat` và giữ cửa sổ đó để Server/Web chạy.
2. Mở **`run-skill0-test.bat`**, giữ cửa sổ PC test. Nếu PC test đang chạy nền thì dùng tiến trình hiện tại, không mở bản thứ hai.
3. Vào `http://127.0.0.1:5173/#projects`, chọn Project trên → Process **Skill 0 - Thực thi trên PC** → **Run**. Hoặc vào Runs → tạo Run, chọn đúng Project/Process.
4. Nhập JSON, rồi bấm chạy:

   ```json
   {"topic":"Thật tệ khi làm mẹ đơn thân"}
   ```

5. Mở chi tiết Run → **Kết quả trên PC**, sao chép đường dẫn hoặc mở trực tiếp thư mục trên PC. Với chủ đề mẫu, file là `E:\PhuongCH\AI\AgentCF\tests\Thật tệ khi làm mẹ đơn thân\cot truyen.txt`. File do Codex dùng tool tạo, không phải Client lấy câu trả lời rồi ghi thay. Có thể đổi `topic` để chạy chủ đề khác. Skill 0 tạo **dàn ý**; bài hoàn chỉnh thuộc Skill 1.

Skill → **Thêm mới/Sửa** có **PC chứa file Skill**, **File .md chính của Skill** và **Chọn file…**. Dán đường dẫn tuyệt đối hoặc chọn file trên PC đó qua Client đang chạy bản mới, không upload nội dung hoặc dùng đường dẫn giả `C:\fakepath`. Chỉ chọn file chính (thường là `SKILL.md`, có thể mang tên `.md` khác); CLI tự đọc các ref tương đối từ thư mục chứa file chính. Lưu xong dùng ngay trong Process. Mỗi lần chạy tự chụp tham chiếu đường dẫn/PC và đọc file gốc hiện tại. Các trường này cũng có khi tạo Skill từ Process editor. Process editor → node Agent chọn đúng **PC thực thi** và **Thư mục làm việc trên PC**. Demo dùng `E:\PhuongCH\AI\AgentCF\tests\.agents\skills\0.tao_cot_truyen\SKILL.md` và working directory `E:\PhuongCH\AI\AgentCF\tests`. Không đổi Skill gốc để chạy demo.

PC test nhận các version published của Process demo đã cấu hình, không xử lý Project khác. Node demo giới hạn 600 giây, quyền thực thi 900 giây; heartbeat mỗi 3 giây. Đây là runner test riêng, chưa phải daemon Client tổng quát hoặc kiểm chứng Temporal. Không tự retry khi chưa rõ kết quả. Ctrl+C chờ công việc hiện tại kết thúc rồi dừng PC test. Để giữ cấu hình sau restart, không xóa thư mục runtime. Cần tránh chạy hai tác vụ cùng sửa một output; không dùng cùng chủ đề để ghi đè file có sẵn nếu chưa có chủ đích.

Script `apps/client/scripts/skill0_test_project.py` có ba lệnh: `setup` tạo cấu hình (không gọi model), `serve` mở PC nhận việc, `run --topic "..."` tạo một Run thật; cấu hình ban đầu nhận `--skill-path` và `--working-directory` tuyệt đối. Dùng `.venv/Scripts/python.exe`, `PYTHONPATH=apps/client/src`; mặc định model `gpt-5.6-sol`, chỉ dùng model đã kiểm chứng trên tài khoản/máy. Lượt Codex local dùng effort `low` và sandbox `workspace-write` tại thư mục làm việc, giữ config/tool đã cài của người dùng; không sửa config/đăng nhập global. Không dùng `--ignore-user-config` cho lượt local: CLI 0.147.0 đã được quan sát nhận quyền read-only với tùy chọn này dù yêu cầu workspace-write. Script thêm loopback vào `NO_PROXY` trong tiến trình để HTTP local không đi qua proxy công ty; không sửa cấu hình hệ thống. Credentials/log điều phối ở `runtime/skill0-test-project/`, ngoài Git; output nghiệp vụ nằm ở working directory theo Skill. Chế độ Skill local hiện kiểm chứng Codex; adapter khác báo chưa hỗ trợ thay vì tự chuyển runtime.

## 1. Yêu cầu tiên quyết (Prerequisites)

- **Hệ điều hành**: Windows 10/11 hoặc Linux / macOS (hướng dẫn mẫu sử dụng PowerShell trên Windows).
- **Python**: Phiên bản **3.14** (hoặc 3.12+).
- **Node.js**: Phiên bản **24.x** kèm **npm 11.x**.
- *(Tùy chọn cho Agent Skill execution)*: Codex CLI (`codex`) hoặc Antigravity CLI (`agy`) nếu chạy tác vụ AI thực tế trên máy local.

---

## 2. Cài đặt Dependency trên máy mới

Mở PowerShell tại thư mục gốc repository (`AgentCF`):

```powershell
# 1. Khởi tạo môi trường ảo Python 3.14
py -3.14 -m venv .venv

# 2. Cài đặt các gói phụ thuộc Python
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. Kiểm tra tính toàn vẹn phụ thuộc Python
.venv/Scripts/python.exe -m pip check

# 4. Cài đặt gói phụ thuộc cho ứng dụng Web
npm.cmd --prefix apps/web ci --prefer-offline
```

---

## 3. Khởi tạo Cơ sở Dữ liệu và Migrations (001–021)

Agent CF sử dụng SQLite chế độ WAL với kiểm tra khóa ngoại (Foreign Keys) và transaction nguyên tử. Toàn bộ schema từ migration `001` đến `021` (gồm Process, Runner Pairing, Robot Catalog, Quality Review Loop, Recovery/Observation, Scheduling & Overview, Backup & Audit, Project/Team/Targets, Skill local/scope, xóa aggregate, root Project, identity PC và telemetry RAM) được khởi tạo tự động:

```powershell
# Thiết lập PYTHONPATH cho Server
$env:PYTHONPATH = 'apps/server/src'

# Chạy lệnh migrate để áp dụng toàn bộ schema migrations 001 -> 021
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.server migrate
```

Cơ sở dữ liệu mặc định sẽ được tạo tại `runtime/server/agent_cf.sqlite3`.

Migration 011 bổ sung tham chiếu file Skill local và PC sở hữu; không chuyển đổi/sửa các SkillVersion hoặc ProcessVersion đã publish trước đó.

Migration 012 thêm phạm vi Global/nhiều Project cho Skill; Skill hiện có giữ Global, không sửa version và lịch sử. Khi tạo/sửa Skill mới, tích ít nhất một Project hoặc Global; không cần giữ Ctrl. Bảng Skills lọc một Project sẽ gồm Skill của Project đó và Global. Trong node editor, **Tạo Skill cho Project này** mở form chọn sẵn Project hiện tại. Skill dùng chung nhiều Project vẫn là một Skill, không nhân bản nội dung.

---

## 4. Khởi động Server

Chạy Server ở chế độ nền tảng HTTP API:

```powershell
$env:PYTHONPATH = 'apps/server/src'
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.server
```

- **Địa chỉ phục vụ**: `http://127.0.0.1:8000` (chỉ gắn loopback an toàn).
- **Health check**: `GET http://127.0.0.1:8000/healthz`
- **Tài liệu API Swagger**: `GET http://127.0.0.1:8000/docs`
- **OpenAPI Schema**: `GET http://127.0.0.1:8000/openapi.json`

---

## 5. Khởi động Giao diện Web (Frontend)

Mở một cửa sổ terminal mới và khởi động Vite development server:

```powershell
npm.cmd --prefix apps/web run dev
```

- **Truy cập giao diện**: Mở trình duyệt tại `http://127.0.0.1:5173`.
- **Proxy**: Mọi API gọi tới `/api` hoặc `/v1` sẽ tự động được chuyển tiếp tới Server port 8000.
- **Các màn hình đã hoạt động đầy đủ với dữ liệu thật**:
  - **Tổng quan (Overview)**: Khối cảnh báo lỗi đỏ chưa xử lý, xác nhận lỗi, bảng tiến độ mục tiêu Project, bảng xếp hạng token Agent thực tế.
  - **Điều phối & Chạy Process (Runs)**: Tạo lượt chạy mới từ cấu hình Process đã lưu, xem danh sách lịch sử phân trang / lọc theo trạng thái, chi tiết các bước DAG, nhật ký Logs thời gian thực, xem & tải artifact an toàn UTF-8, hủy lượt chạy (Cancel), và tiếp tục khi có can thiệp người dùng (Continue).
  - **Robots (Chương trình độc lập)**: Catalog Robot, quản lý phiên bản, Lưu dùng ngay, tính toán tỷ lệ thành công theo version từ dữ liệu thực tế, thực thi script/node trên PC Runner.
  - **Trạng thái kết nối**: Kiểm tra kết nối an toàn với Control Plane Server.

---

## 6. Ghép nối và Chạy PC Runner Client

Agent CF Runner Client chạy trên máy tính người dùng, kết nối outbound tới Control Plane và nhận việc qua CAS (Compare-And-Swap) an toàn:

### Kết nối từ Web Center

1. Mở **PC → Connect PC**, chọn Workspace và đặt tên PC trên Web.
2. Bấm **Mở CF Client trên máy này**. Nếu chưa cài, tải **CF Client Setup.exe**, mở và bấm **Cài và mở CF Client**; quay lại Web bấm mở Client lần nữa. Trình duyệt có thể hỏi mở ứng dụng.
3. Client chỉ hiện yêu cầu kết nối và trạng thái; bấm **Kết nối**. Không nhập/sửa Server hoặc tên PC trong Client. Các cấu hình PC/công cụ/model quản lý tại Web Center.
4. Web tự báo thành công sau session và heartbeat thật. Đóng cửa sổ Client sẽ thu xuống khay; Thoát chờ công việc hiện tại kết thúc. Khởi động cùng Windows là tùy chọn trong Client, không tự bật.

Nếu ứng dụng không mở từ trình duyệt, mở CF Client từ Start Menu, hoặc chạy **`run-client.bat`** tại root. Trong Web mở phần **Kết nối PC khác / dán liên kết thủ công**, sao chép liên kết rồi chọn **Dán liên kết** trong Client. URL localhost chỉ dùng cùng máy; PC khác phải truy cập HTTPS tới cùng Web Center trước khi lấy liên kết. Không dùng mã/địa chỉ của một Server cho Server khác.

Client được cài tại `%LOCALAPPDATA%\AgentCF\Client\CF Client.exe`; profile/credential DPAPI tại `%LOCALAPPDATA%\AgentCF`, thuộc tài khoản Windows hiện tại. Task Manager → **Details → CF Client.exe** (kèm tiến trình Python nội bộ). Đây là app trong phiên đăng nhập, không phải Windows Service. CLI/tool vẫn phải được cài và đăng nhập riêng trên PC.

### Build hoặc phát triển Client

Tại root trên Windows x64 với `.venv` đã cài dependency và CPython có Tk:

```powershell
.venv/Scripts/python.exe -m pip install -r infra/client/requirements-build.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra/build-client.ps1
.\run-client.bat
```

Builder dùng compiler .NET Framework Windows, CPython hiện có và dependency HTTPX trong `.venv`, đóng gói bộ cài `runtime/client-build/CF Client Setup.exe`. Không tải Python khi người dùng cài. Server phục vụ đúng file này qua `/v1/client/windows-installer`; có thể đổi `AGENT_CF_SERVER_CLIENT_INSTALLER_PATH`. Installer chưa ký số; tuân theo xác nhận/chính sách tải/chạy của Windows. Không tự bỏ qua cảnh báo của hệ điều hành.

`run-client.bat` ưu tiên app đã cài; nếu chưa cài sẽ mở source bằng `.venv/Scripts/pythonw.exe`. Bản source có nút Đăng ký mở từ Web dành cho phát triển. Entrypoint tương đương là `python -m agent_cf_client desktop`; không có lệnh `daemon` cũ từng mô tả. `run-skill0-test.bat` là launcher demo riêng, không phải Client chung.

CLI ghép nối thủ công cũ (`python -m agent_cf_client pair --server-url ... --code ...`) vẫn giữ để chẩn đoán. Credential của CLI/source legacy tại `~/.agent_cf/runner_credentials.json` là file JSON, không được mô tả là kho OS an toàn; app desktop mới dùng DPAPI riêng. Không sao chép credential/login CLI lên Web. Giới hạn runtime, phiên Windows, deadline và kiểm chứng tại [CLI-004](tasks/client/004-desktop-onboarding.md).

---

## 7. Sao lưu và Phục hồi SQLite (Backup & Restore)

Agent CF cung cấp công cụ sao lưu snapshot online nhất quán (sử dụng SQLite Online Backup API) và phục hồi kiểm tra tính toàn vẹn:

```powershell
$env:PYTHONPATH = 'apps/server/src'

# Sao lưu snapshot nhất quán trực tuyến (không cần dừng Server)
.venv/Scripts/python.exe -m agent_cf_server.tools.backup_restore backup `
    --database runtime/server/agent_cf.sqlite3 `
    --output runtime/backups/agent_cf_snapshot.sqlite3

# Kiểm tra tính toàn vẹn và phục hồi
.venv/Scripts/python.exe -m agent_cf_server.tools.backup_restore restore `
    --source runtime/backups/agent_cf_snapshot.sqlite3 `
    --target runtime/server/agent_cf_restored.sqlite3
```
Chi tiết về quy trình vận hành và khắc phục sự cố: xem [`docs/operations/backup-restore.md`](../operations/backup-restore.md).

---

## 8. Chạy Bộ Kiểm Thử Tự Động (Automated Test Suites)

Để xác minh toàn bộ hệ thống hoạt động ổn định trên máy mới, hãy chạy các bộ kiểm tra sau:

```powershell
# 1. Bộ kiểm thử toàn diện Python (Server, Client, E2E Dynamic Processes, Quality Review, Recovery)
.venv/Scripts/python.exe -m pytest

# Kết quả mong đợi: 151 passed, 1 skipped (test Temporal service opt-in)

# 2. Kiểm tra typecheck TypeScript phía Web
npm.cmd --prefix apps/web run typecheck

# 3. Bộ kiểm thử chức năng Frontend Web
npm.cmd --prefix apps/web test
# Kết quả mong đợi: 16 passed, 0 failed

# 4. Kiểm tra biên dịch ứng dụng Web
npm.cmd --prefix apps/web run build

# 5. Kiểm tra tính hợp lệ hợp đồng OpenAPI 3.1
node openapi/check-contract.cjs
# Số schema/path/operation hiện tại được lệnh in ra; không dùng số đếm cũ làm chuẩn.
```

---

## 9. Cấu hình Biến Môi trường (Environment Variables)

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `AGENT_CF_SERVER_HOST` | `127.0.0.1` | Địa chỉ lắng nghe của Server (chỉ loopback) |
| `AGENT_CF_SERVER_PORT` | `8000` | Port dịch vụ HTTP API |
| `AGENT_CF_SERVER_DATABASE_PATH` | `runtime/server/agent_cf.sqlite3` | Đường dẫn file CSDL SQLite nghiệp vụ |
| `AGENT_CF_SERVER_DATABASE_BUSY_TIMEOUT_MS` | `5000` | Timeout khóa ghi SQLite |
| `AGENT_CF_SERVER_REQUEST_TIMEOUT_SECONDS` | `5` | Giới hạn thời gian kết nối outbound |
| `AGENT_CF_CLIENT_SERVER_URL` | `http://127.0.0.1:8000` | Địa chỉ Control Plane mà Client kết nối tới |
| `AGENT_CF_WEB_SERVER_URL` | `http://127.0.0.1:8000` | Địa chỉ Server mục tiêu mà Web Vite proxy tới |

## 10. Giao diện theo prototype và kiểm tra trình duyệt

Web mở mặc định Overview, có tám menu trong sidebar; dùng Ctrl/Cmd+K để chuyển nhanh. Các màn lấy dữ liệu từ Server, không tự seed catalog mẫu. Trên DB mới, khai báo Provider/Model/Role phù hợp trong Settings, tạo Skill và lưu đường dẫn file/PC, tạo Agent với Skills/Allowed tools, rồi tạo Workspace/Project với PM. Team và Targets nằm trong Project. Model ID phải lấy từ cấu hình runtime đã kiểm chứng trên máy, không đoán từ nhãn hiển thị.

Trong Project, tạo Process, thêm Agent/Skill hoặc RobotVersion/PC, cấu hình dependency và Lưu. Chạy chọn thư mục chủ đề hoặc input nâng cao; Server tự chụp cấu hình cho Run, không yêu cầu Publish/chọn version. Save Schedule không Start; Stop không Cancel. Các giới hạn publish, runtime tổng quát, telemetry và secret store được ghi rõ trong [báo cáo UI](../reports/ui-completion-check.md); đây chưa phải xác nhận toàn bộ sản phẩm sẵn sàng production.

Regression UI dùng Server với DB mới trong thư mục tạm và Vite proxy riêng; không chạy smoke trên DB đang sử dụng vì smoke có tạo catalog/Project/Run. Ví dụ sau khi đã chạy Server thử tại `18080`, Vite tại `5178` proxy về Server đó và Edge headless CDP tại `9338`:

```powershell
$env:BASE_URL = 'http://127.0.0.1:5178'
$env:CDP_URL = 'http://127.0.0.1:9338'
node apps/web/tests/browser/smoke.cjs
```

Smoke kiểm tra tám menu desktop/mobile, catalog/version, editor kéo node/publish/reload, Schedule Start/Stop, Run/create/cancel, PC pairing/Disable. Ảnh lưu ở `runtime/ui-review/`; không gọi runtime hoặc provider trả phí. Test API provider chỉ được gọi khi người vận hành bấm nút tương ứng, không nằm trong smoke này.


Migration 013 giữ identity lịch sử khi Xóa PC bằng dấu `deleted_at`; danh sách ẩn PC đã gỡ, credential/session bị thu hồi. [PC-003](tasks/runners/003-edit-remove.md).

Form node dùng **Nhiệm vụ** để nhập prompt, ví dụ `done`. Chọn **Agent điều phối** từ danh mục đang hoạt động, Skill đã lưu, **Công cụ AI thực thi** và **Model thực thi**. Model CLI không lấy từ Agent API. Settings → **Providers & Models API** cấu hình API của Agent; Settings → **Công cụ AI trên PC** → chọn Codex CLI/Antigravity → thêm/sửa tên, Model ID gửi tới CLI và Bật sử dụng. Chỉ model đã bật của đúng công cụ hiện trong node. Migration 015 tạo danh mục CLI riêng với một model khởi tạo mỗi công cụ; giữ API model và lịch sử cũ. Field runtime_adapter của API model từ migration 014 không dùng cho lựa chọn mới. Task key tự sinh; Timeout/mapping/schema ở **Cấu hình nâng cao**. [SET-005](tasks/settings/005-ai-tool-models.md).
