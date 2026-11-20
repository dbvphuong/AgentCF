# CF Client desktop và Connect PC có hướng dẫn

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-pc) · [ADR 0002](../../../architecture/decisions/0002-cf-client-windows.md)

## CLI-004

- [x] **CLI-004 — Mở/cài Client từ Connect PC và xác nhận kết nối thật** — Xong | Feature
  - Phụ thuộc: PC-001/003, CLI-001/002/003; giữ backlog RTM-008, RUN-008, BASE-003 và vòng Agent API riêng.
  - Web: nhập Workspace/tên PC → Mở CF Client qua agentcf URL; có tải bộ cài thật, hướng dẫn quay lại mở ứng dụng, fallback sao chép liên kết. Poll tracking ID đến khi có session + heartbeat; hỗ trợ hết hạn/tạo mã mới, đóng và mở lại modal. Không giả định trình duyệt đã mở EXE thành công.
  - Theo chỉnh của người dùng: Client gọn, không hiện ô Server/tên PC hoặc cấu hình model/tool. Cấu hình quản lý trên Web Center. Client nhận link, xác nhận, hiện trạng thái; có mở Web, dán link dự phòng, thu khay/thoát và startup Windows tùy chọn. Không còn nút tạm dừng công việc ở UI Client.
  - Migration 017: ID tracking và Runner đã ghép trong pairing record, os_name của PC. Mã 256-bit chỉ lưu hash, dùng một lần/hết hạn; tracking không lộ token. Session creation chưa được coi là heartbeat. Client desktop giữ credential bằng DPAPI hiện hành; registry protocol/startup chỉ HKCU, không admin.
  - Client chung dùng TaskExecutionWorker, một việc mỗi lần trong Workspace, không lọc riêng Project demo. Chỉ công bố capability tool tìm thấy và Server kiểm khi poll/claim; không tự cài/đăng nhập tool. Giữ heartbeat khi chạy việc; deadline/stop_attempt_ids dừng cây tiến trình qua ProcessManager. Robot dùng PID thật và ProcessManager thay PID giả/subprocess không hủy được. Thoát chờ việc xong; kết quả không được Server xác nhận không tự chạy lại.
  - Bộ cài .NET/WinForms + CPython đi kèm và HTTPX dependencies, không tải dependency khi cài và không cần Python trên PC đích. Native CF Client.exe giữ tiến trình launcher đến khi Python worker kết thúc, tìm được trong Task Manager. Một phiên theo profile/phiên Windows; mở lại hoặc protocol link chuyển tới instance hiện có. Khởi động cùng Windows không tự bật.
  - `run-client.bat`/`infra/start-client.ps1` mở Client đã cài, fallback source để phát triển. `run-skill0-test.bat` vẫn chỉ là demo riêng, không đổi tên thành Client chung.

### Code và kiểm chứng 2026-11-18

- Desktop: `desktop/entry.py`, `app.py`, `native_tray.py`, `windows.py`, `links.py`, `daemon.py`; `connection/credentials.py`/ClientSession; CLI desktop entry. Build: `infra/build-client.ps1`, `build_client.py`, `client/Bootstrap.cs`. Web: `features/runners/ConnectPc.tsx`. Server: runners API/repository và client_download API.
- `.venv/Scripts/python.exe infra/build_client.py`: tạo `runtime/client-build/CF Client Setup.exe`, khoảng **17.7 MB**, kèm interpreter/stdlib/Tk/HTTPX và license dependency. Installer chưa ký số; cảnh báo tải/chạy EXE tùy chính sách Windows/trình duyệt chưa được tự bỏ qua.
- `.venv/Scripts/python.exe -m pytest -q`: **232 passed, 1 skipped**. Test mới kiểm pairing pending/paired/heartbeat/expired/removed, đóng phiên/auth, download path cố định, URI data-only, DPAPI, và daemon chạy một Process ngoài demo với output file fixture thật. Không gọi LLM trong test.
- `npm.cmd test`: **19 passed**; `npm.cmd run build`: TypeScript/Vite đạt. OpenAPI checker: **94 schemas, 74 paths, 98 operations** đạt.
- `apps/web/tests/browser/client-onboarding.cjs` + `apps/client/scripts/probe_desktop_onboarding.py`: **passed** trên Server/DB riêng 18091, Web 5191, Edge CDP 9353. Web tạo mã nhưng chưa có Runner; GUI preview/xác nhận, session/heartbeat thật làm Web chuyển thành công; download trả EXE thật. Lặp lại sau khi bỏ ô Server/tên PC, probe kiểm main window không có Entry cấu hình. Desktop probe chỉ tự xác nhận trong test, không là cơ chế tự xác nhận của app thật.
- Source và bundle tự kiểm Tk/DPAPI/tool import đều đạt. Native tray, hide/show, thoát và tooltip Unicode dài đạt. Bộ cài được mở và bấm đúng nút Cài và mở; HKCU protocol và Start Menu shortcut có thật, startup vẫn tắt. Mở agentcf link vào app đã cài đi qua IPC và vẫn chỉ có một CF Client instance. Kiểm tra này dùng mã không hợp lệ, không tạo PC thật.

### Kiểm tra tiếp ngày 2026-11-19

- Build lại bộ cài từ source cuối; đồng bộ bản Client đã cài khi ứng dụng không chạy, giữ khóa độc quyền `client.lock` và giữ nguyên credential/cấu hình.
- Giao diện compact, entrypoint và IPC đã cài khớp source; bổ sung spool stdout/stderr Robot để tránh đầy pipe khi output dài.
- Chạy lại test Robots, Run execution và desktop daemon: **11 passed**; OpenAPI: **94 schemas, 74 paths, 98 operations** đạt. Không chạy model hoặc tạo Run trên dữ liệu thật. Server local không chạy tại thời điểm bàn giao kiểm tra này.

### Giới hạn

- Windows x64, chạy trong phiên người dùng; không phải Windows Service. Bộ cài cần .NET Framework có sẵn trên máy Windows đã kiểm tra, chưa nghiệm thu mọi bản Windows/máy sạch/chính sách doanh nghiệp. Chưa ký số và chưa có auto-update/uninstall UI.
- Client nhận việc chung không chứng minh mọi Skill/Robot hay Agent API đã chạy thật. Worker inline cũ còn giới hạn fixture; chế độ local Skill giữ file/ref/output trên PC. Server hiện có execution deadline tối đa khoảng 30 phút; Client không làm sống lại quyền hết hạn và chưa bổ sung cơ chế renew dài hạn.
- Kết quả không chắc chắn sau gián đoạn giữ journal/Server state để đối soát, không tự retry model. Không bảo đảm tool chạy khi đăng xuất; Client ngừng nhận việc mới khi desktop bị khóa.
- Tải bộ cài khác với trình duyệt cho phép mở/chạy file: vẫn cần hành động người dùng và policy hệ điều hành. Không ghi nhận một HTTP response tải EXE như bằng chứng app đã được cài.
