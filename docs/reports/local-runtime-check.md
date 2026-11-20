# Kiểm chứng runtime local — 2026-11-16

> Date: 2026-11-16 (Asia/Saigon)  
> Status: Codex đạt thử nghiệm nhỏ; Antigravity đạt Skill và resume sau thoát qua CMD tương tác, đường headless/pipe còn giới hạn.

## Phạm vi và kết quả

Kiểm chứng bằng Skill chẩn đoán chỉ đọc, không tạo bài, không sửa ba Skill nghiệp vụ, không dùng phiên hội thoại đang làm việc của người dùng. Chưa triển khai adapter production, Web hoặc engine. Không sửa credential hoặc đổi tài khoản; đã xác nhận trust riêng workspace fixture trong phiên Antigravity tương tác.

| Kiểm tra | Codex CLI 0.147.0 | Antigravity CLI 1.0.6 |
|---|---|---|
| Tìm thấy executable, đọc version/help | Đạt qua `codex.cmd` | Đạt qua `agy.exe` |
| Liệt kê model | Đạt: app-server `model/list`, gồm hidden, hỗ trợ phân trang | Qua pipe: exit 0 nhưng rỗng. Qua terminal tương tác: thấy 3 nhãn model |
| Phát hiện Skill trong workspace | `skills/list` thấy `runtime-probe`, enabled, không lỗi discovery | Phiên CMD tương tác đọc đúng file Skill theo đường dẫn prompt; chưa kiểm chứng discovery API |
| Chạy Skill thật | Đạt với `gpt-5.6-sol`; runtime đọc `SKILL.md`, trả đúng marker | CMD → `agy`: đạt với Claude Sonnet 4.6 (Thinking). Print/pipe vẫn chưa đạt |
| Tiếp tục đúng phiên | Đạt: `exec resume <thread-id>` giữ đầu vào cũ | Đạt trong phiên và sau thoát/mở lại bằng `--conversation=<id>`; giữ đầu vào cũ |

**Cả hai runtime đã thực thi Skill thử trên máy.** Antigravity hoạt động qua CMD tương tác; kết quả print/pipe rỗng trước đó không chứng minh runtime không chat được. Vẫn cần đường tích hợp tin cậy cho ứng dụng (ví dụ điều khiển terminal có PTY hoặc sửa đường headless), chưa coi adapter production đã hoàn thành. Không kết luận lỗi trước đó do tài khoản thiếu quyền hoặc hết quota.

## Bằng chứng Codex

- `codex.cmd login status`: đã đăng nhập bằng ChatGPT. Không đọc hoặc xuất credential.
- `initialize` qua stdio thành công; `model/list` trả 5 mục. Danh mục tham chiếu và trạng thái kiểm chứng tại [local-runtime-models.json](local-runtime-models.json); chỉ `gpt-5.6-sol` được thử inference ở chặng này.
- Cấu hình mặc định đang chọn `gpt-6.1-sol`; lần gọi đầu bị từ chối với `model_not_found` và thông báo không hỗ trợ model này khi dùng tài khoản ChatGPT local. Không suy ra model đó không tồn tại ở mọi sản phẩm/tài khoản. Các phép thử sau truyền rõ `-m gpt-5.6-sol`, không sửa cấu hình global.
- Skill thử được phát hiện dưới `tests/fixtures/runtime-probe/.agents/skills/runtime-probe/SKILL.md`. Prompt chỉ cung cấp từ `orchid`; marker bí mật thử nghiệm nằm trong Skill, không được nhúng trong prompt.
- Lượt đầu có sự kiện runtime đọc file Skill thành công, phản hồi `SKILL_OK|orchid|cobalt-lantern-42`, rồi `turn.completed`, exit 0.
- Lượt sau dùng đúng thread ID của lượt đầu, phản hồi `RESUME_OK|orchid|cobalt-lantern-42`, rồi `turn.completed`, exit 0. Không dùng `--last` để tránh tiếp tục nhầm phiên khác.
- Thử nghiệm dùng approval `never`, sandbox `read-only`, không bypass permission; chưa kiểm chứng quyền ghi artifact, web search, timeout/hủy hoặc phục hồi sau crash.

Lệnh tái lập từ root (smoke gửi yêu cầu model thật, dùng quota tài khoản):

```powershell
.\.venv\Scripts\python.exe apps/client/scripts/probe_local_runtime.py codex
.\.venv\Scripts\python.exe apps/client/scripts/probe_local_runtime.py codex --smoke --model gpt-5.6-sol --timeout 90
```

