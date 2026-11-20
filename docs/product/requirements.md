# Yêu cầu sản phẩm và giao diện Agent CF

> Status: Draft  
> Last updated: 2026-11-17  
> Owner: Product

## Mục đích

Tài liệu này là nguồn chuẩn cho yêu cầu và quy tắc nghiệp vụ của MVP Agent CF. Nó mô tả hành vi mục tiêu để kiểm chứng bằng prototype và triển khai sau này; không khẳng định các hành vi đã tồn tại trong repository.

Phạm vi sản phẩm và giới hạn nằm trong [Tầm nhìn sản phẩm](vision.md). Định nghĩa thuật ngữ nằm trong [Thuật ngữ](glossary.md).

Mốc đối chiếu giao diện: **2026-11-13**, [HTML prototype](../../demo/agent-cf-prototype/index.html). Phần [yêu cầu theo màn hình](#yêu-cầu-theo-màn-hình) ghi nhận các quyết định đã review để triển khai tiếp. Thiết kế nền ngày 2026-11-16 phục vụ hệ thống quản lý tổng và Process động; Skill 0–1–2 là bộ test, không giới hạn graph hoặc loại nghiệp vụ. Schema/mapping và snapshot tại [domain](../architecture/domain-model.md#định-nghĩa-process-động-và-snapshot), vòng đời/Runner tại [execution](../architecture/execution-model.md), HTTP tại [OpenAPI](../../openapi/openapi.yaml). Các mục MUST/SHOULD/OUT là yêu cầu cho sản phẩm thật, không phải báo cáo tính năng đã hoàn thành. Những phần prototype giả lập và thiết kế còn mở được phân biệt ở cuối tài liệu.

## Quy ước mức độ

- **MUST:** bắt buộc để MVP được chấp nhận.
- **SHOULD:** mong muốn nếu không làm tăng đáng kể phạm vi; có thể hoãn với lý do rõ ràng.
- **OUT:** không thuộc MVP.

## Tác nhân

- **Người thiết kế process:** tạo Project, Process, các bước và dependency.
- **Người vận hành:** khởi chạy, theo dõi và hủy ProcessRun.
- **Runner:** thành phần đáng tin cậy thực thi TaskRun đã đủ điều kiện.

Trong MVP, người thiết kế và người vận hành có thể là cùng một người. Đây là trách nhiệm nghiệp vụ, chưa phải vai trò phân quyền chính thức.

## Nhu cầu thực tế và phạm vi tích hợp

Người dùng muốn xây hệ thống thật, dùng HTML để hình dung trước khi triển khai. Use case đại diện là [sản xuất video YouTube](use-cases/youtube-video.md). Tool hiện đã có và thường được chạy bằng cách nạp input rồi lấy output. Hệ thống cần Agent điều khiển/giám sát tool, không mặc định viết lại tool hoặc thay Codex/Antigravity bằng một model API.

### Giữ quy trình và output trên PC

Web là nơi giao việc, cấu hình và theo dõi; CF Client thay người dùng điều khiển Codex, Antigravity và các tool trên PC. Quy trình của Skill giữ nguyên, bao gồm đọc tài nguyên, gọi tool, sửa file và tạo ảnh/file/thư mục thật. Không đổi quy trình thành chỉ trả nội dung chat để hệ thống tự dựng output thay runtime.

Output gốc phải nằm trên PC thực thi, đúng thư mục làm việc và quy ước của Skill, để các bước sau dùng trực tiếp. Web hiển thị trạng thái, log và tham chiếu PC/đường dẫn; bản sao hoặc preview trên Web là tùy chọn. Không yêu cầu mọi loại output phải upload hoặc hiển thị được trên Web để công nhận thành công.

Skill local cho nhập/dán đường dẫn tuyệt đối hoặc chọn file `.md` chính (thường là `SKILL.md`) và PC sở hữu file ngay trong form Thêm/Sửa Skill, kể cả tạo từ Process editor. Nút Chọn file duyệt thư mục qua Client của PC đã chọn; chỉ trả tên/đường dẫn, không upload hay lưu nội dung Markdown/ref lên Web. Runtime đọc file chính và tự đọc các ref tương đối tại thư mục Skill gốc. Không cần chọn các ref. Process node chọn cùng PC; thư mục làm việc tuyệt đối cấu hình một lần ở Project, không nhập tại node. Mỗi lần chạy gọi file gốc tại đường dẫn đã lưu; thiếu file/sai PC phải báo lỗi, không thay bằng hướng dẫn đã copy. Snapshot Run giữ tham chiếu nguồn đã dùng; bằng chứng Attempt ghi hash file thực tế. [ADR 0006](../architecture/decisions/0006-local-skill-paths-and-pc-outputs.md) quy định sự khác biệt với Skill nội dung/bundle; nút chọn file là bổ sung giao diện, không thay cơ chế chạy.

Các yêu cầu dưới đây là nhu cầu sản phẩm đã ghi nhận, được triển khai theo [các mốc](../development/implementation-plan.md); chưa phải khả năng đã có và không bắt buộc hoàn thành toàn bộ ở mốc thử kết nối đầu tiên:

- **CF Client:** thành phần cài trên PC nhận việc từ server, gọi Agent/tool, giữ output gốc tại PC và gửi log/tham chiếu output/trạng thái.
- **Agent runtime:** hỗ trợ tích hợp Codex/Google Antigravity theo adapter được kiểm chứng. Agent chọn model là chưa đủ; phải xác định runtime, ngữ cảnh/Skill, quyền và tool có thể gọi. Chưa có form runtime trong HTML, cần thiết kế khi tích hợp.
- **Xử lý ngoại lệ:** Agent được chẩn đoán và xử lý trong phạm vi cho phép, có giới hạn và lịch sử; không xử lý được hoặc vượt giới hạn phải báo người dùng với lỗi/phần đã hoàn thành. Không hứa tự xử lý mọi lỗi.
- **Can thiệp:** có thể chờ người dùng duyệt hoặc bổ sung hướng dẫn rồi tiếp tục; đây là nhu cầu thật, không còn loại khỏi định hướng sản phẩm chỉ vì MVP ban đầu chưa có.
- **Human/Continue:** nhiều Process có thể chờ xử lý. Process đã hoàn thành 3/5 node phải giữ ba kết quả đã đạt khi tạm dừng tại bước vướng; sau người dùng khắc phục/bổ sung hướng dẫn, Continue tiếp tục đúng bước. Không tự chạy lại các bước đã đạt hoặc gọi lại tool đang còn chạy. Yêu cầu can thiệp phải lưu được để người dùng tìm lại; màn Human tập trung chưa có trong HTML, cần thiết kế ở mốc tương ứng.
- **Làm lại một phần:** cần giữ phần đạt và tạo lịch sử riêng khi xử lý lại phần lỗi, tránh chạy lại cả video/batch; quy tắc retry/resume/version và trạng thái chưa chốt, cần thiết kế trước triển khai.
- **Tích hợp tool:** adapter phải mô tả cách gọi, input/output, lỗi, khả năng hủy và phụ thuộc phiên desktop. Tool lỗi hoặc trả file thiếu không tự được tính là kết quả đạt.

## Kịch bản MVP chính

1. Người dùng tạo một Project.
2. Người dùng tạo Process và chỉnh sửa cấu hình hiện tại.
3. Người dùng thêm các Task, chọn Agent và nối Dependency.
4. Hệ thống kiểm tra tính hợp lệ khi lưu cấu hình.
5. Người dùng chọn chủ đề/input và Chạy Process; Server tự chụp cấu hình bất biến.
6. Hệ thống tạo TaskRun, đưa các task đủ điều kiện cho Runner và cập nhật trạng thái.
7. Người dùng xem tiến độ, output hoặc lỗi và có thể yêu cầu hủy run đang hoạt động.

## Yêu cầu chức năng

### Project

#### REQ-PROJ-01 — Tạo project — MUST

Người dùng có thể tạo Project với tên và PM bắt buộc, mô tả tùy chọn. Team hiển thị tự động theo PM và phân công node; Targets được quản lý bên trong Project.

Tiêu chí nghiệm thu:

- Tên rỗng hoặc chỉ gồm khoảng trắng bị từ chối với lỗi tại trường dữ liệu.
- Project mới xuất hiện trong danh sách và có định danh ổn định.

#### REQ-PROJ-02 — Xem và cập nhật project — MUST

Người dùng có thể tìm trong danh sách, mở chi tiết và cập nhật tên, mô tả hoặc PM. Chi tiết có Processes, Team, Targets và Runs; quy tắc thành viên và nghiệm thu Target nằm trong yêu cầu theo màn hình.

#### REQ-PROJ-03 — Lưu lịch sử khi ngừng sử dụng project — SHOULD

Xóa Project là xóa vĩnh viễn cùng các Process con và lịch sử thuộc nó, kể cả đã có ProcessRun/version published. Chỉ chặn khi còn Run chưa kết thúc; người dùng phải dừng và chờ Run kết thúc trước. Ngừng hoạt động là hành động riêng giữ lịch sử. Quy tắc chi tiết nằm trong mục quản lý Project và Process bên dưới.

### Process và cấu hình chạy

#### REQ-PROC-01 — Tạo process — MUST

Người dùng có thể tạo Process trong một Project với tên bắt buộc và mô tả tùy chọn. Process mới có cấu hình để thêm các bước; không cần tạo phiên bản thủ công.

#### REQ-PROC-02 — Thiết kế task graph — MUST

Trong cấu hình Process, người dùng có thể thêm, sửa và xóa Task; khai báo Dependency giữa các task; và chọn Agent cho từng task.

Mỗi Task phải có tối thiểu:

- định danh ổn định trong version;
- tên;
- loại thực thi Agent hoặc Robot và cấu hình tương ứng;
- một Agent đang hoạt động, chọn trực tiếp từ danh mục và chịu trách nhiệm output;
- với Robot: RobotVersion, PC thực thi và input hợp lệ; với Agent task: hướng dẫn và Skill/Tool cần dùng.

#### REQ-PROC-03 — Kiểm tra cấu hình trước khi lưu và chạy — MUST

Hệ thống chỉ cho lưu/chạy cấu hình hợp lệ khi:

- có ít nhất một Task;
- mọi Task có cấu hình bắt buộc;
- mọi Agent được tham chiếu tồn tại và đang hoạt động;
- mọi Dependency tham chiếu Task trong cùng version;
- đồ thị Dependency không có chu trình;
- cấu hình tool của Task không vượt quá tool Agent được phép sử dụng.
- node Robot có version hợp lệ và cấu hình PC/input bắt buộc; Agent được giao chọn trực tiếp từ danh mục đang hoạt động.

Lỗi phải chỉ ra Task hoặc Dependency liên quan khi có thể.

Đây là validation mục tiêu của sản phẩm thật. Prototype chỉ hỗ trợ một phần editor/validation, không phải engine kiểm tra đầy đủ.

#### REQ-PROC-04 — Snapshot lần chạy là bất biến — MUST

Tạo Run tự chụp cấu hình bất biến trong cùng transaction. Sửa Process/Skill chỉ tác động lần chạy mới, không sửa snapshot của Run đang chạy hoặc đã kết thúc.

#### REQ-PROC-05 — Chỉnh sửa cấu hình hiện tại — SHOULD

Người dùng mở Process để sửa trực tiếp và Lưu. Không có Draft/Version/Publish thủ công. Token cấu hình ngăn ghi đè thay đổi đồng thời.

#### REQ-PROC-06 — Đặt lịch chạy cơ bản — MUST

Người dùng có thể bật hoặc tắt lịch chạy theo thời gian cho một Process. Lịch phải hiển thị lần chạy dự kiến kế tiếp và cho phép chọn một Runner cụ thể hoặc để hệ thống tự chọn Runner phù hợp.

- Lịch trên Web lấy cấu hình Process/Skill đã lưu tại thời điểm đến hạn và tạo snapshot riêng cho Run. API ghim snapshot cũ được giữ tương thích.
- Nếu Runner được chỉ định đang offline hoặc không còn quyền, run không được giao sang máy khác trừ khi Schedule dùng chế độ tự động chọn.
- Lịch phức tạp theo calendar, event trigger và webhook nằm ngoài MVP.

Start bật lịch và chờ mốc kế tiếp; Save schedule không tự bật lịch. Stop chỉ tắt lịch tương lai, không hủy run đang chạy. Manual Run và Cancel run là các thao tác riêng. Giờ Việt Nam là mặc định, không có chọn múi giờ trong UI.

### Agent và tool

#### REQ-AGENT-01 — Khai báo agent — MUST

Người dùng tạo/cập nhật **Agent điều phối** với tên, Role, hướng dẫn giao việc/kiểm tra, **Model API** từ Providers & Models API, Skills và quyền Tool. Agent API thay người có hai trách nhiệm: giao nhiệm vụ cho Codex/Antigravity; kiểm tra tiến độ/hoàn thành, lỗi và chất lượng kết quả để duyệt hoặc yêu cầu làm tiếp/sửa. Codex/Antigravity là **Công cụ AI thực thi** trực tiếp làm việc trên PC, không phải Agent API đó. Một Role dùng chung cho nhiều Agent; PM gán riêng theo Project. Theo dõi token theo Agent, không có Cost/Budget; không coi token CLI quy về Agent là token API đã gọi.

Các trường cấu hình provider/model đã có trong định hướng UI; giao thức adapter, lưu credential, ghi nhận token thực tế và quyền thực thi chưa được chốt. Role Permissions là chuẩn bị cho giai đoạn sau, không phải cơ chế đang bảo vệ runtime.

#### REQ-AGENT-02 — Không dùng agent archived cho run mới — MUST

Agent đã archived trong dữ liệu cũ không được gán mới. Web không cung cấp Archive/Restore hay công tắc Inactive cho Agent; Agent mới không dùng đến được để nguyên. Trạng thái/API cũ được giữ cho tương thích và lịch sử.

#### REQ-TOOL-01 — Kiểm tra quyền tool tại nơi thực thi — MUST

Runner chỉ thực thi Tool nằm trong quyền hiệu lực của Agent và Task. UI có thể hỗ trợ chọn Tool nhưng không phải điểm kiểm tra quyền duy nhất.

#### REQ-TOOL-02 — Bảo vệ dữ liệu nhạy cảm — MUST

Secret không được hiển thị lại dưới dạng rõ hoặc ghi vào log, output và AuditEvent. Cơ chế quản lý secret cụ thể cần quyết định kiến trúc riêng trước khi triển khai.

### Cấu hình node dùng runtime local

Cấu hình Process lưu trực tiếp; Skill dùng nguồn đã lưu mới nhất. Server tự chụp Agent/runtime/model/Skill khi tạo Run, không có bước Publish hoặc chọn version. Với các Skill local cùng PC/root, form mặc định chọn hoặc dán đường dẫn thư mục chủ đề đã có, kèm yêu cầu riêng tùy chọn; mọi bước nhận cùng ngữ cảnh. Process khác giữ input JSON nâng cao. Chủ đề không giới hạn loại nghiệp vụ hoặc tên Skill, không hard-code graph trong engine.

- Form node có Tên bước, Agent phụ trách, Skill, Runtime (Codex/Antigravity), Model, **Nhiệm vụ bổ sung (không bắt buộc)**, PC; không có ô thư mục tại node. Mặc định chạy Skill đã chọn cho chủ đề của lần chạy, không bắt lặp tên chủ đề hoặc chép hướng dẫn Skill. Nhiệm vụ bổ sung truyền nguyên văn cùng hướng dẫn Agent/Skill, không tự đánh dấu thành công dựa trên chữ `done`.
- Agent phụ trách chọn trực tiếp từ toàn bộ danh mục Agent active, không giới hạn PM hoặc Team có sẵn. Không có Quản lý Team trong form node. Sau khi lưu định nghĩa Process, tab Team tự tổng hợp phân công; chỉ mở form hoặc đổi graph chưa lưu không thay dữ liệu Team trên Server.
- **Agent điều phối** chọn riêng Model API. **Công cụ AI thực thi** và **Model thực thi** của node lấy từ catalog CLI độc lập trong Settings → Công cụ AI trên PC. Chọn Codex chỉ hiện model Codex đã bật; chọn Antigravity chỉ hiện model Antigravity đã bật. Đổi Agent không đổi công cụ/model CLI. Không lấy model API, model chưa phân loại hoặc suy Runtime từ tên để điền lựa chọn. Server kiểm đúng công cụ, identifier và trạng thái bật khi lưu/chạy; tắt model CLI chặn Run mới liên quan, giữ lịch sử và không hủy run hiện có.
- Task key tự sinh, ổn định khi đổi tên/sửa node và không nằm trong form thường dùng. Timeout nằm trong Cấu hình nâng cao; ba trường mapping/input-output schema chưa hoàn thiện bị ẩn khỏi form node, giữ dữ liệu cũ khi sửa. Skill local chọn sẵn PC từ nguồn Skill đã lưu mới nhất. Project cấu hình root làm việc một lần cho Skill local. Luồng cấu hình hiện tại lấy root Project, không dùng override thư mục cũ của node; PC mặc định theo nguồn Skill. Mỗi Run tự chụp root/PC. Snapshot và API lifecycle cũ giữ nguyên.
- Lần chạy theo chủ đề: `topic_directory` tuyệt đối và thuộc root đã ghim; các Skill local cần cùng PC/root. Server dẫn xuất `topic` từ tên thư mục, truyền cùng `request` tới mọi node. Client kiểm thư mục thực tế tồn tại và resolve bên trong root trước khi spawn, không tự tạo folder. Cwd vẫn là root Project; Skill dùng thư mục chủ đề đã có và file của các bước trước theo quy trình gốc. Output trên Web ghi root/chủ đề và đường dẫn file thật. Việc chọn folder chỉ đọc metadata qua Client, không gọi model hoặc upload nội dung.
- Chọn trên PC chỉ bật khi heartbeat còn mới (`display_status` online/busy), không suy từ raw status còn lưu. PC chưa kết nối thì báo ngay, vẫn cho dán path; không ngồi chờ browse hết hạn. Nguồn Skill trỏ PC đã xóa phải cập nhật nguồn và Lưu và cấu hình node phù hợp, không tự chuyển ownership sang một PC khác.
- Danh mục model tách tên hiển thị, ID runtime và trạng thái khả dụng theo máy/tài khoản. Giữ các lựa chọn dự kiến kể cả khi tài khoản hiện tại chưa dùng được; làm mới khả dụng khi đổi tài khoản. Trước khi chạy phải có ID hợp lệ và kiểm tra quyền; không tự thay model khác hoặc coi model xuất hiện trong danh sách là đã chạy được.
- Mốc tích hợp đầu tiên: người dùng nhập chủ đề trên Web, chọn cấu hình đã được kiểm chứng và chạy riêng Skill 0 qua Server → CF Client → Codex; xem lại cốt truyện, log và lịch sử đã lưu. Mốc này chưa có Agent duyệt, Skill 1/2 hoặc editor; không đồng nghĩa hoàn tất luồng nghiệp vụ hay MVP tổng thể.
- Luồng nghiệp vụ đầy đủ của ba Skill: người dùng nhập chủ đề trên Web; Agent thay người giao việc, đánh giá, duyệt/yêu cầu sửa; runtime local thực thi Skill 0 → 1 → 2. Skill 1 giữ checkpoint từng Part để Agent duyệt. Tiêu chí duyệt và giới hạn sửa cần được thiết kế trước khi triển khai; vượt giới hạn thì yêu cầu người dùng can thiệp. Từng adapter Codex/Antigravity chỉ được đưa vào thực thi khi đã kiểm chứng; không tự đổi runtime của người dùng.
- Nhánh tự tìm chủ đề để sau; khi triển khai, người dùng duyệt chủ đề trước khi vào luồng tạo nội dung. Chạy song song chưa thuộc mốc tích hợp đầu tiên hoặc luồng ba Skill cố định.
- Kết quả kiểm chứng runtime và danh mục model tham chiếu nằm tại [báo cáo runtime local](../reports/local-runtime-check.md). Yêu cầu này không tự coi mọi runtime/model là đã tích hợp thành công.

### Runner Client

#### REQ-RUNNER-01 — Ghép nối Runner Client — MUST

Người vận hành có thể đăng ký Runner Client cài trên máy tính bằng thông tin ghép nối có thời hạn và chỉ dùng một lần. Runner Client phải chủ động kết nối outbound tới control plane; MVP không yêu cầu server mở kết nối trực tiếp vào PC.

#### REQ-RUNNER-02 — Theo dõi trạng thái Runner — MUST

Người vận hành có thể xem tên Runner, Machine và hệ điều hành, phiên bản client, trạng thái `online`, `offline`, `busy` hoặc `disabled`, heartbeat gần nhất và TaskRun hiện tại nếu có.

#### REQ-RUNNER-03 — Khai báo năng lực và quyền — MUST

Runner chỉ được nhận TaskRun phù hợp với hệ điều hành, năng lực và Tool đã được cấp. Thông tin do Runner Client gửi phải được xác thực; Runner không được tự mở rộng quyền bằng cách chỉ khai báo thêm năng lực.

#### REQ-RUNNER-04 — Thu hồi Runner — MUST

Người vận hành có thể vô hiệu hóa hoặc thu hồi credential của Runner. Runner đã bị thu hồi không được nhận task mới; lịch sử TaskRun từng thực thi trên Runner đó phải được giữ lại.

#### REQ-RUNNER-05 — Mất kết nối — MUST

Khi Runner quá hạn heartbeat, hệ thống đánh dấu Runner offline và không giao task mới. TaskRun đang chạy trên Runner đó không được tự động chạy lại cho tới khi policy recovery xác định kết quả và rủi ro side effect.

### Khởi chạy và theo dõi

#### REQ-RUN-01 — Khởi chạy thủ công hoặc theo lịch — MUST

Người vận hành có thể tạo ProcessRun thủ công từ cấu hình Process đã lưu và cung cấp input. Hệ thống cũng có thể tạo ProcessRun khi Schedule đến hạn. Mọi trường hợp phải lưu nguồn kích hoạt và tham chiếu chính xác tới snapshot tự chụp cho lần chạy.

#### REQ-RUN-02 — Tạo lịch sử task run — MUST

Mỗi Task trong version tạo đúng một TaskRun thuộc ProcessRun trong MVP. TaskRun tham chiếu Task của chính version đó và không ghi trạng thái ngược vào định nghĩa Task.

#### REQ-RUN-03 — Tôn trọng dependency — MUST

TaskRun chỉ đủ điều kiện thực thi khi mọi TaskRun nguồn đã thành công. TaskRun chỉ được giao cho Runner online, được xác thực và có năng lực phù hợp. Các TaskRun không phụ thuộc nhau có thể chạy đồng thời nếu tài nguyên cho phép; hệ thống không cam kết thời điểm bắt đầu tuyệt đối.

#### REQ-RUN-04 — Quan sát trạng thái — MUST

Người vận hành có thể xem:

- trạng thái và thời điểm chính của ProcessRun;
- version và input đã dùng;
- trạng thái của từng TaskRun;
- output an toàn hoặc lỗi có ngữ cảnh;
- TaskRun nào chưa chạy do dependency thất bại hoặc run bị hủy.

Prototype mô phỏng cập nhật trực tiếp; thiết kế baseline dùng poll/cursor và WebSocket hint tùy chọn, chưa triển khai.

#### REQ-RUN-05 — Kết quả process — MUST

ProcessRun thành công khi mọi TaskRun hoàn thành thành công. Output của MVP là tập output của các Task cuối đồ thị; quy tắc ánh xạ output tùy chỉnh nằm ngoài MVP.

#### REQ-RUN-06 — Xử lý thất bại — MUST

Khi một TaskRun thất bại:

- lỗi được lưu với ngữ cảnh an toàn;
- task phụ thuộc trực tiếp hoặc gián tiếp không được chạy;
- ProcessRun kết thúc thất bại sau khi các task đang chạy độc lập đã đạt trạng thái kết thúc;
- side effect đã hoàn tất không được tự động hoàn tác.

#### REQ-RUN-07 — Hủy run — MUST

Người vận hành có thể yêu cầu hủy ProcessRun đang chờ hoặc đang chạy. Hệ thống ngăn task mới bắt đầu, yêu cầu dừng task đang chạy theo cơ chế best effort và giữ lại toàn bộ lịch sử đã có.

#### REQ-RUN-08 — Giới hạn thời gian — MUST

Mọi lần thực thi task phải có giới hạn thời gian hữu hạn do nền tảng hoặc cấu hình task cung cấp. Policy mặc định và deadline/lease đã chốt tại execution model; phải kiểm chứng dừng tiến trình trước khi ghi timeout terminal.

#### REQ-RUN-09 — Retry tự động — OUT

MVP không tự động retry TaskRun. Người dùng có thể tạo ProcessRun mới sau khi sửa nguyên nhân lỗi. Mô hình dữ liệu tương lai không được ghi đè lịch sử Attempt nếu retry được bổ sung.

### Audit và lịch sử

#### REQ-AUDIT-01 — Ghi nhận hành động quan trọng — MUST

Hệ thống lưu AuditEvent tối thiểu cho lưu cấu hình, tạo snapshot/bắt đầu Run, yêu cầu hủy và kết quả cuối của run. Mỗi event cần có thời điểm, loại hành động, tài nguyên, chủ thể thực hiện và kết quả.

#### REQ-AUDIT-02 — Không sửa lịch sử run — MUST

Không cho phép sửa input, output, lỗi hoặc trạng thái lịch sử để làm như một run đã diễn ra khác đi. Xóa Project/Process có xác nhận được phép xóa lịch sử thuộc nó theo quy tắc Delete bên dưới; giữ audit riêng ghi nhận thao tác xóa. Việc che dữ liệu nhạy cảm theo chính sách lưu giữ sẽ cần quy tắc riêng.

## Yêu cầu chất lượng

### REQ-QUAL-01 — Lỗi có thể hành động — MUST

Validation và lỗi thực thi phải có mã hoặc loại lỗi ổn định, thông điệp có ngữ cảnh và không làm lộ secret.

### REQ-QUAL-02 — Không thực thi trùng ngoài ý muốn — MUST

Hệ thống không được giao cùng một TaskRun cho nhiều lần thực thi đồng thời ngoài chủ ý. Cơ chế idempotency và lease cụ thể thuộc quyết định kiến trúc.

### REQ-QUAL-03 — Truy vết xuyên suốt — MUST

Từ ProcessRun phải truy được ProcessVersion và mọi TaskRun; từ TaskRun phải truy được Task và thông tin thực thi liên quan.

### REQ-QUAL-04 — Trạng thái nhất quán — MUST

Backend/domain là nguồn chuẩn của trạng thái. Giao diện không được tự suy diễn một trạng thái nghiệp vụ khác với [Mô hình thực thi](../architecture/execution-model.md).

## Ngoài phạm vi

Các khả năng sau vẫn là `OUT` đối với MVP ban đầu: lịch calendar phức tạp và event/webhook trigger; condition và loop tổng quát; process lồng nhau; retry tự động tổng quát; resume từ checkpoint tùy ý; phân quyền người dùng chi tiết; nhiều workspace; multi-region runner; marketplace; báo cáo hiệu suất và SLA nâng cao.

Chờ người dùng duyệt, Agent xử lý lỗi có giới hạn và làm lại phần lỗi đã được ghi nhận là nhu cầu sản phẩm. Chúng được thiết kế/kiểm chứng sau kết nối cốt lõi, không được coi là đã có trong state machine MVP sơ bộ hoặc đồng nhất với retry tự động tổng quát.

## Tiêu chí chấp nhận MVP tổng thể

Một bản triển khai MVP chỉ được chấp nhận khi có test hoặc kịch bản kiểm chứng cho:

- lưu và chạy thành công một Process nhiều bước;
- từ chối process có chu trình hoặc thiếu cấu hình;
- task độc lập có thể được lập lịch mà không vi phạm dependency;
- task lỗi làm run thất bại và chặn downstream task;
- timeout làm task và run thất bại với lỗi có ngữ cảnh;
- hủy run ngăn task mới bắt đầu và giữ lịch sử;
- sửa cấu hình không làm thay đổi run đang hoặc đã chạy;
- Runner từ chối tool không được phép;
- Runner offline hoặc đã bị thu hồi không nhận task mới;
- lịch sử và log không làm lộ secret trong dữ liệu thử nghiệm.

## Yêu cầu theo màn hình

### Tên hiển thị và định danh kỹ thuật

Bảng, form và tiêu đề thường dùng hiển thị tên Project/Process/Skill/Agent/PC, phiên bản Robot và ngữ cảnh như chủ đề/thời gian để phân biệt các lần chạy. Không hiển thị UUID nội bộ làm tên hoặc fallback khi thiếu dữ liệu; dùng nhãn thiếu tên rõ ràng. ID vẫn dùng nguyên vẹn trong dữ liệu, URL, request và tìm kiếm.

Các ID cần tra lỗi cùng hash/output JSON nằm trong **Chi tiết kỹ thuật**, mặc định đóng và có thao tác sao chép. Mã ghép nối PC, Model ID dùng để cấu hình runtime và đường dẫn file/thư mục là thông tin thao tác nên vẫn hiển thị ở nơi cần dùng. Nhật ký lỗi và form chỉnh mapping có thể chứa định danh vì phục vụ cấu hình/chẩn đoán, không được tự xóa ID khỏi nội dung nghiệp vụ hoặc thông báo lỗi.

Các nội dung dưới đây là mốc UI hiện tại để triển khai tiếp; prototype chỉ mô phỏng trong trình duyệt, chưa triển khai backend.

### Điều hướng và cách trình bày

| Màn | Nội dung chính |
|---|---|
| Overview | Lỗi chưa xử lý, tiến độ Project, token Agent |
| Projects | Danh sách dự án; mở Project để quản lý Processes, Team, Targets và Runs |
| Runs | Theo dõi lần chạy toàn công ty, lọc, phân trang và mở Logs |
| Agents | Nhân viên Agent, Role, model, Skills, chất lượng và Tokens |
| Skills | Skill có hướng dẫn/tiêu chuẩn output; Tools nội bộ trong tab riêng |
| Robots | Chương trình độc lập, version và tỷ lệ thành công theo version |
| PC | Máy thực thi, trạng thái, tải và node đang chạy |
| Settings | Providers & API, Models, Roles, General |

- Sidebar chỉ có logo + Agent CF ở đầu rồi vào Overview; không có phụ đề Control Center, khối Company/Workspace hoặc nhãn Tổng quan lặp lại. Các nhóm menu còn lại giữ theo prototype.
- Nhãn ngắn, chữ dễ đọc, khoảng cách thoáng. Không thêm mô tả lặp lại tên màn/tab. Nội dung khó hiểu dùng trợ giúp hover/focus khi cần. Màu trạng thái phải kèm nhãn, không chỉ dựa vào màu.
- Mọi thao tác xóa bị chặn phải thông báo tiếng Việt, nêu tên mục đang xóa, loại và tên dữ liệu liên quan cùng cách xử lý. Không dùng ID kỹ thuật thay cho tên hoặc trả nguyên lỗi SQL/JSON cho người dùng. Tham chiếu Process cần ngữ cảnh Project/bước hoặc version; Run cần Process/Project, thời điểm giờ Việt Nam và trạng thái để tìm trong Runs. Danh sách dài được giới hạn nhưng phải ghi số mục còn lại. Giữ nguyên ràng buộc xóa và không tự xóa dữ liệu liên quan để bỏ chặn.
- Sidebar dùng nhận diện CF phẳng và wordmark Agent CF dạng vector, nền trung tính và điểm nhấn tím tiết chế; icon nét đồng nhất, phân biệt được các chức năng. Hover/nhấn phản hồi bằng màu trong khoảng 140–180 ms (nhấn có thể nhanh hơn), không dịch chuyển chữ/icon; mục hiện tại có nền và độ đậm riêng. Có focus bàn phím rõ, giữ menu mobile và tắt chuyển động khi người dùng chọn giảm chuyển động. Tên menu, route và chức năng giữ nguyên.

### Luồng Project và Process

- Process được quản lý bên trong Project, không có menu Processes độc lập. Tool nội bộ nằm trong Skills → Tools; Robots là danh mục chương trình độc lập.
- Project hiển thị mục tiêu tuần/tháng, PM và tiến độ. Danh sách Process có lịch, lần chạy kế tiếp và lần chạy gần nhất; không dùng một cột PC chung để đại diện các node Robot.
- Process mở sơ đồ node có dây nối; mỗi Task có Agent chịu trách nhiệm output, kể cả khi dùng Skill hoặc Tool. Skill có hướng dẫn và tiêu chuẩn output; một Skill có thể dùng chung cho nhiều Agent.
- Schedule cấu hình tần suất, giờ Việt Nam mặc định, cấu hình Process hiện tại và PC cụ thể hoặc Auto. Lưu một lịch mới không tự bật lịch: người dùng bấm Start. Stop chỉ ngừng các lần kích hoạt theo lịch tiếp theo, không hủy run đang chạy. Chạy Manual là thao tác riêng, không bật lịch.
### Runs và Logs

- Runs hiển thị cả run đang chạy và lịch sử, có chi tiết Task, output, Logs và Cancel run. Hủy run không làm tắt lịch của Process.
- Runs dùng một bộ lọc Status cho toàn bộ danh sách, không tách tab theo trạng thái. Run detail ưu tiên diện tích cho Logs; flow phía trên gọn với tên node và trạng thái, hover xem Agent/PC. Giờ Việt Nam là mặc định, không lặp nhãn múi giờ trên giao diện.
- Status có Running, Succeeded, Failed và Cancelled; Running gồm queued/running/reconciling/cancelling của thiết kế engine. Dòng hiển thị trạng thái cụ thể; prototype trước đây chỉ mô phỏng Running/Cancelling. Bộ lọc kết hợp Run ID, Project, Process và khoảng ngày Started (bao gồm cả hai đầu), mặc định 7 ngày gần nhất. Chọn Project giới hạn Process tương ứng, đổi Project đặt lại Process.
- Bảng Runs có STT liên tục qua trang, Run/Process, Project, Status, tiến độ số node hoàn thành/tổng node (hover xem node hiện tại và Agent), Started, Ended, Duration và Actions. Ended trống khi đang chạy; Duration cập nhật đến khi kết thúc, thiếu dữ liệu hiển thị `—`. Bảng sắp Started mới nhất trước, có 25/50/100 dòng, Previous/Next và Total số khớp bộ lọc kèm tổng toàn bộ run. Prototype sử dụng timestamp mẫu; run tạo/hủy thủ công ghi timestamp trong phiên, chưa có execution telemetry/backend.
- Run detail dùng khung lớn: hàng node nối theo thứ tự có trạng thái và bảng Logs bên dưới. Logs có thời điểm, level, node, agent, source và message; hỗ trợ search kết hợp bộ lọc level/node, chọn số dòng và phân trang. Node phụ thuộc task thất bại hiển thị skipped. Contract baseline dùng query cursor/poll; WebSocket chỉ thông báo thay đổi. Backend và streaming chưa triển khai; prototype chỉ mô phỏng.
### Overview và theo dõi Agent

- Overview chỉ tập trung vào khối lỗi nổi bật màu đỏ ở đầu trang, bảng tiến độ Projects và bảng token Agents phía dưới; không có các thẻ chỉ số tổng hợp hoặc bảng Runs riêng. Lỗi mở được chi tiết ngay từ Overview. Màu kèm nhãn: đỏ cho lỗi, xanh dương cho running, xanh lá cho thành công và xám cho tắt/hủy.
- Toàn bộ giao diện chỉ theo dõi một tổng Tokens cho mỗi Agent. Bảng token Overview xếp từ cao xuống thấp, có tổng tháng; không có Cost, Budget, giá tiền hoặc cảnh báo tiền. Chưa đặt ngưỡng cảnh báo token. Dữ liệu token là số liệu mẫu, chưa nối thống kê thực tế.
- Khối đỏ đầu Overview chỉ có lỗi run chưa được đánh dấu xử lý. Trạng thái xử lý cảnh báo lưu riêng, không sửa status/input/output/logs của run; có thể mở lại cảnh báo từ Run detail. Project không tiếp tục báo lỗi đã xử lý như việc đang chờ xử lý, nhưng Last run và lịch sử vẫn giữ Failed.
- Running trên Overview mở tab Runs của đúng Project với lọc Running, gồm cả cancelling. Bấm Agent mở số token tháng chính xác, model và thao tác Edit agent.
- Overview dùng cùng hàm chọn Target theo kỳ và tiến độ với Projects. Chưa có target hiện tại hiển thị “—”, không hiện 0/0 hay tự kết luận On track. Bỏ mô tả lặp.
- Agents hiển thị model, chất lượng và token để đánh giá theo vai trò. Project có target tuần/tháng. PM theo dõi, review và báo cáo; cơ chế PM thực thi và công thức xếp hạng chưa được chốt.

### Quản lý danh mục và chi tiết màn

#### Quản lý Project và Process qua giao diện

- Bảng Projects gồm Project, Mô tả, PM, Trạng thái và cột thao tác gọn. Mô tả là cột riêng, tối đa hai dòng trong bảng; có thể xem đầy đủ khi mở Project. Tìm kiếm theo tên, mô tả hoặc PM. Bộ lọc có Tất cả, Đang hoạt động và Không hoạt động; mặc định Đang hoạt động, kết hợp với tìm kiếm.
- Trạng thái Project trên Web chỉ dùng **Đang hoạt động** (xanh lá) và **Không hoạt động** (đỏ), kèm chữ/chấm màu và nền nhạt. Đây là nhãn hiển thị của `active`/`archived`, không thêm trạng thái domain mới.
- Chi tiết Project đặt liên kết **← Projects** bên trái, cùng dòng mô tả/PM ngay dưới tiêu đề, không tạo hàng điều hướng riêng. Menu thao tác vẫn bên phải tiêu đề.
- Thao tác của Project gom trong menu **⋯**: Sửa, Nhân bản, Ngừng hoạt động hoặc Kích hoạt lại, Xóa. Xóa dùng màu đỏ và được tách với nhóm chỉnh sửa. Menu dùng được bằng bàn phím, đóng bằng Escape/click ngoài và không bị cắt bởi khối bảng cuộn ngang.
- Ngừng hoạt động, Kích hoạt lại và Xóa đều có xác nhận nêu tên Project và ảnh hưởng; nút xác nhận ghi đúng tên hành động. Ngừng hoạt động giữ dữ liệu/lịch sử và tắt lịch; Kích hoạt lại không tự bật lịch. Sửa mở form trực tiếp; Nhân bản mở form đặt tên trước khi tạo.
- Thao tác Xóa/Ngừng hoạt động/Kích hoạt lại trong Projects báo kết quả bằng thông báo góc trên bên phải, tự đóng sau 6 giây và có nút đóng. Xóa thành công báo xanh và mục biến mất khỏi danh sách. Lỗi API báo đỏ và giữ hộp xác nhận để người dùng sửa/thử lại. Không âm thầm chuyển sang Không hoạt động khi bấm Xóa. Nhân bản thành công cũng dùng thông báo này.
- Nhân bản Project chép toàn bộ cấu hình, PM/Team, các Process và version, Targets **giữ nguyên số liệu hiện tại**, cùng cấu hình Schedule. Bản sao giữ trạng thái cấu hình của nguồn, có ID Project/Process/version/Target/Schedule riêng; lịch được ghim lại đúng version của bản sao và luôn tắt, không có next/last run. Không chép Run, TaskRun, Attempt, Logs, artifact hoặc tick; không khởi chạy gì khi nhân bản. Agent/Skill/Robot/PC thuộc danh mục dùng chung vẫn được tham chiếu, không nhân đôi danh mục toàn cục. Nhân bản có tính nguyên tử, audit nguồn/bản sao và chống lặp khi gửi lại cùng Idempotency-Key; đổi tên với cùng key bị từ chối.
- Có New/Edit/Delete cho Project và Process. Tên bắt buộc và không được chỉ có khoảng trắng. Form Project có tên, mô tả và PM; Team chỉ hiển thị, Targets có phần quản lý riêng. Process được tạo trong Project, thêm bước rồi Lưu để chạy.
- Edit metadata tên/mô tả không thay đổi định nghĩa đã publish. Thay đổi hành vi Task lưu trực tiếp vào cấu hình hiện tại; các snapshot của Run cũ không đổi.
- Delete phải có cảnh báo xóa vĩnh viễn và bước xác nhận. Xóa Project cùng toàn bộ Process/version, Task/Dependency, lịch/tick, Run/TaskRun/Attempt, quyền thực thi, quyết định review/human, usage, Logs/events và artifact thuộc nó trên Server, dù đã published/có lịch sử. Xóa Process áp dụng cho riêng Process đó. Không tự xóa Workspace, PC, Skill, Agent, Robot, Tool dùng chung hoặc file nguồn/output trên PC. Gỡ liên kết Skill với Project; giữ các liên kết Project khác, không tự chuyển Skill thành Global nếu mất liên kết cuối cùng. Giữ một audit ghi nhận thao tác xóa; các dữ liệu/lịch sử của Project khác không thay đổi.
- Không xóa khi còn bất kỳ Run chưa terminal (queued/running/reconciling/cancelling), hoặc thực thi chưa xác nhận dừng. Báo rõ cần dừng Run và chờ kết thúc, không tự hủy. Ngừng hoạt động/Kích hoạt lại vẫn là chức năng riêng giữ lịch sử, ngừng hoạt động tắt các lịch liên quan.
- Archived bị ẩn khỏi danh sách active, không được tạo run hoặc bật lịch; vẫn xem được lịch sử. Restore từ danh sách Archived không tự bật lại Schedule.

#### Quản lý Agents, Skills và Tools qua giao diện

- Giao diện Skills, Tools, Agents, Robots, Roles và Process không có thao tác hoặc bộ lọc Archive/Restore. Mục tạo ra nhưng chưa cần dùng được để nguyên; không cần lưu trữ thủ công. Riêng **Project** giữ nguyên Ngừng hoạt động/Kích hoạt lại và bộ lọc Đang hoạt động/Không hoạt động. Enable/Disable Provider/Model, Start/Stop Schedule và Cancel Run không phải thao tác Archive, tiếp tục giữ nguyên.
- Trạng thái archived và API cũ được giữ cho tương thích/lịch sử, không tạo điều khiển tương ứng trên Web. Dữ liệu đã archived từ trước không tự khôi phục hoặc xóa; danh sách thao tác thường dùng chỉ hiện mục chưa archived. Quy tắc Delete/bảo vệ phiên bản và lịch sử không thay đổi bởi việc bỏ nút.

- Skill không có nhóm riêng. Khi tạo/sửa, chọn nhiều Project hiện có hoặc Global bằng ô tích; bắt buộc ít nhất một Project hoặc Global. Global loại trừ các Project cụ thể và dùng được cho mọi Project. Một Skill gán nhiều Project vẫn là cùng một Skill/version, không sao chép theo Project.
- Bảng Skills có cột Project và bộ lọc theo Project/Global. Lọc một Project bao gồm Skill của Project đó và Global. Process editor chỉ cho chọn Skill khả dụng của Project hiện tại; tạo Skill từ editor chọn sẵn Project đó. Agent vẫn là catalog dùng chung, nhưng việc Agent được gán Skill không cho phép vượt phạm vi Project khi lưu hoặc chạy Process.
- Bảng Skills không có cột Version hoặc nút Versions/Publish. Lưu nguồn Skill xong dùng ngay trong Process; chỉ Robot giữ danh sách phiên bản.
- Backend kiểm scope khi lưu và mỗi Run mới. Thu hẹp scope không sửa snapshot hoặc Run/lịch sử đã có; Process dùng Skill ngoài scope cần cập nhật cấu hình trước lần chạy mới. Skill cũ trước migration được giữ Global. Khi nhân bản Project, mở rộng liên kết Skill riêng của nguồn sang bản sao, giữ cùng ID Skill và version.

- Mỗi danh mục có New/Edit/Delete. Agent gồm tên, vai trò, hướng dẫn, model, Skill và quyền Tool; không cấu hình ngân sách tiền. Skill gồm hướng dẫn, tiêu chuẩn output và Tool; Tool có tên, mô tả và loại.
- Tên bắt buộc, không chỉ có khoảng trắng và không trùng trong cùng danh mục. Agent không được chọn Skill yêu cầu Tool ngoài Allowed tools. Model lấy từ danh mục Models trong Settings; các giá trị và thống kê hiện chỉ minh họa, chưa kết nối provider hoặc credential thật.
- ID catalog ổn định khi đổi tên; Process đã publish giữ cấu hình/nhãn snapshot. Sửa Skill cập nhật nguồn hiện tại, không ghi đè snapshot của Run cũ.
- Delete cần xác nhận và kiểm tra tham chiếu tại Server. Skill/Agent chỉ bị chặn xóa khi còn được node trong Process sử dụng (cấu hình hiện tại hoặc snapshot của Run chưa kết thúc, Project đang hoặc không hoạt động; dữ liệu chưa chuyển đổi vẫn kiểm tham chiếu legacy). Khi không còn Process tham chiếu, được xóa Skill cùng mọi version và liên kết Agent/Project; được xóa Agent cùng snapshot và liên kết Team/Skill/Tool, bỏ gán PM của Project nếu có. File Skill trên PC giữ nguyên. Có version published, snapshot, hoặc được gán vào danh mục/Team mà chưa dùng trong Process không tự chặn xóa. Quy tắc Tool/Robot không thay đổi. Web không đề xuất Archive/Restore thay cho thao tác này.
- Các hành vi trên hiện được mô phỏng trong trình duyệt. Chưa có lưu trữ catalog, thực thi Tool hay quản lý provider/secret thật.

#### Settings và cấu hình model

- Settings gồm **Providers & Models API**, **Công cụ AI trên PC**, Roles và General. Không có cấu hình Workspace, múi giờ hoặc ngân sách tiền; mặc định giờ Việt Nam. Account chưa thuộc giao diện hiện tại.
- Providers & Models API chứa Provider (API format, Base URL, timeout, credential/trạng thái) và Model API (tên, Model ID, provider, output/temperature). Chỉ danh mục này dùng khi tạo/sửa Agent điều phối.
- Công cụ AI trên PC có Codex CLI/Antigravity; mỗi công cụ quản lý tên model, Model ID gửi tới CLI và Bật sử dụng. Chỉ bật vài model thường dùng; thêm/sửa trong Settings. Không nhập Provider/API key cho model CLI; đăng nhập công cụ trên PC theo adapter. Danh mục khởi tạo có một model đã dùng trong probe mỗi công cụ, có thể sửa/tắt; không chứng minh entitlement trên PC/tài khoản khác. Sửa catalog không sửa exact model_id trong snapshot đã publish. Trường runtime_adapter của API model từ migration 014 chỉ giữ tương thích, không dùng cho lựa chọn mới. [ADR 0007](../architecture/decisions/0007-orchestration-agents-and-ai-tools.md).
- Prototype có Test API giả lập, gồm đang kiểm tra, thành công, sai khóa và timeout. Kiểm tra định dạng Base URL/khóa rỗng tại form; các kết quả kết nối là kịch bản mẫu, không có request thật. Kết quả luôn ghi rõ Demo và bị vô hiệu khi sửa input, kể cả khi đang test; API key không được lưu cùng kết quả. Kiểm tra kết nối thật thuộc backend sau này.
- General có timeout mặc định cho Task mới và số dòng mặc định của Logs. Thay đổi mặc định không ghi đè Task trong version đã publish.
- Provider/model bị tắt không được dùng cho run mới; các lịch bị ảnh hưởng được tắt. Chưa có giao thức provider, secret store hay phép thử kết nối thật; cấu hình và API key phải được triển khai tại backend đáng tin cậy trước khi dùng production. Prototype không lưu API key.

#### Quản lý PC

- Bảng PC có tên/hệ điều hành, trạng thái, Current run, CPU%, RAM dùng/tổng GB và %, Last seen và Actions. Client đọc tải CPU từ delta hệ thống, RAM vật lý từ Windows; gửi qua heartbeat, không sinh số mẫu. Sample CPU đầu chưa đủ dữ liệu hoặc đọc lỗi để trống. Phiên mới xóa sample cũ; offline không hiển thị tải cũ như hiện tại. PC table cập nhật 5 giây khi tab hiển thị. Current run mở chi tiết run.
- Hover/focus trạng thái Running hiển thị Process, node đang thực thi và Agent phụ trách; nếu có nhiều run thì liệt kê tương ứng.
- Connect PC có ba bước: nhập thông tin PC tại Web → Mở/Cài CF Client → xác nhận đã kết nối. Nút Mở CF Client dùng liên kết `agentcf://connect/` đã đăng ký theo tài khoản Windows; trình duyệt có thể hỏi xác nhận mở ứng dụng. Nếu chưa cài, tải CF Client Setup.exe, cài rồi bấm mở lại. Không suy đoán đã mở ứng dụng chỉ từ một timeout trên Web.
- CF Client là cầu nối gọn chạy trong phiên Windows, không hiện ô nhập Server, tên PC hoặc cấu hình model/công cụ; các cấu hình đó quản lý ở Web Center. Client nhận dữ liệu kết nối từ Web, người dùng xác nhận Kết nối. Có trạng thái, mở Web Center, thu xuống khay, thoát và tùy chọn khởi động cùng Windows (mặc định không tự bật). Đóng cửa sổ chỉ thu xuống khay; thoát chờ việc hiện tại kết thúc và không nhận việc mới.
- PC khác hoặc trình duyệt không mở được ứng dụng có thể sao chép liên kết trong Web rồi chọn Dán liên kết ở Client; không bắt nhập Server/tên PC lần nữa. Địa chỉ loopback chỉ dùng cùng máy; PC khác cần HTTPS tới cùng Web/Server. Liên kết chỉ chứa origin Server hợp lệ và mã một lần, không chứa lệnh shell hay token Runner.
- Mã ghép nối 256-bit, dùng một lần, có hạn. Web theo dõi bằng ID ghép nối độc lập, chỉ báo đã kết nối sau session và heartbeat thật. Hết hạn/bị xóa có thông báo/tạo mã mới; không trả credential trong endpoint theo dõi. Client desktop giữ credential bằng Windows DPAPI của người dùng, không upload đăng nhập Codex/Antigravity.
- Edit thay tên hiển thị, giữ identity và tham chiếu trong Process/Run. Details có thông số máy, Task/Agent đang chạy và các Tool được cấp.
- Phía trên bảng có **Connect PC**. Mỗi dòng đặt **Kết nối** khi offline hoặc **Hủy kết nối** khi online/busy trong cột Thao tác, cùng **Sửa** và **Xóa**; không đặt nút dưới tên PC, không có Disable/Enable/Revoke. Hủy kết nối chỉ thu hồi credential/session, giữ PC/cấu hình/file và bị chặn khi có Run/Attempt chưa kết thúc; kết nối lại chính dòng đó giữ ID và các tham chiếu.
- Một device trong Workspace chỉ có một PC còn hoạt động. Client gửi định danh Windows/cài đặt ổn định cùng proof bảo vệ DPAPI; Server lưu proof hash, không dedup theo tên/OS hoặc dùng device ID thay authentication. Connect PC có sẵn tạo code gắn target ID; ghép lại giữ ID, rotate credential/revoke session cũ trong transaction. Client legacy có credential hợp lệ bind device khi nâng cấp; legacy chưa có đủ identity không tự gộp theo tên. PC đã Xóa không tự restore. Quy tắc và giới hạn tại ADR 0010.
- Xóa cần xác nhận, bị chặn khi PC có Attempt hoặc node ghim PC thuộc run chưa kết thúc (kể cả đang chờ). Xóa gỡ PC khỏi danh sách, thu hồi credential/session và tắt Schedule chỉ định PC hoặc chứa node ghim PC đó. File trên máy và lịch sử chạy giữ nguyên; ghép nối lại tạo danh tính mới. Version cũ giữ tham chiếu; để chạy tiếp phải chọn PC khác và publish version mới. API Disable/Enable/Revoke cũ giữ tương thích; Enable không khôi phục PC đã xóa.

#### Robot catalog và node Robot

- Robots có New/Edit/Delete và New version. Bảng chỉ hiển thị active version và thống kê của version đó, không có dropdown đổi version trực tiếp. Chỉ đổi active version trong Edit và áp dụng khi Save; Cancel không đổi gì. Tạo version mới không tự active. Active version làm mặc định khi thêm node mới, không tự đổi RobotVersion đã gán trong Process. Catalog không gán Agent/PC. Edit sửa metadata; thay đổi chương trình qua version mới, không ghi đè version đã phát hành.
- Success rate tách theo RobotVersion; bản mới chưa có dữ liệu thay vì hiển thị 0%. Thành công/(thành công + thất bại); timeout là lỗi, hủy thống kê riêng. Bản cũ giữ dữ liệu sau khi phát hành bản mới.
- Kéo Robot vào Process hoặc bấm Robot trong palette để thêm node; node bắt buộc chọn RobotVersion, Agent chịu trách nhiệm, PC và input JSON hợp lệ. PM quản lý tổng thể, không thay Agent phụ trách node.
- Thay đổi node của Process đã publish tạo draft; Publish tạo ProcessVersion mới. Run cũ giữ snapshot graph/version cũ; Schedule không tự chuyển version mới. Trong prototype, node mới nối tiếp chuỗi hiện có; dependency tùy ý và engine thực thi chưa được triển khai.
- Robot có phiên bản published, lịch sử hoặc tham chiếu không xóa cứng được. Robot chưa sử dụng có thể xóa sau xác nhận; Web không có nút hoặc bộ lọc Archive/Restore.
- Thống kê và Entry point hiện là dữ liệu mẫu trong bộ nhớ, chưa upload hoặc chạy artifact thật.

#### Projects, Team và Targets

- Projects dùng bảng có Search. Cảnh báo lỗi phải chỉ rõ số lỗi và mở được run liên quan, không chỉ hiển thị nhãn “cần chú ý”; cảnh báo vận hành được tách khỏi hai trạng thái vòng đời Đang hoạt động / Không hoạt động của Project.
- Trong Project có Processes, Team, Targets, Runs. Header gọn với PM, target hiện tại và số run đang hoạt động; không lặp các thẻ thống kê. Tab Runs được đặt đúng nội dung.
- Team chỉ là danh sách thông tin tự tổng hợp theo Project: PM hiện tại và các Agent được phân công trong node của phiên bản mới nhất đã lưu của mỗi Process (draft nếu có, nếu không là published mới nhất). Khử trùng theo ID Agent trên toàn Project, PM cũng chỉ hiện một lần. Chọn Agent trực tiếp từ catalog active cho cả node AI và Robot; không quản lý membership hoặc yêu cầu thêm vào Team trước. Đổi PM, đổi/xóa node hay xóa Process tự phản ánh vào Team khi tải lại; quay từ editor về Project tải lại dữ liệu. Version lịch sử không làm phình Team hiện tại; lịch sử/snapshot và bảo vệ xóa Agent còn được version Process tham chiếu không thay đổi. Membership thủ công cũ không phải nguồn tính Team.
- Target lưu loại kỳ tuần/tháng, khoảng thời gian, mục tiêu, số kết quả được duyệt và tiêu chí nghiệm thu. Run thành công không tự tính là kết quả được duyệt. Cơ chế PM duyệt thật và lưu bằng chứng chưa được triển khai; prototype nhập số lượng qua form.
- Header dùng target tháng đang hiệu lực, nếu không có thì target tuần. Kỳ cũ giữ lại trong Targets; chưa có target hiện tại thì không hiển thị phần trăm giả.
- Bảng Process có Run và Start/Stop, các thao tác Schedule/Edit/Delete nằm trong menu ⋯. Lịch hiển thị ProcessVersion đã gán, không tự chuyển sang version mới. Last run mở Run detail; PC cấu hình theo node Robot.

#### Roles của Agent

- Settings → Roles có thêm/sửa/xóa tên Role, mô tả nhiệm vụ (Duties) và phần Permissions dự kiến. Agent chọn Role bằng select; nhiều Agent có thể chọn cùng một Role. Không dùng free text hoặc chuỗi “Project Manager” để xác định quyền/vai trò PM.
- Trong giai đoạn prototype, Role chỉ mô tả nhiệm vụ và chuẩn bị cho phân quyền sau này. Permissions không thay đổi khả năng chạy, không tự tắt Schedule và không cấp quyền thật; quyền Tool riêng hiện có của Agent vẫn được kiểm tra theo mô hình hiện tại. PM được giao tại Project độc lập với nhãn Role.
- Tên Role bắt buộc, không chỉ có khoảng trắng và không trùng trong catalog. Đổi tên giữ ID và cập nhật nhãn các Agent cùng Role; không ghi đè cấu hình model/Skill hoặc lịch sử sử dụng riêng.
- Delete phải có xác nhận. Role chưa dùng có thể xóa hẳn; Role đang có Agent tham chiếu bị từ chối xóa để giữ liên kết. Web không có thao tác/bộ lọc Archive/Restore cho Role.
- Phân quyền Agent thực sự và phân quyền tài khoản là thiết kế cho giai đoạn sau; không coi checkbox Permissions hiện tại là biện pháp bảo mật đã triển khai.

## Phạm vi prototype và phần cần triển khai thật

| Hạng mục | Đã có trong HTML prototype | Cần triển khai/thiết kế tiếp |
|---|---|---|
| Lưu trữ | Dữ liệu mẫu trong bộ nhớ, refresh đặt lại | Backend, database, migration và audit bền vững |
| Project/Process/catalog | CRUD, xác nhận Delete, Archive/Restore trong prototype cũ, Team/Targets | Web hiện hành chỉ giữ bật/tắt Project; validation đáng tin cậy và lịch sử bền vững |
| Process editor | Kéo node, thêm/sửa node Robot, publish/snapshot mẫu | Editor Agent task/dependency đầy đủ, hợp đồng input/output |
| Schedule | Lưu cấu hình, Start/Stop, tính mốc tiếp theo | Scheduler thật, chống tạo trùng và điều phối PC |
| Runs/Logs | Filter, STT, Total, phân trang, trạng thái/timestamp/log mẫu, Cancel giả lập | Engine thực thi, log thật, truy vấn server, cập nhật trực tiếp |
| Overview | Lỗi chưa xử lý, tiến độ Target, tổng token mẫu | Dữ liệu nguồn, lưu trạng thái xử lý cảnh báo và thống kê thực tế |
| Agent/Project đánh giá | Quality mẫu, Targets nhập qua form | PM review/báo cáo tự động, bằng chứng nghiệm thu, công thức xếp hạng |
| Robots/Skills/Tools | Catalog và version minh họa, thống kê Robot theo version | Upload/chạy artifact, Tool execution và Skill snapshot bền vững |
| PC | Ghép nối, trạng thái/tải và lifecycle giả lập | Bộ cài Runner Client, credential, heartbeat, telemetry và dispatch |
| Providers/Models | Form, Test API giả lập và danh mục chọn model | Secret store, adapter provider và Test API thật phía backend |
| Roles/Account | Role chung và Permissions dự kiến | Quyền Agent/runtime, tài khoản và phân quyền người dùng |
| Tokens | Một tổng tháng mẫu mỗi Agent | Usage từ provider, chốt kỳ, đối soát/chống đếm trùng; chưa có ngưỡng cảnh báo |

Các kiểm tra UI hiện tại được mô tả tại [README prototype](../../demo/agent-cf-prototype/README.md#kiểm-tra-giao-diện). Chúng không chứng minh yêu cầu engine, quyền hoặc kết nối thật đã hoàn thành.

## Kiểm tra khi triển khai theo giao diện

- Giữ tên và vị trí menu; tạo Process từ trong Project, Tool nội bộ trong Skills và Role trong Settings.
- Project/Process/catalog có thêm/sửa/xóa và xác nhận trước Delete, giữ bảo vệ lịch sử; riêng Project có Ngừng hoạt động/Kích hoạt lại. Các mục khác không có Archive/Restore trên Web.
- Save schedule không Start, Start không Run ngay, Stop không Cancel, Cancel không Stop.
- Run luôn giữ ProcessVersion/RobotVersion và Agent chịu trách nhiệm; sửa catalog/draft không đổi lịch sử.
- Filter Runs kết hợp đúng Project/Process/Status/ngày; Ended, Duration, STT và Total đúng qua trang, kể cả không có kết quả.
- Run detail giữ log là phần chính; tìm/lọc/phân trang theo dữ liệu thật, không suy trạng thái TaskRun từ phần trăm.
- Đánh dấu lỗi đã xử lý không sửa trạng thái Run; nghiệm thu Target không tự tăng theo run thành công.
- Mọi Agent chọn Role/model từ catalog; nhiều Agent dùng cùng Role; cấu hình PM độc lập.
- Không thêm Workspace, Cost/Budget hoặc chọn múi giờ vào UI hiện tại.

## Các câu hỏi thiết kế còn lại

- Chính sách lưu giữ dữ liệu sau archive.
- Có cần thao tác publish-and-run về sau hay không; hiện tại Publish và Run tách riêng.
- Input/output dùng JSON Schema 2020-12 và binding khai báo theo domain model; kiểm chứng khi triển khai.
- Default timeout/heartbeat/lease đã thiết kế tại execution model; giới hạn vận hành cần kiểm chứng khi triển khai.
- Dữ liệu log nào được lưu và thời hạn lưu giữ.
- Cơ chế runner mẫu cần thiết cho lần triển khai đầu tiên.
- PC node là ràng buộc; Schedule/Manual Run cung cấp mặc định cho node không ghim PC. Filter Running gồm mọi trạng thái chưa terminal; dòng giữ trạng thái cụ thể theo execution model.
- PM review/báo cáo tự động, bằng chứng nghiệm thu và công thức xếp hạng.
- Nguồn usage token, kỳ thống kê và ngưỡng cảnh báo nếu bổ sung sau này.

## Lưu và dùng ngay — BASE-009

Prompt Skill local mặc định là hai dòng `Gọi skill <đường dẫn .md>` và `cho chủ đề <đường dẫn chủ đề>`, truyền trực tiếp cho CLI; không qua file yêu cầu trung gian. Chỉ nối nội dung Nhiệm vụ bổ sung của node và Yêu cầu riêng của lần chạy khi người dùng nhập. Không tự ghép hướng dẫn Agent, bản copy Skill, tiêu chuẩn output, JSON hoặc quy trình bổ sung; file Skill gốc quy định cách thực hiện.

Khi chuyển từ cấu hình thư mục ở node sang root Project, bảo toàn cấu hình đã lưu: Project trống nhận root cũ nếu các node thống nhất; không ghi đè root Project hiện có hoặc tự chọn giữa các root khác nhau. Giữ nguyên snapshot và file PC.

Nhánh Skill local Codex và Antigravity phải dùng cùng kiểm tra PC/root/chủ đề, không sửa Skill gốc và chỉ báo thành công khi có output thật trên PC. Antigravity dùng Model ID chính xác, timeout node và callback PID cho journal/quản lý tiến trình; CLI tự fallback model không được tính là thành công. Khả năng CLI/tài khoản/mạng được kiểm chứng riêng, không suy từ catalog.

Ngoài Robot không có bước Draft/Version/Publish trên Web. Skill lưu đường dẫn/PC; Process Lưu rồi Chạy. Robot Lưu một phiên bản sẵn dùng, không Publish riêng. Snapshot và API lifecycle cũ chỉ phục vụ tương thích/lịch sử; xem [ADR 0011](../architecture/decisions/0011-save-and-run-current-configuration.md).
