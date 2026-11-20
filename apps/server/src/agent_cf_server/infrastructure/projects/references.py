"""Catalog deletion is blocked by actual node references in any saved Process version."""


def process_using(connection, kind: str, resource_id: str):
    keys = {"skill": ("skill_id",), "agent": ("agent_id", "reviewer_agent_id")}[kind]
    conditions = " OR ".join(f"json_extract(node.value, '$.{key}')=?" for key in keys)
    return connection.execute(
        "SELECT p.name,pr.name AS project_name,COALESCE(json_extract(node.value,'$.name'),'Bước chưa có tên') AS task_name,"
        "'cấu hình Process' AS source FROM processes p JOIN projects pr ON pr.id=p.project_id "
        "LEFT JOIN process_versions legacy ON legacy.process_id=p.id AND p.configuration_json IS NULL "
        "JOIN json_each(COALESCE(p.configuration_json,legacy.definition_json), '$.tasks') node WHERE " + conditions +
        " UNION ALL SELECT p.name,pr.name,COALESCE(json_extract(node.value,'$.name'),'Bước chưa có tên'),"
        "'snapshot của Run chưa kết thúc' FROM process_runs r JOIN processes p ON p.id=r.process_id "
        "JOIN projects pr ON pr.id=p.project_id "
        "JOIN process_versions v ON v.id=r.process_version_id JOIN json_each(v.definition_json,'$.tasks') node "
        "WHERE r.status NOT IN ('succeeded','failed','cancelled') AND (" + conditions + ") LIMIT 1",
        (resource_id,) * (len(keys) * 2),
    ).fetchone()
