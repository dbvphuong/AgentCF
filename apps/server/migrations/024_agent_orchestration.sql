-- Migration 024: Agent orchestration templates, multi-turn decisions, and human resume context

CREATE TABLE agent_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    prompt_text TEXT NOT NULL CHECK(length(trim(prompt_text)) > 0),
    allow_reply INTEGER NOT NULL DEFAULT 1 CHECK(allow_reply IN (0, 1)),
    allow_retry INTEGER NOT NULL DEFAULT 1 CHECK(allow_retry IN (0, 1)),
    allow_need_human INTEGER NOT NULL DEFAULT 1 CHECK(allow_need_human IN (0, 1)),
    max_turns INTEGER NOT NULL DEFAULT 10 CHECK(max_turns >= 1 AND max_turns <= 50),
    is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE UNIQUE INDEX one_default_agent_template ON agent_templates(is_default) WHERE is_default = 1;

INSERT INTO agent_templates (
    id, name, description, prompt_text, allow_reply, allow_retry, allow_need_human, max_turns, is_default
) VALUES
(
    'tpl-default-orchestrator',
    'Điều phối chuẩn',
    'Kiểm tra kết quả, tự trả lời câu hỏi đơn giản, hỏi người dùng khi cần và phân tích lỗi.',
    'Kiểm tra kết quả công cụ AI trả về và tình trạng file đã tạo/sửa:' || char(10) ||
    '- Chọn done: khi công việc đã hoàn thành đúng mục tiêu và có kết quả hợp lệ.' || char(10) ||
    '- Chọn reply: khi công cụ hỏi có tiếp tục không (ví dụ viết Part tiếp theo), hỏi xác nhận đơn giản hoặc cần nhắc hoàn tất ghi file -> nhập câu trả lời ngắn gọn.' || char(10) ||
    '- Chọn need_human: khi công cụ hỏi quyết định nghiệp vụ quan trọng, thiếu thông tin từ chủ dự án hoặc cần đăng nhập/thao tác tay.' || char(10) ||
    '- Chọn retry: khi gặp lỗi mạng, timeout hoặc CLI ngắt tạm thời.' || char(10) ||
    '- Chọn fail: khi lỗi không tự xử lý được -> giải thích rõ nguyên nhân và cách khắc phục bằng tiếng Việt.',
    1, 1, 1, 10, 1
),
(
    'tpl-multi-part-writer',
    'Viết dài nhiều Part',
    'Tự động gõ tiếp tục qua từng Part cho tới khi hoàn thành toàn bộ bài.',
    'Theo dõi tiến trình viết nhiều Part của công cụ AI:' || char(10) ||
    '- Chọn reply: nếu công cụ vừa viết xong một Part và hỏi tiếp tục, hãy trả lời "Tiếp tục viết Part tiếp theo". Nếu hỏi chọn hướng mặc định, chọn phương án đầu tiên phù hợp yêu cầu.' || char(10) ||
    '- Chọn done: chỉ khi công cụ xác nhận đã hoàn thành toàn bộ các Part và đã ghi file.' || char(10) ||
    '- Chọn need_human: khi công cụ hỏi chỉnh sửa cốt truyện lớn hoặc vượt quá khả năng tự quyết.' || char(10) ||
    '- Chọn retry/fail: khi lỗi CLI hoặc thiếu quyền/quota, tóm tắt rõ nguyên nhân tiếng Việt.',
    1, 1, 1, 15, 0
),
(
    'tpl-strict-single-run',
    'Chạy thẳng & Kiểm lỗi',
    'Không tự trả lời hội thoại; chỉ kiểm tra hoàn thành, thử lại khi lỗi tạm hoặc báo lỗi.',
    'Kiểm tra kết quả chạy một lượt của công cụ AI:' || char(10) ||
    '- Chọn done: khi bước thực hiện xong và có kết quả hợp lệ.' || char(10) ||
    '- Chọn need_human: nếu công cụ dừng lại đặt câu hỏi chờ xác nhận.' || char(10) ||
    '- Chọn retry: khi lỗi mạng hoặc timeout tạm thời.' || char(10) ||
    '- Chọn fail: khi thất bại rõ ràng -> phân tích nguyên nhân và gợi ý cách xử lý bằng tiếng Việt.',
    0, 1, 1, 3, 0
);

ALTER TABLE agents ADD COLUMN template_id TEXT;
ALTER TABLE agents ADD COLUMN allow_reply INTEGER NOT NULL DEFAULT 1 CHECK(allow_reply IN (0, 1));
ALTER TABLE agents ADD COLUMN allow_retry INTEGER NOT NULL DEFAULT 1 CHECK(allow_retry IN (0, 1));
ALTER TABLE agents ADD COLUMN allow_need_human INTEGER NOT NULL DEFAULT 1 CHECK(allow_need_human IN (0, 1));
ALTER TABLE agents ADD COLUMN max_turns INTEGER NOT NULL DEFAULT 10 CHECK(max_turns >= 1 AND max_turns <= 50);

ALTER TABLE task_runs ADD COLUMN waiting_context_json TEXT CHECK(waiting_context_json IS NULL OR json_valid(waiting_context_json));

CREATE TABLE agent_turn_decisions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES process_runs(id),
    task_run_id TEXT NOT NULL REFERENCES task_runs(id),
    attempt_id TEXT NOT NULL REFERENCES attempts(id),
    agent_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL CHECK(turn_number >= 1),
    action TEXT NOT NULL CHECK(action IN ('done', 'reply', 'need_human', 'retry', 'fail')),
    reply_message TEXT,
    route TEXT,
    summary_vi TEXT NOT NULL DEFAULT '',
    question_for_user TEXT,
    suggested_options_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(suggested_options_json)),
    error_analysis TEXT,
    raw_output_preview TEXT,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
) STRICT;

CREATE INDEX idx_agent_turn_decisions_run ON agent_turn_decisions(run_id, task_run_id, turn_number);

-- Allow conditional-branch skipped tasks (and handled failed tasks) when a Run completes as succeeded
DROP TRIGGER IF EXISTS terminal_run_requires_settled_tasks;
CREATE TRIGGER terminal_run_requires_settled_tasks BEFORE UPDATE OF status ON process_runs
WHEN NEW.status IN ('succeeded', 'failed', 'cancelled') AND (
    EXISTS(SELECT 1 FROM task_runs WHERE run_id = NEW.id AND status NOT IN ('succeeded', 'failed', 'skipped', 'cancelled'))
    OR EXISTS(SELECT 1 FROM attempts WHERE run_id = NEW.id AND status NOT IN ('succeeded', 'failed', 'cancelled'))
    OR (NEW.status = 'succeeded' AND NOT EXISTS(SELECT 1 FROM task_runs WHERE run_id = NEW.id AND status = 'succeeded'))
    OR (NEW.status = 'succeeded' AND EXISTS(SELECT 1 FROM task_runs WHERE run_id = NEW.id AND status = 'cancelled'))
)
BEGIN
    SELECT RAISE(ABORT, 'run_tasks_unsettled');
END;
