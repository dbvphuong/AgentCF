# 0011 - Lưu cấu hình và dùng ngay, tự chụp cấu hình khi chạy

- Status: Accepted
- Date: 2026-11-19

## Context

Người dùng đã kiểm thử Skill và công cụ ở PC. Web phục vụ điều khiển thực thi; các bước Draft/Version/Publish khiến việc sử dụng rườm rà. Chỉ Robot cần quản lý số phiên bản. Lịch sử Run vẫn phải giữ đúng cấu hình đã dùng.

## Decision

Skill dùng nguồn đã lưu mới nhất, gồm đường dẫn file chính và PC; không yêu cầu Publish. Process có một cấu hình hiện tại, lưu với token chống ghi đè thay đổi đồng thời. Web chỉ có Lưu và Chạy. Server kiểm graph, phạm vi Skill, công cụ/model, PC và quyền Tool khi lưu và trước khi chạy.

Khi tạo Run, Server tự đóng băng cấu hình Process cùng Agent/Skill/model hiện tại thành snapshot trong transaction tạo Run. Các bảng ProcessVersion/Task cũ tiếp tục lưu snapshot bất biến, không thành đối tượng người dùng phải quản lý. Khóa idempotency theo Process được kiểm trước khi chụp snapshot. Snapshot của Run cũ không bị cập nhật.

Lịch trên Web dùng cấu hình hiện tại khi đến hạn. Migration 022 chuyển lịch hiện có sang cơ chế đó, không sửa Run cũ; API cũ vẫn cho caller chỉ rõ snapshot để tương thích. Process cũ đọc cấu hình từ bản lưu gần nhất cho đến khi lưu cấu hình mới.

Robot giữ danh sách phiên bản. Form mới lưu phiên bản sẵn dùng trong một transaction; không có thao tác Draft/Publish riêng. API lifecycle cũ giữ tương thích. Quyết định này thay phần thao tác phiên bản thủ công của ADR 0005, giữ nguyên nguyên tắc Run tham chiếu snapshot bất biến.

## Consequences

Sửa Skill tác động lần chạy mới mà không cần lưu lại mọi Process. Run đang chạy giữ snapshot cũ. File Skill và output vẫn nằm trên PC; snapshot chỉ giữ tham chiếu và metadata nguồn, không sao chép Markdown/ref lên Web. Phải kiểm lại quyền và tính hợp lệ khi đến lịch vì cấu hình có thể đã đổi.

## Alternatives considered

Chỉ ẩn nút và tự chọn bản Published cũ khiến cấu hình vừa lưu không được dùng. Ghi đè snapshot đang được Run tham chiếu làm sai lịch sử. Cả hai phương án bị loại.
