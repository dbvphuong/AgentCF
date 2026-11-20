# Project test chạy Skill 0 bằng Codex CLI

> Bằng chứng dưới đây thuộc bản demo upload ban đầu. Bản demo hiện hành giữ quy trình và output gốc tại PC, gọi Skill bằng đường dẫn tuyệt đối: [RTM-009](../runtime/006-local-skill-pc-output.md). Không dùng kết quả cũ để khẳng định runtime đã tự gọi tool ghi file.

[Module](README.md) · [Hướng dẫn chạy](../../setup.md#project-test-skill-0-bằng-codex-cli)

## PROJ-004

- [x] **PROJ-004 — Chuẩn bị đầy đủ Project test Skill 0 chạy thật trên máy local** — Xong | Verification/Fix
  - Yêu cầu: người dùng muốn Project test có sẵn Process và Skill 0 để tạo cốt truyện bằng Codex CLI, đủ các thành phần để chạy được.
  - Nguồn: [Project](../../../product/requirements.md#project), [ADR 0005](../../../architecture/decisions/0005-versioned-process-execution.md).
  - Phụ thuộc: PROJ-001/002, PROC-003, SKL-001, AGN-003, PC-001, RTM-005.
  - Nghiệm thu: Workspace/Provider/Model/Role/Agent/Skill version/Project/Process version/PC riêng; Skill giữ nguyên nguồn; thực thi thật trả `succeeded`, có artifact `cot truyen.txt` tiếng Việt đủ nhân vật, điểm tương tác và Part 1–5; người dùng chạy lại từ Web với `topic` khác.
  - Phạm vi sửa: nhánh Skill 0 nạp instruction/standard/Agent snapshot đã publish, dùng timeout của node; Codex spool log tránh đầy PIPE khi output dài; script chuẩn bị dữ liệu qua HTTP và PC test chỉ nhận version đã cấu hình, launcher Windows riêng.
  - Không đóng RTM-008/RUN-008: chưa triển khai Skill tổng quát, mapping, Temporal relay hoặc daemon production. Không sửa ba Skill nguồn.
  - Code: `apps/client/scripts/skill0_test_project.py`, `apps/client/src/agent_cf_client/execution/task_worker.py`, `apps/client/src/agent_cf_client/runtime/codex_adapter.py`, `run-skill0-test.bat`.
  - Test: `apps/client/tests/unit/adapters/test_skill0_snapshot.py`; kiểm tra snapshot tiếng Việt, model/timeout, artifact khi thành công, lỗi không báo thành công, output JSONL 256 KiB không kẹt PIPE.

### Bằng chứng 2026-11-18 (Asia/Saigon)

- Project `0569909f-2206-49a5-bb3b-8d34aef34886`, ProcessVersion `6b78ef24-f9d9-4ef7-903b-ca2363d3d785`; model `gpt-5.6-sol`, Codex CLI 0.147.0, đăng nhập CLI đã có trên máy. Script dùng API public, Workspace và catalog test riêng; không ghi trực tiếp DB.
- Run `717f65c0-9bb8-4063-aaff-e35b872d7fa5`: **succeeded**, bắt đầu 08:41:05, kết thúc 08:43:14, khoảng 129 giây. Chủ đề: **Thật tệ khi làm mẹ đơn thân**. Artifact `8c1142d5-36ac-41eb-87b3-6a5282101b78`, `cot truyen.txt`, **28.110 byte UTF-8**; đã tải từ API, đối chiếu SHA-256, kiểm tra nhân vật, bốn mục tương tác và đúng năm tiêu đề Part 1–5. Đây là dàn ý, chưa chạy Skill 1/2 hoặc Agent duyệt chất lượng.
- SHA-256 artifact: `7019d8951283e990001f672f1fac9cf0a6f6807c06468c75c7186a5dd950d350`. Skill snapshot bằng nguyên văn file nguồn; hash file nguồn trước/sau không đổi. Cơ chế lưu là CLI `--output-last-message`, Client upload artifact về Server; không tuyên bố model tự ghi file bằng tool.
- Lượt đầu `173e5534-e247-4ac2-94eb-b08601415546` đã ghi nhận **failed**, không xóa lịch sử: phát hiện PowerShell đọc sai UTF-8 và đã dừng đúng cây Codex thử trước khi chạy mới. Đã sửa request thành UTF-8 BOM và chỉ dẫn đọc `-Encoding UTF8`; lượt thành công xác nhận log đọc đúng tiếng Việt. Runner test dùng effort `low`/`--ignore-user-config` cho lần gọi, không sửa cấu hình global.
- `.venv/Scripts/python.exe -m pytest -q`: **173 passed, 1 skipped**, một cảnh báo deprecation FastAPI/Starlette; test bỏ qua cần Temporal opt-in.
- `.venv/Scripts/python.exe -m pytest apps/client/tests/unit/adapters/test_skill0_snapshot.py apps/client/tests/integration/test_runtime_adapters.py -q`: **12 passed**, chạy lại sau chỉnh UTF-8. `py_compile` ba file Python thay đổi thành công.
- Kiểm tra trình duyệt Edge headless/CDP trên Web đang chạy: mở đúng Project, nút Run trỏ đúng published version, vào Run thành công → tab **Artifacts / Cốt truyện** đọc được file; không có JavaScript exception. Không submit thêm model call từ phép kiểm tra UI. Script/ảnh/bằng chứng local: `runtime/skill0-test-project/verify-ui.cjs`, `project-run-form.png`, `run-artifact.png`, `ui-validation.json`, `validation.json`; không đưa raw log/credential/output vào Git.
- Khởi chạy PC test thứ hai bị từ chối bởi file lock, không thay thế session đang hoạt động. PC tiếp tục chạy nền để người dùng chạy từ Web; sau restart dùng `run.bat` và `run-skill0-test.bat` theo hướng dẫn.

### Giới hạn còn lại

Runner chỉ nhận đúng ProcessVersion test, chưa theo version mới nếu người dùng publish lại graph. Timeout/quyền thực thi cố định cho thử nghiệm 600/900 giây; chưa thêm renew/cancel/recovery hoặc daemon tổng quát. Luồng một node dùng trực tiếp `topic` từ Run input, không chứng minh input mapping/JSON Schema tổng quát. Temporal đang tắt trên Server local; không đánh dấu BASE-003, RTM-008 hoặc RUN-008 hoàn tất từ kết quả này.
