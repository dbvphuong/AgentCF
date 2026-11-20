"""Execute an on-PC Skill in place and report references to actual local files."""

import hashlib
import os
from pathlib import Path

from agent_cf_client.runtime.base import RuntimeExecutionResult


def file_inventory(directory: Path) -> dict[str, dict]:
    files = {}
    for root, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {".git", ".agents", "__pycache__"}
                   and not (Path(root) / d).is_symlink()]
        for name in names:
            path = Path(root) / name
            if path.is_symlink() or not path.is_file():
                continue
            with path.open("rb") as stream:
                raw_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            files[str(path.relative_to(directory))] = {
                "path": str(path.resolve()), "size_bytes": path.stat().st_size, "sha256": raw_hash,
            }
    return files


def execute_local_skill(*, adapter, task, input_data, runner_id, log_dir, on_started, session_id=None):
    source = task["skill_snapshot"]
    if source.get("source_runner_id") != runner_id or task.get("runner_id") != runner_id:
        raise ValueError("PC không khớp PC sở hữu file Skill")
    skill_path = Path(source["source_path"])
    working = Path(task.get("working_directory", ""))
    if not skill_path.is_absolute() or not skill_path.is_file() or skill_path.suffix.lower() != ".md":
        raise ValueError("Không tìm thấy file .md chính tại đường dẫn tuyệt đối trên PC này")
    if not working.is_absolute() or not working.is_dir():
        raise ValueError("Thư mục làm việc tuyệt đối phải tồn tại trên PC này")
    working = working.resolve()
    topic_directory = None
    if input_data.get("topic_directory"):
        topic_directory = Path(input_data["topic_directory"])
        if not topic_directory.is_absolute() or not topic_directory.is_dir():
            raise ValueError("Không tìm thấy thư mục chủ đề đã có trên PC. Không tự tạo thư mục thay thế.")
        topic_directory = topic_directory.resolve()
        if topic_directory == working or not topic_directory.is_relative_to(working):
            raise ValueError("Thư mục chủ đề thực tế phải nằm bên trong thư mục Project.")
    # Validate UTF-8 without replacing the source Skill or its supporting files.
    skill_path.read_text(encoding="utf-8-sig")
    source_hash = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    inventory_root = topic_directory or working
    before = file_inventory(inventory_root)
    # The original Skill owns the workflow. Pass the user's invocation directly,
    # without adding another set of instructions or a request-file indirection.
    prompt = f"Gọi skill {skill_path}"
    topic = str(topic_directory) if topic_directory else input_data.get("topic")
    if topic:
        prompt += f"\ncho chủ đề {topic}"
    # Only append notes explicitly entered by the user, without adding rules.
    for note in (task.get("instructions"), input_data.get("request")):
        if isinstance(note, str) and note.strip():
            prompt += "\n" + note.strip()
    method = getattr(adapter, "execute_local_skill", None)
    if method is None:
        raise ValueError("Adapter này chưa được kiểm chứng cho Skill tạo/sửa file tại PC")
    result = method(
        prompt=prompt,
        cwd=working, model=task["runtime"]["model_id"],
        timeout_seconds=float(task.get("execution_timeout_seconds", 300)),
        log_dir=log_dir, on_started=on_started,
        session_id=session_id,
        **({"reasoning_effort": task["runtime"]["reasoning_effort"]}
           if task["runtime"].get("reasoning_effort") else {}),
    )
    if not result.session_id and session_id:
        result.session_id = session_id
    after = file_inventory(inventory_root)
    changed = [value for key, value in after.items() if before.get(key) != value]
    source_unchanged = skill_path.exists() and hashlib.sha256(skill_path.read_bytes()).hexdigest() == source_hash
    if result.success and (not changed or not source_unchanged):
        result = RuntimeExecutionResult(
            success=False, exit_code=result.exit_code, session_id=result.session_id,
            error_code="local_output_missing" if not changed else "skill_source_modified",
            error_message="Runtime chưa tạo/sửa file output thực tế" if not changed else "Runtime đã thay đổi Skill nguồn",
        )
    metadata = {
        "runner_id": runner_id, "working_directory": str(working),
        "skill_source_path": str(skill_path), "skill_source_sha256": source_hash,
        "local_files": changed, "session_id": result.session_id,
        "summary": result.output_text,
        **({"topic_directory": str(topic_directory)} if topic_directory else {}),
    }
    return result, metadata