Script dùng stdlib Python, đọc danh sách qua RPC và phân trang đến hết; xuất kết quả đã chọn lọc, không xuất raw log hoặc tài khoản. Metadata discovery không chứng minh quyền dùng model. Một phiên mới được tạo khi smoke và có thể được Codex lưu trong dữ liệu người dùng; script không xóa hoặc sửa các phiên khác.

## Bằng chứng Antigravity

Help local xác nhận `-p`/`--print`, `--model`, `--continue`, `--conversation`, `--sandbox`, `--print-timeout`, `--log-file`; chưa có transport JSON/stream trong help của bản này. Không áp dụng máy móc mọi cờ của tài liệu online mới hơn.

```powershell
agy.exe --version
agy.exe --help
agy.exe models
```

- Trong terminal tương tác, `agy models` hiển thị `Claude Sonnet 4.6 (Thinking)`, `Claude Opus 4.6 (Thinking)`, `GPT-OSS 120B (Medium)`; không kèm ID máy đọc được trong đầu ra quan sát.
- `subprocess` với stdout/stderr pipe nhận chuỗi rỗng dù exit 0; script chẩn đoán coi là chưa kiểm chứng, không phải thành công.
- Lần thử đầu `agy --sandbox --print-timeout 45s -p <prompt-thử>` trong terminal không trả kết quả sau hơn 45 giây; đã dừng đúng tiến trình chẩn đoán, giữ nguyên tiến trình Antigravity có sẵn của người dùng. Lần đó chưa hoàn tất checkpoint trust workspace qua giao diện; chưa xác định đó là nguyên nhân duy nhất. Chưa khẳng định cờ timeout hoạt động đúng trên đường gọi này.
- Sau khi trust workspace qua CMD, đã thử lại script print/pipe với timeout 30 giây: exit 0 nhưng stdout/stderr vẫn rỗng, không đạt marker. Không được dùng kết quả này phủ nhận thành công của chế độ tương tác.
- Chưa kiểm chứng artifact, chọn model khác hoặc search. Không dùng `--continue` vì có thể chạm phiên gần nhất của người dùng.

Chẩn đoán qua pipe (hiện exit 1 để thể hiện còn cần kiểm tra thủ công):

```powershell
.\.venv\Scripts\python.exe apps/client/scripts/probe_local_runtime.py antigravity
.\.venv\Scripts\python.exe apps/client/scripts/probe_local_runtime.py antigravity --smoke --timeout 60
```

Nếu kiểm tra terminal tương tác, chuyển vào `tests/fixtures/runtime-probe` rồi dùng prompt yêu cầu Skill `runtime-probe` với input `orchid`. Phải có thời hạn giám sát bên ngoài; không chỉ dựa vào `--print-timeout`. Script qua pipe không thay thế kiểm tra terminal.

### Bổ sung theo cách người dùng đang chạy: CMD → agy

Đã mở một terminal có PTY trong workspace fixture, chạy `cmd.exe /d /c agy` (không dùng print mode). CLI yêu cầu trust thư mục fixture; sau xác nhận xuất hiện prompt với model Claude Sonnet 4.6 (Thinking). Có cảnh báo tải ảnh hồ sơ thất bại nhưng không ngăn các lượt chat thử thành công.

1. Nhập yêu cầu đọc `.agents/skills/runtime-probe/SKILL.md`, input `orchid`, không sửa file hoặc delegate. Quan sát tool Read đọc đúng file, kết quả `SKILL_OK|orchid|cobalt-lantern-42` và quay về prompt.
2. Gửi lượt tiếp yêu cầu nhớ input trước, không cung cấp lại từ đó. Kết quả `RESUME_OK|orchid|cobalt-lantern-42` và quay về prompt: hội thoại trong cùng phiên giữ được ngữ cảnh.
3. Gõ `/exit`: CLI thoát exit 0 và in lệnh `agy --conversation=<conversation-id>` của chính phiên thử. ID được dùng cục bộ, không cần đưa tài khoản hoặc raw transcript vào Git.
4. Mở tiến trình CMD mới với `agy --conversation=<conversation-id>` lấy từ bước trước; CLI tải lại hội thoại. Gửi yêu cầu nhớ input gốc, không nêu lại từ đó: kết quả `RESUME_OK|orchid|cobalt-lantern-42` và quay về prompt. Như vậy resume sau thoát đã được kiểm chứng, không chỉ hội thoại nhiều lượt trong tiến trình cũ. Đã thoát phiên thử sau kiểm tra.

Kết quả print/pipe và kết quả CMD tương tác là hai phép thử khác nhau. Chưa có adapter điều khiển PTY/chuẩn hóa màn hình terminal trong Client; chưa tự chọn dependency hoặc coi đọc ANSI là hợp đồng sự kiện ổn định.

