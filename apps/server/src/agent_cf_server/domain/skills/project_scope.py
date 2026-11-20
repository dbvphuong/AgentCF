"""Skill availability belongs to its Project assignments or Global scope."""


def validate_scope(is_global: bool, project_ids: list[str]) -> None:
    if is_global and project_ids:
        raise ValueError("Global không được chọn cùng Project cụ thể")
    if not is_global and not project_ids:
        raise ValueError("Chọn ít nhất một Project hoặc Global")
    if any(not isinstance(pid, str) or not pid.strip() for pid in project_ids):
        raise ValueError("Project ID không hợp lệ")
