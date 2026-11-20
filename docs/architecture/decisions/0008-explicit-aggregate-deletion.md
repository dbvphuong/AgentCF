# 0008 - Xóa chủ đích Project/Process và danh mục không còn dùng

- Status: Accepted
- Date: 2026-11-19

## Context

Người dùng xác nhận Xóa phải xóa hẳn Project kể cả đã có lịch sử hoặc version published. Không âm thầm chuyển thành Không hoạt động. Run chưa kết thúc phải được người dùng dừng và chờ kết thúc trước khi xóa. Skill/Agent chỉ bị chặn khi còn Process sử dụng. Quy tắc cũ cùng trigger bất biến không hỗ trợ thao tác này.

## Decision

- Xóa có xác nhận là thao tác riêng với Ngừng hoạt động/Kích hoạt lại. Server xóa nguyên tử aggregate Project/Process và toàn bộ lịch sử nghiệp vụ thuộc nó; giữ Workspace, PC, catalog dùng chung và file trên PC. Không thực hiện xóa dữ liệu thật chỉ để thử tính năng.
- Từ chối khi còn Run chưa terminal hoặc Attempt chưa xác nhận dừng. Check và delete trong cùng transaction SQLite `BEGIN IMMEDIATE`, không tự hủy Run.
- Migration 018 giữ mọi trigger bất biến đối với UPDATE và DELETE thông thường. Ngoại lệ DELETE qua hàm kiểm tra theo connection/table/rowid, mặc định từ chối; chỉ mở đúng các hàng đã chọn cho một câu DELETE trong service xóa và đóng trong `finally`. Không tắt FK hoặc drop trigger lúc chạy.
- Xóa lịch sử audit gắn với aggregate đã xóa và ghi audit riêng cho thao tác xóa. Artifact upload trên Server được đưa vào hàng đợi cleanup bền vững trong transaction; unlink file sau commit và thử lại khi khởi động/xóa tiếp, chỉ trong root artifact Server. Không đụng đường dẫn output PC.
- Skill/Agent còn được node ở bất kỳ ProcessVersion draft/published nào sử dụng bị từ chối xóa, kể cả Project Không hoạt động. Khi không còn Process tham chiếu, xóa được cùng version/snapshot và các liên kết catalog. Xóa Agent bỏ gán PM/Team nếu có; cần chọn PM mới trước khi lưu/chạy Project đó. Không tự xóa Skill/Agent khi xóa Project.
- Nội dung snapshot và lịch sử còn tồn tại tiếp tục bất biến. Đây là ngoại lệ xóa aggregate có chủ đích cho thiết kế snapshot tại ADR 0005, không cho phép sửa lịch sử hoặc mở rộng quyền thực thi.

## Consequences

- Không thể hoàn tác bằng Kích hoạt lại; phải khôi phục backup nếu cần. UI cảnh báo đúng phạm vi và chỉ báo thành công khi trả `deleted:true`.
- File Server bị hệ điều hành khóa có thể chờ cleanup, trong khi metadata/UI đã xóa. Các chương trình ngoài hệ thống, file PC và lịch sử Temporal riêng chịu vòng đời riêng; task này chỉ xóa dữ liệu nghiệp vụ local và artifact Server.
- Kiểm tra tham chiếu thực hiện phía Server trên định nghĩa Process đã lưu, không suy từ việc có version published hoặc membership trong danh mục.

## Alternatives considered

- Chuyển Xóa thành Archive: trái yêu cầu và gây hiểu nhầm khi mục vẫn hiện.
- Tắt FK/xóa toàn cục hoặc bỏ mọi trigger bất biến: có thể hỏng dữ liệu ngoài phạm vi.
- Xóa file trước commit: transaction lỗi sẽ mất file của dữ liệu chưa xóa.