## Danh mục model và cấu hình node sau này

### Thử lựa chọn Gemini 3.8 Flash High cho Skill 0

Người dùng yêu cầu thử Skill 0 cho chủ đề “Thật tệ khi làm mẹ đơn thân”, thư mục đích `tests/3.Thật tệ khi làm mẹ đơn thân/`. Kiểm tra trước chạy: thư mục có sẵn và trống.

- Đã mở `agy` tương tác trong `tests/`, xác nhận trust thư mục và mở `/model`: chỉ thấy Claude Sonnet 4.6 (Thinking), Claude Opus 4.6 (Thinking), GPT-OSS 120B (Medium); không thấy Gemini 3.8 Flash High.
- Thử `agy.exe --model 'Gemini 3.8 Flash High'` theo đúng nhãn người dùng cung cấp: giao diện vẫn hiện Claude Sonnet 4.6 (Thinking). Nhãn này chưa được xác minh là ID runtime hợp lệ; không kết luận lỗi do quyền tài khoản hoặc Gemini không tồn tại.
- Chưa gửi prompt tạo cốt truyện, chưa tạo hoặc ghi đè `cot truyen.txt`, không tự chuyển model khác. Đã thoát các phiên thử.
- Phép thử Skill 0 với model được yêu cầu **chưa thực hiện được**; cần xác định cách chọn/ID Gemini trên CLI hoặc cấu hình/tài khoản CLI phù hợp. Nhãn vẫn được giữ trong inventory.

### Quy tắc danh mục

Giữ **đủ 7 nhãn Antigravity trong ảnh người dùng cung cấp**, kể cả ba mục đang Unavailable. Không lọc mất model chỉ vì tài khoản hiện tại không có quyền. Danh sách đầy đủ nằm ở [inventory JSON](local-runtime-models.json), không phải danh sách cố định của toàn bộ sản phẩm Antigravity.

Tách tên hiển thị, ID runtime và kết quả kiểm chứng quyền. ID Antigravity hiện để `null` vì chưa có ánh xạ đáng tin cậy; không đoán ID từ nhãn. Người dùng vẫn có thể lưu lựa chọn dự kiến trong bản thiết kế sau này, nhưng cần giải quyết ID và kiểm tra khả dụng trước khi thực thi; không tự thay bằng model khác. Đổi tài khoản/máy cần làm mới quyền và ánh xạ, giữ nguyên danh mục lựa chọn. Danh mục tham chiếu JSON chưa phải config runtime đã được ứng dụng sử dụng.

Mỗi node sẽ chọn Agent phụ trách, runtime, model, Skill và input theo [requirements](../product/requirements.md#cấu-hình-node-dùng-runtime-local). Phần editor thuộc chặng sau, chưa có trong thử nghiệm này.

## Kiểm tra và giới hạn

```powershell
.\.venv\Scripts\python.exe -m pytest apps/client/tests/unit/adapters/test_local_runtime_probe.py -q
```

Đã chạy **9 test đạt**: marker đúng, giữ thread ID, không chấp nhận thiếu completion hoặc có lỗi, không coi exit 0 rỗng là thành công, timeout và không xuất raw log. Đã chạy metadata probe thực tế cho hai CLI; smoke Skill/resume thực tế của Codex đạt. Antigravity đạt Skill và resume sau thoát qua CMD tương tác; phép thử đó dùng PTY, không phải script pipe. Script không phải bộ quản lý cây tiến trình production: timeout qua wrapper Windows chưa bảo đảm dừng mọi chương trình con; xử lý cây tiến trình thuộc phần độ tin cậy sau này.

Ba Skill nghiệp vụ vẫn nguyên trạng. Skill 1 còn yêu cầu người dùng duyệt trong nội dung hiện hữu; khi triển khai vòng Agent thay người phải cập nhật hợp đồng và hướng dẫn liên quan, không tự bỏ checkpoint trong bước chẩn đoán.

## Nguồn đối chiếu

- [OpenAI Codex App Server](https://developers.openai.com/codex/app-server): tham chiếu stdio RPC, model/Skill discovery và vòng đời thread; local help/probe xác nhận phần đang dùng.
- [OpenAI non-interactive mode](https://developers.openai.com/codex/noninteractive): tham chiếu exec, JSONL và resume.
- [Antigravity headless](https://antigravity.google/docs/cli/headless/): tham chiếu print/tiếp tục hội thoại; khác biệt của bản cài local được ghi riêng phía trên.

Các nhãn model trong ảnh là dữ liệu do người dùng cung cấp; không phải cam kết quyền dùng hoặc model ID được tài liệu chính thức xác nhận.
