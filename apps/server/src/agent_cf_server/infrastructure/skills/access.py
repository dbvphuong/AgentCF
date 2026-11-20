"""Public catalog scope check used inside publish/start transactions."""


def require_project_skill(connection, skill_id: str, project_id: str) -> None:
    allowed = connection.execute(
        "SELECT 1 FROM skills s WHERE s.id=? AND (s.is_global=1 OR EXISTS("
        "SELECT 1 FROM skill_projects sp WHERE sp.skill_id=s.id AND sp.project_id=?))",
        (skill_id, project_id),
    ).fetchone()
    if not allowed:
        raise ValueError("Skill không thuộc Project này và không phải Global")
