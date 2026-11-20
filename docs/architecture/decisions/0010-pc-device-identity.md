# 0010 - Định danh PC ổn định tách khỏi credential kết nối

- Status: Accepted
- Date: 2026-11-19

## Context

Người dùng xác nhận một máy chỉ có một dòng PC, Kết nối lại không tạo bản ghi mới; cần Hủy kết nối riêng với Xóa. Tên/OS không đủ chứng minh cùng máy, fingerprint cũ đã bị session ghi null.

## Decision

- Định danh device ổn định, credential luân chuyển và session là ba thứ riêng. Client dùng hash Windows MachineGuid hoặc fallback installation ID, kèm proof ngẫu nhiên bảo vệ DPAPI. Server chỉ lưu proof hash.
- Unique PC còn hoạt động theo Workspace/device. Pairing code có target cho reconnect một PC cụ thể; giữ ID/config, revoke credential/session cũ, chặn unfinished execution. Untargeted reconnect một device đã có cần proof, không dựa trên tên.
- Client có credential hợp lệ được gắn identity cho PC legacy khi mở session; không tự chuyển dữ liệu sang PC khác. Legacy ambiguous không được gộp chỉ vì trùng tên/OS.
- Hủy kết nối giữ PC/identity/file và thu hồi session/credential; Xóa vẫn là thao tác riêng giữ quan hệ lịch sử. Không tự restore PC đã Xóa hoặc đổi Workspace khi reconnect.
- Telemetry là sample Client đọc từ OS, không phải định danh máy hoặc bằng chứng tiến trình đã dừng. Phiên mới reset sample, offline không trình bày sample cũ như live.

## Consequences

- Kết nối lại trên cùng máy không tạo dòng trùng, các tham chiếu Skill/Process giữ nguyên. Chứng thực pairing và nguồn cấu hình vẫn được kiểm tra tại Server.
- MachineGuid không phải secret, nên không dùng nó thay authentication/proof. Máy clone/reinstall cần xử lý identity riêng; task không thêm nhận diện TPM hay chuyển Workspace.
- Thay đổi vòng đời Delete PC tại task PC-003 được giữ: chỉ reconnect PC chưa bị xóa mới giữ ID; các audit/snapshot cũ không bị sửa.

## Alternatives considered

- Ghép máy theo tên/OS: có thể gộp nhầm máy thực sự khác nhau.
- Mỗi pairing luôn tạo ID: tạo trùng, làm mất liên kết cấu hình khi người dùng xóa nhầm dòng.
- Chỉ đổi label hoặc ẩn dòng trùng trên UI: không sửa identity/credential và vẫn có thể dispatch sai PC.
