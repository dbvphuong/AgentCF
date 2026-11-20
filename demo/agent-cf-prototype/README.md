# Agent CF HTML Prototype

Prototype tĩnh dùng để review cấu trúc module, luồng chính và visual direction của Agent CF. Đây không phải frontend production và không kết nối backend.

Định hướng đã review được đồng bộ tại [yêu cầu theo màn hình](../../docs/product/requirements.md#yêu-cầu-theo-màn-hình). Khi làm sản phẩm thật, dùng tài liệu đó cho hành vi nghiệp vụ; README này hướng dẫn mở và kiểm tra bản giả lập.

## Mở prototype

Từ thư mục repository:

```powershell
python -m http.server 4173 --bind 127.0.0.1 --directory demo/agent-cf-prototype
```

Sau đó mở `http://127.0.0.1:4173`.

Prototype không có dependency ngoài và không cần build. Có thể mở trực tiếp `index.html`, nhưng static server cho hành vi gần môi trường web hơn.

## Hướng trình bày

Settings dùng tiêu đề và nhãn ngắn, không lặp mô tả dưới tiêu đề/tab. Giải thích thông số kỹ thuật đặt tại dấu `?`, hiện khi hover hoặc focus; chỉ giữ thông báo cần thiết để người dùng quyết định.

Giữ bố cục quản trị và bảng màu tím. Nội dung chính dùng cỡ chữ khoảng 15px, tiêu đề khối 17px và chữ phụ chủ yếu 12–13px; chữ phụ được tăng độ đậm để dễ đọc hơn. Hàng dữ liệu và ô nhập có thêm khoảng trống, bảng rộng cuộn ngang trong khối, dashboard xếp dọc trên màn hình hẹp. Các quy tắc cụ thể nằm trong `styles.css`.

## Module có trong bản review

- Overview: khối đỏ chỉ có lỗi run chưa xử lý; bên dưới có bảng tiến độ Projects và token Agents. Token xếp từ cao xuống thấp, kèm tổng tháng. PC offline được nhắc gọn trong phần Projects.
- Đánh dấu “Đã xử lý” chỉ ẩn cảnh báo, không sửa Failed hoặc Logs; Run detail có Reopen alert. Running mở Runs của đúng Project và lọc lượt đang hoạt động. Bấm Agent xem số token chính xác và model. Target/tiến độ dùng chung nguồn với Projects, không hiển thị 0/0 khi chưa có target hiện tại.
- Toàn bộ giao diện chỉ theo dõi một tổng Tokens cho mỗi Agent; không có Cost, Budget, tiền tệ hoặc cảnh báo ngân sách. Token là số liệu mẫu; chưa đặt ngưỡng cảnh báo token.
- Projects dùng bảng có Search, PM, target hiện tại, tiến độ và cảnh báo cụ thể. Bên trong dự án có Processes, Team, Targets và Runs; header thu gọn thành một dòng, không có các thẻ thống kê lặp lại.
- Team là nhân sự riêng của dự án: Manage team thêm/bỏ thành viên mà không xóa Agent toàn cục. PM và Agent đã được giao Task được giữ lại. Token toàn cục của Agent không được quy thành token riêng của Project nếu chưa có dữ liệu phân bổ.
- Targets có kỳ tuần/tháng, ngày bắt đầu/kết thúc, số lượng mục tiêu, kết quả được duyệt và tiêu chí nghiệm thu. Tiến độ không tự tăng theo số run thành công; số liệu duyệt là dữ liệu mẫu được nhập trong form. Header ưu tiên target tháng đang hiệu lực, nếu không có thì dùng target tuần.
- Bảng Process giữ Run, Start/Stop và menu ⋯ (Schedule, Edit, Delete). Cột Schedule ghi version đang dùng; không còn cột PC chung. Last run mở chi tiết. PC Robot vẫn cấu hình tại node.
- Process: Schedule, Start/Stop và sơ đồ node kéo thả, xem Agent/Skill/Tool từng Task.
- Agents, Skills (gồm Tools nội bộ) và Robots độc lập.
- Cả ba mục có New/Edit/Delete và danh sách Archived/Restore. Agent cấu hình tên, vai trò, hướng dẫn, model minh họa, Skills và Allowed tools. Skill cấu hình hướng dẫn, Expected output và Tools; sửa Skill tạo version catalog mới và giữ bản trước. Tool cấu hình tên, mô tả và loại; chưa kết nối công cụ thật.
- Runs: lượt đang chạy, lịch sử, chi tiết Task, output, Logs và Cancel run.
- PC và Settings.
- PC có Connect giả lập với mã hết hạn sau 10 phút, tên hiển thị, Details, Disable/Enable và Remove có xác nhận. CPU/RAM hiển thị phần trăm, hover hoặc focus xem thông số (ví dụ `9.6 / 16 GB`). Offline hiển thị `—` cho số đo, không giả vờ tải bằng 0. Current run mở Run detail.
- Hover/focus vào Running của PC để xem Process, node đang chạy và Agent phụ trách.
- Settings gồm Providers & API (tên, API format, Base URL, request timeout), Models (Model ID, provider, max output, temperature), Roles và General (timeout Task, số dòng Logs mặc định). Model khai báo ở đây được chọn trong Agent. Không có Workspace hoặc lựa chọn múi giờ; Account để giai đoạn sau.
- Settings → Roles có New/Edit/Delete, tên, Duties và số Agent cùng dùng. Role trong Agent là select. Một Role dùng chung cho nhiều Agent; dữ liệu mẫu có PM và Nhân viên. Permissions nằm trong phần mở rộng để chuẩn bị cho tương lai, không chặn chạy hay tự tắt lịch ở prototype. PM của Project được chỉ định riêng, không suy ra bằng cách gõ tên Role.
- Role chưa dùng có thể xóa sau xác nhận; Role đang được Agent tham chiếu chuyển Archived, giữ liên kết cũ và không cho gán mới. Có Restore. Đổi tên Role cập nhật nhãn cho các Agent cùng dùng, không thay đổi Skills/model hoặc lịch sử sử dụng riêng.
- Provider có Test API giả lập: kiểm tra Base URL và yêu cầu khóa mẫu, hiện Testing rồi Success/Invalid key/Timeout theo Demo scenario. Kết quả trong bảng ghi Demo OK/Demo Error; sửa input sẽ hủy kết quả cũ. Không gọi mạng và không xác minh khóa thật.

## Tương tác mẫu

- Chuyển module bằng sidebar hoặc `Ctrl/Cmd + K`.
- Đầu sidebar chỉ giữ logo và Agent CF, vào thẳng Overview; không có khối chuyển công ty hoặc phụ đề.
- Chọn Project để xem danh sách Process, lịch và PC của riêng dự án đó.
- Projects có New project; trong dự án có Edit project và Delete. Form quản lý tên, mô tả và PM; target và thành viên quản lý trong các tab riêng.
- Danh sách Process có New process, Edit và Delete. Process mới là draft với sơ đồ mẫu, cần Publish trong sơ đồ trước khi Run hoặc bật Schedule. Metadata sửa từ danh sách; cấu hình node Robot sửa trong sơ đồ.
- Robots có New/Edit/Delete, New version và thống kê riêng từng version. Bảng chỉ hiển thị active version dạng chữ, không có dropdown. Đổi active version trong Edit rồi Save; tạo version mới không tự active. Active version làm mặc định khi thêm node mới, không đổi version đã gán trong Process. Bản mới chưa có dữ liệu; không gán Agent/PC trong catalog. Các con số trong bản mẫu không phải dữ liệu vận hành thật.
- Trong Process, kéo hoặc bấm Robot ở palette để thêm node, chọn version, Agent, PC và input JSON. Node mới nối tiếp chuỗi; sửa graph đã publish tạo draft. Publish không đổi graph của run cũ hoặc version Schedule đang dùng. Tool nội bộ vẫn ở Skills → Tools.
- Delete luôn có cảnh báo và xác nhận. Mục chưa có run được xóa cùng dữ liệu con; mục đã có run chuyển vào Archived, tắt lịch và giữ Runs/Logs. Có thể chuyển sang danh sách Archived để Restore; Restore không tự bật lại lịch. Không cho xóa/Archive khi còn run đang chạy hoặc đang hủy.
- Với Agent/Skill/Tool, Delete hiển thị nơi sử dụng. Mục có tham chiếu hoặc dữ liệu sử dụng token chuyển sang Archive, giữ ID và thông tin cũ của graph/run; lịch Process bị ảnh hưởng sẽ tắt và run mới bị chặn. Run đang chạy không bị hủy. Restore không tự bật lịch; mục chưa được dùng có thể xóa hẳn sau xác nhận. Sửa tên catalog không đổi nhãn snapshot trong Process đã publish.
- Lưu Schedule rồi bấm Start để bật lịch. Stop chỉ tắt lịch; run đang chạy vẫn tiếp tục.
- Run tạo lượt chạy mẫu thủ công, không thay đổi lịch. Input được kiểm tra JSON.
- Trong Runs, lọc Running, xem Details/Logs và Cancel run. Run chuyển qua Cancelling rồi Cancelled; hủy không tắt lịch.
- Runs gộp các trạng thái vào filter Status. Run detail mở gần toàn màn hình, flow gọn phía trên; bảng Logs chiếm phần lớn diện tích. Hover node xem Agent/PC; giờ Việt Nam mặc định, không kèm nhãn múi giờ.
- Runs có tìm Run ID, lọc Project/Process/Status và ngày Started từ–đến (mặc định 7 ngày gần nhất). Running gồm cả Cancelling, không có filter Cancelling riêng. Bảng có STT nối tiếp qua trang, tiến độ số node, Started/Ended/Duration, 25/50/100 dòng và Total số khớp/tổng run. Ended và Duration dùng timestamp mẫu; run thủ công ghi nhận lúc tạo/hủy trong phiên. Chưa có telemetry thực tế.
- Run detail mở khung lớn: hàng node nối theo thứ tự kèm trạng thái, bên dưới là bảng Logs với Time, Level, Node, Agent, Source và Message. Search kết hợp lọc Level/Node, chọn 25/50/100 dòng và Previous/Next; bấm node để lọc nhanh. Detailed log là dữ liệu mẫu tạo trong trình duyệt để review phân trang, chưa có streaming hoặc truy vấn backend.
- Kéo node trong Process; dây nối cập nhật theo vị trí. Bấm node để xem trách nhiệm Agent, Skill và Tool.
- Xem responsive navigation trên màn hình nhỏ.
- Disable PC ngừng giao việc mới và tắt lịch chỉ định PC đó, giữ run hiện tại. Enable không tự bật lại lịch. Remove bị chặn nếu PC còn run hoạt động; sau Remove vẫn giữ định danh trong lịch sử. Đổi tên chỉ đổi nhãn, không sửa tham chiếu lịch/run. Connect và số đo phần cứng đều là dữ liệu giả lập; chưa có bộ cài thật.

Tất cả dữ liệu và thao tác đều là dữ liệu mẫu trong trình duyệt. Refresh trang sẽ đưa prototype về trạng thái ban đầu.

Schedule chỉ tính và hiển thị thời điểm kế tiếp theo giờ Việt Nam; không có scheduler tự chạy thật. Các lượt chạy không gọi model/tool/robot, không phát sinh token thực tế. Chưa có upload/chạy artifact Robot, engine PM, editor dependency tùy ý hoặc bộ cài PC. Settings chỉ lưu trong phiên trình duyệt; API key bị bỏ khi Save, không có kho khóa hoặc kiểm tra kết nối thật.

## Kiểm tra giao diện

Cần Node.js 22+ và Edge/Chromium chạy với remote debugging trên localhost. Ví dụ PowerShell trên Windows:

```powershell
$previewProfile = Join-Path $env:TEMP 'agent-cf-browser-check'
Start-Process -FilePath 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' -ArgumentList @('--headless=new', '--remote-debugging-port=9335', "--user-data-dir=$previewProfile", 'about:blank') -WindowStyle Hidden
node demo/agent-cf-prototype/tests/smoke.cjs
```

Test mở và đóng tab riêng, kiểm tra navigation, Start/Stop, Schedule, input JSON, run thủ công, hủy run, kéo node và 40 tổ hợp trang/kích thước. Có thể đặt biến `CDP_URL` nếu dùng cổng khác. Prototype không có bước build/lint riêng; kiểm tra cú pháp JavaScript bằng `node --check demo/agent-cf-prototype/app.js`.
