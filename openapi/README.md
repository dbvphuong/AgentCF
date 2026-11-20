# Hợp đồng thiết kế nền

`openapi.yaml` là nguồn chuẩn HTTP, OpenAPI 3.1.0. Các API editor/Project local và phần lọc lịch sử Runs được cập nhật theo HTTP boundary; xem `x-implementation-status` từng operation. Nhiều contract nền vẫn giữ Design, chưa có client sinh tự động. Quy tắc giao tiếp tại [Client protocol](../docs/architecture/client-protocol.md), vòng đời tại [execution](../docs/architecture/execution-model.md), snapshot và mapping tại [domain](../docs/architecture/domain-model.md#định-nghĩa-process-động-và-snapshot).

Đồng bộ phần UI local sau khi sửa model/route bằng `node openapi/sync-local-ui.cjs`, rồi chạy checker dưới đây. Script chỉ thay các operation/schema UI được chỉ định, giữ hợp đồng nền khác. API `implemented-local` hiện dựa vào loopback, chưa có remote operator auth hoặc idempotency cho request tạo editor; các giới hạn không được mô tả như đã đáp ứng scope/receipt của thiết kế nền. [Báo cáo UI](../docs/reports/ui-completion-check.md) ghi phạm vi và task còn lại.

Contract bao phủ đọc/sửa/publish định nghĩa, tạo/xem/hủy Run, cấu hình, pairing/session/giao việc, event/result/observation, bundle/artifact và API nội bộ engine. `x-implementation-status` phân biệt health đã triển khai với route nghiệp vụ còn Design. Đây chưa phải toàn bộ CRUD/menu, scheduler, Human/Continue hoặc Agent review. Server kiểm scope và ownership ngoài việc xác thực bearer; `x-required-scope` ghi yêu cầu authorization. Không cung cấp URL server giả hoặc secret mẫu.

`examples/foundation-cases.json` gồm dữ liệu hợp lệ/bị từ chối, DAG chung và Skill 0–1–2 dạng fixture. ID model/adapter/Skill trong ví dụ là tổng hợp, không chứng minh runtime khả dụng. Kiểm tra graph trong script chỉ review cycle/reference, không thay validator nghiệp vụ sẽ triển khai.

Lỗi xóa ở API local tiếp tục trả `detail` dạng chuỗi và giữ mã HTTP hiện có (409 với catalog/PC, 422 với Project/Process chưa kết thúc thực thi). Theo [BASE-011](../docs/development/tasks/base/010-deletion-feedback.md), chuỗi hiển thị dùng tên dữ liệu và ngữ cảnh liên quan thay ID kỹ thuật, kèm hướng xử lý; ví dụ `Không thể xóa Provider “Local” vì còn Model API liên kết: “Model viết bài”. Vào Settings → Providers & Models API → Models API để xóa các model này trước.` Không đổi schema hoặc tự xóa dữ liệu phụ thuộc.

Kiểm tra độc lập từ root repository bằng Node; dependency đặt trong thư mục runtime đã ignore, không thay manifest ứng dụng:

```powershell
npm.cmd install --prefix runtime/design-review/node --no-audit --no-fund @apidevtools/swagger-parser@13.1.0 ajv@8.20.0 ajv-formats@3.0.1 yaml@2.9.1
node openapi/check-contract.cjs
```

Có thể truyền đường dẫn thư mục `node_modules` khác làm đối số đầu tiên. Phiên bản thực sự dùng trong review được ghi tại [báo cáo](../docs/reports/foundation-design-review.md). Script kiểm cấu trúc OpenAPI, biên dịch schema, các ca fixture và quy tắc scope/idempotency; không gọi HTTP, Temporal hoặc chương trình trên PC.
