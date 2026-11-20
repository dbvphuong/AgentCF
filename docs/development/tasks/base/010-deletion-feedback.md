# Thông báo rõ nguyên nhân khi không xóa được

[Module](README.md) · [Yêu cầu](../../../product/requirements.md#yêu-cầu-theo-màn-hình)

## BASE-011

- [x] **BASE-011 — Hiển thị tên dữ liệu đang chặn xóa trên toàn Web** — Xong | Fix
  - Nguồn: yêu cầu người dùng ngày 2026-11-20; áp dụng mọi thao tác xóa trên Web, không chỉ Provider.
  - Phụ thuộc: BASE-006; SET-002/003/005; PROJ-007; PC-003; ROB-001.
  - Tái hiện: xóa Provider vẫn có Model API liên kết → lỗi tiếng Anh chỉ có ID. Tool/Robot có lỗi tương tự; Project/Process/PC báo chung chung không xác định Run.
  - Nghiệm thu: thông báo tiếng Việt, tên mục đang xóa, loại/tên dữ liệu chặn và hướng xử lý. Process cần tên Project/bước hoặc version để tìm đúng; Run cần Process/Project, thời điểm giờ Việt Nam và trạng thái. Không lộ ID/SQL/secret; nhiều tham chiếu có danh sách giới hạn và số còn lại. Giữ nguyên điều kiện chặn, mã HTTP và giao dịch; không tự xóa dây chuyền hoặc dữ liệu thật. Robot dùng modal giữ nguyên lỗi để đọc/thử lại; không đề xuất Archive khi Web không có.
  - Vị trí: Server repositories Settings/Skills/Agents/Robots/Projects/Runners và helper hiển thị; Web Robot API/list, regression API/browser.
  - Bàn giao: lỗi `detail` vẫn là chuỗi, mã HTTP/điều kiện xóa/giao dịch không đổi. Helper `infrastructure/deletion_feedback.py` định dạng tên/danh sách và giờ Run; không truy cập chéo repository. Tên được render như text. Shared Web API giữ thông báo Server, có fallback tiếng Việt cho lỗi mạng/quyền/Server thay vì raw JSON. DELETE không tìm thấy catalog trả hướng dẫn tải lại thay ID.

### Phạm vi rà soát

| Nơi xóa | Thông báo khi bị chặn |
|---|---|
| Settings → Provider | Tên Provider và các Model API liên kết, hướng dẫn vào Models API |
| Settings → Model API/Role | Tên Model/Role và các Agent tham chiếu, hướng dẫn đổi cấu hình Agent |
| Model công cụ AI (API tương thích) | Tên Model, Process/Project/version tham chiếu, hướng dẫn tắt sử dụng để giữ lịch sử |
| Skills → Tools | Tên Tool, Skill/version và Agent tham chiếu; giải thích liên kết version đã phát hành vẫn bất biến |
| Skill / Agent điều phối | Tên Skill/Agent, Project, Process, bước và nguồn cấu hình hoặc snapshot Run chưa kết thúc |
| Robot | Tên Robot, bước/Process/Project/version tham chiếu hoặc version Robot đã phát hành; bỏ đề xuất Archive không có trên Web |
| Project / Process | Các Run chưa kết thúc với tên Process/Project, thời điểm tạo giờ Việt Nam và trạng thái; hoặc tên PC chưa xác nhận đã dừng |
| PC | Tên PC và các Run liên quan đang chặn, hướng dẫn vào Runs để dừng/chờ |
| Editor node/dây nối | Xóa cục bộ không có ràng buộc DB; Node Start đã có giải thích rõ là điểm cố định, giữ nguyên |

Các Web DELETE đi qua Catalog, Projects, PC hoặc Robots đã được rà soát. Xóa version Skill/model CLI là API tương thích, không thêm nút xóa mới. API đóng session PC không có thao tác xóa trên Web, không thay vòng đời phiên.

### Kiểm chứng 2026-11-20

- `.venv/Scripts/python.exe -m pytest apps/server/tests/integration/settings_skills_agents apps/server/tests/integration/projects apps/server/tests/integration/robots apps/server/tests/integration/runners -q`: **135 passed**. Gồm 23 regression mới trong `projects/test_deletion_feedback.py`; kiểm tên, không lộ ID/secret, model tắt/Agent archived, nhiều tham chiếu, rollback, xóa sau gỡ liên kết, các trạng thái Run, snapshot đang chạy, PC chưa xác nhận, Robot/Tool/version. Bổ sung kiểm thông báo PC tại `runners/test_runner_actions.py`; cập nhật assertion tiếng Việt trong test Robot, vẫn kiểm ràng buộc published.
- `npm.cmd run build` và `npm.cmd test` trong `apps/web`: TypeScript/Vite đạt, **23 passed**; có regression giữ nguyên named blocker và lỗi mạng/quyền/Server/AbortError. Không có lệnh lint riêng trong package.
- `node apps/web/tests/browser/deletion-feedback.cjs`: **10 thao tác xóa đạt**, lỗi ở trong modal, Robot không điều hướng nhầm khi click Xóa và thử lại thành công, **0 lỗi JavaScript/0 request API thật**. Fixture intercept mọi API; đã xem ảnh `runtime/deletion-feedback/{provider-error,robot-error}.png`, report `runtime/deletion-feedback/browser.json`.
- `node openapi/check-contract.cjs`: **97 schemas, 80 paths, 105 operations** đạt. Không đổi schema/mã HTTP; quy ước `detail` cập nhật tại `openapi/README.md`.
- Server local được nạp lại sau khi kiểm **0 Run/Attempt chưa kết thúc**. GET health đạt/schema **23**; số hàng Project/Process/Run/Attempt/Provider/Model/Role/Agent/Skill/Tool/Robot/PC giữ nguyên và `foreign_key_check` sạch. Không thử DELETE trên dữ liệu thật.

### Giới hạn

- Giữ nguyên chính sách xóa; không tự gỡ phụ thuộc hoặc mở quyền xóa Robot/version bất biến.
- Danh sách dài hiện tối đa tám mục cùng số còn lại. Skill/Agent/Robot nêu một vị trí Process đang chặn theo truy vấn hiện hành; không bổ sung màn hình phân tích phụ thuộc.
- Lỗi ràng buộc bất thường không xác định được tham chiếu vẫn có thông báo an toàn kèm tên mục/hướng tải lại, không đưa SQL ra Web. Kiểm chứng browser bằng Edge local/fixture, không phải toàn bộ trình duyệt hoặc runtime production.
