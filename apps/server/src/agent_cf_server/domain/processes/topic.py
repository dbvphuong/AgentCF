"""A topic is an existing directory inside the pinned Project working directory."""

from pathlib import PurePosixPath, PureWindowsPath
from agent_cf_server.domain.skills.local_source import validate_absolute_path


def path_object(value):
    validate_absolute_path(value)
    path = PureWindowsPath(value) if PureWindowsPath(value).is_absolute() else PurePosixPath(value)
    if ".." in path.parts:
        raise ValueError("Đường dẫn không được chứa '..'")
    return path


def topic_configuration(tasks):
    local = [t for t in tasks if t.get("skill_snapshot", {}).get("source_path")]
    if not local:
        raise ValueError("Process chưa có Skill local; dùng dữ liệu nâng cao cho loại Process này.")
    roots = {path_object(t.get("working_directory", "")) for t in local}
    runners = {t.get("runner_id") for t in local}
    if len(roots) != 1 or len(runners) != 1 or not next(iter(runners)):
        raise ValueError("Các bước Skill local cần cùng PC và thư mục Project để dùng chung một chủ đề.")
    return {"working_directory": str(next(iter(roots))), "runner_id": next(iter(runners))}


def normalize_topic_input(data, tasks):
    if "topic_directory" not in data:
        return data
    raw = data["topic_directory"]
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Nhập đường dẫn thư mục chủ đề đã có trên PC.")
    config = topic_configuration(tasks)
    root = path_object(config["working_directory"])
    topic = path_object(raw.strip())
    if type(topic) is not type(root) or topic == root or not topic.is_relative_to(root):
        raise ValueError("Thư mục chủ đề phải nằm bên trong thư mục Project đã cấu hình.")
    if "request" in data and not isinstance(data["request"], str):
        raise ValueError("Yêu cầu riêng phải là văn bản.")
    return {**data, "topic_directory": str(topic), "topic": topic.name}
