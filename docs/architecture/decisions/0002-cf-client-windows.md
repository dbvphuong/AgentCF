# 0002 - CF Client chạy trong phiên người dùng Windows

- Status: Accepted
- Date: 2026-11-13
- Last updated: 2026-11-16

## Context

Người dùng dùng tool có sẵn, Codex, Google Antigravity, trình duyệt và GPM. Một số bước có thể cần desktop hoặc profile đang đăng nhập. Web không trực tiếp chạy chương trình trên PC nếu không có thành phần thực thi tại máy đó.

Windows Service không trực tiếp tương tác desktop người dùng; chỉ chạy service dưới tên tài khoản người dùng cũng không tự biến nó thành tiến trình trong phiên desktop.

## Decision

Chấp thuận CF Client là ứng dụng Python chạy trong phiên đăng nhập Windows, chủ động kết nối outbound có xác thực tới Server. Entrypoint console đủ cho scaffold; tray và khởi động cùng phiên đăng nhập thuộc phần triển khai Client.

- Khởi chạy/giám sát Codex, Antigravity và tool theo cấu hình, không dựa vào việc bấm vào cửa sổ chat nếu có giao diện lập trình phù hợp.
- Kiểm tra phiên đăng nhập, adapter, đường dẫn và quyền cần thiết trước khi nhận/chạy việc.
- Trả log, lỗi, tiến trình và artifact về server; hỗ trợ yêu cầu hủy theo khả năng của chương trình con.
- Nếu sau này cần service hoạt động trước đăng nhập, tách service quản lý kết nối khỏi thành phần chạy trong phiên người dùng. Chưa triển khai mô hình hai tiến trình ở giai đoạn đầu.
- Không cam kết tool chạy khi khóa màn hình/đăng xuất; phải kiểm chứng riêng.

Chuyển từ Proposed sang Accepted trong BASE-001 ngày 2026-11-16 theo task hoàn thiện thiết kế; chưa có bộ cài, thư viện tray, cơ chế cập nhật hoặc Client production được kiểm chứng. [ADR 0005](0005-versioned-process-execution.md) chốt journal và quyền theo Attempt; [contract Client](../client-protocol.md) chốt ghép nối/thu hồi. Không sao chép credential runtime sang Server hoặc nhận shell từ Web.

## Consequences

- Dễ tiếp cận môi trường tool/profile của người dùng hơn service thuần.
- Đăng xuất có thể làm mất môi trường thực thi; phải hiển thị PC không sẵn sàng thay vì nhận việc rồi treo.
- Phải quản lý cây tiến trình, thư mục từng lượt chạy và quyền hành động; Cancel không được giả định hoàn tác side effect.
- Đổi PC cần cài tool/Agent, đăng nhập và ghép nối lại; không sao chép credential qua repository.

## Alternatives considered

- Windows Service thuần: phù hợp tác vụ không cần desktop, chưa phù hợp làm phương án duy nhất cho bộ tool hiện tại.
- Chỉ chạy từ trình duyệt: không đáp ứng điều khiển tool cục bộ và công việc tiếp tục khi đóng web.
- Ứng dụng desktop nặng chứa toàn bộ web: chưa cần khi Client chủ yếu nhận việc và thực thi.

## References

- [Microsoft: Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services)
- [Codex non-interactive](https://developers.openai.com/codex/noninteractive)
- [Codex App Server](https://developers.openai.com/codex/app-server)
- [Antigravity headless CLI](https://antigravity.google/docs/cli/headless/)
