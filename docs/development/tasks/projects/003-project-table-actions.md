# Bảng Projects, menu thao tác và nhân bản

[Module](README.md) · [Requirements](../../../product/requirements.md#quản-lý-project-và-process-qua-giao-diện)

## PROJ-003

- [x] **PROJ-003 — Làm gọn bảng Projects và nhân bản toàn bộ cấu hình** — Xong | Feature
  - Phụ thuộc: PROJ-001/002, PROC-002/003 cho dữ liệu editor/version hiện có.
  - Phạm vi người dùng chốt: Project | Mô tả | PM | Trạng thái | ⋯; hai nhãn Đang hoạt động xanh / Không hoạt động đỏ; menu Sửa, Nhân bản, Ngừng hoạt động/Kích hoạt lại, Xóa; xác nhận thao tác ảnh hưởng dữ liệu. Nhân bản toàn bộ cấu hình, Team, Process/version, Targets giữ số liệu; lịch ở bản sao tắt, không chép Run/Logs/artifact.
  - Code: `features/projects/ProjectList.tsx`, `ProjectActions.tsx`, `projects.css`, tích hợp `Projects.tsx`; shared form/confirm thêm nhãn tùy chọn nhưng giữ mặc định cho màn khác. API `POST /v1/projects/{project_id}/clone` và transaction trong `ProjectManagement`; đồng bộ qua `openapi/sync-local-ui.cjs`. Không đổi migration hoặc dữ liệu demo.
  - Nghiệm thu: cột mô tả riêng, hàng cân đối và trạng thái có màu/nhãn; menu không cắt trong bảng, hỗ trợ bàn phím/Escape/click ngoài; xác nhận hiển thị đúng tên và tác động, Cancel không gửi mutation. Clone có identity độc lập, giữ snapshot published bất biến, Schedule tham chiếu version mới và luôn tắt; nguồn không đổi; idempotency/retry và rollback khi lỗi.
  - Kiểm chứng 2026-11-17:
    - `.venv/Scripts/python.exe -m pytest apps/server/tests/integration/projects -q`: **19 passed**; `.venv/Scripts/python.exe -m pytest -q`: **170 passed, 1 skipped** (Temporal opt-in).
    - `npm.cmd --prefix apps/web test`: **19 passed**; `npm.cmd --prefix apps/web run build` gồm TypeScript và Vite đạt.
    - `node openapi/sync-local-ui.cjs`, `node openapi/check-contract.cjs`: **74 schemas, 53 paths, 64 operations** đạt. Script giữ header Idempotency-Key đã khai báo bởi endpoint Clone, không tạo tham số trùng.
    - `node apps/web/tests/browser/smoke.cjs`: đạt tám menu/hai viewport và editor mobile (17 checks); thêm Project menu/keyboard/Escape/click ngoài, Clone form, Target giữ số liệu, bản sao không có Run và lịch tắt; Cancel ngừng hoạt động/Xóa không đổi dữ liệu, xác nhận thực sự mới thay đổi trạng thái. Source/clone độc lập; desktop/mobile không tràn toàn trang. Regression đếm Task node riêng với Start node trực quan hiện có, không sửa editor ngoài phạm vi.
    - Đã xem ảnh `runtime/ui-review/projects-1440.png`, `project-menu-1440.png`, `project-menu-390.png`; sửa padding bị ghi đè và vị trí menu theo vùng hiển thị thực của trình duyệt mobile để không cắt mất item.
  - Giới hạn: test dùng DB tạm riêng, không thay DB/ngắt Server/Web người dùng đang mở tại 8000/5173. Cần khởi động lại Server đang chạy để nạp endpoint Clone mới. Không thêm migration, không nhân bản danh mục toàn cục, không tự bật lịch/chạy model và không thay trạng thái nghiệm thu backend còn thiếu của module khác.
