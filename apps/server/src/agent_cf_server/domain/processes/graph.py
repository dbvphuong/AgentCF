"""Validate editable task graphs before they become immutable snapshots."""

from typing import Any


def validate_graph(definition: dict[str, Any]) -> None:
    tasks = definition.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Process cần ít nhất một node")
    if any(not isinstance(task, dict) for task in tasks):
        raise ValueError("Node phải là JSON object")
    dependencies = definition.get("dependencies", [])
    if not isinstance(dependencies, list) or any(not isinstance(edge, dict) for edge in dependencies):
        raise ValueError("Dependencies phải là danh sách JSON object")
    ids = [t.get("id") for t in tasks]
    keys = [t.get("task_key") for t in tasks]
    if any(not isinstance(i, str) or not i.strip() for i in ids + keys):
        raise ValueError("Node cần ID và task_key không rỗng")
    if len(set(ids)) != len(ids) or len(set(keys)) != len(keys):
        raise ValueError("ID hoặc task_key của node bị trùng")
    parents: dict[str, set[str]] = {i: set() for i in ids}
    edges = set()
    for edge in dependencies:
        source, target = edge.get("source_task_id"), edge.get("target_task_id")
        if not isinstance(source, str) or not isinstance(target, str) or source not in parents or target not in parents or source == target:
            raise ValueError(f"Dependency không hợp lệ: {source} → {target}")
        if (source, target) in edges:
            raise ValueError("Dependency bị trùng")
        edges.add((source, target))
        parents[target].add(source)
    ancestors: dict[str, set[str]] = {}
    visiting = set()

    def visit(node: str) -> set[str]:
        if node in visiting:
            raise ValueError(f"Graph có chu trình tại node {node}")
        if node in ancestors:
            return ancestors[node]
        visiting.add(node)
        result = set(parents[node])
        for parent in parents[node]:
            result.update(visit(parent))
        visiting.remove(node)
        ancestors[node] = result
        return result

    for task in tasks:
        tid = task["id"]
        visit(tid)
        if not isinstance(task.get("name"), str) or not task["name"].strip():
            raise ValueError(f"Node {tid}: thiếu tên")
        if task.get("kind") not in ("agent", "robot"):
            raise ValueError(f"Node {tid}: loại node không hợp lệ")
        if "instructions" in task and not isinstance(task["instructions"], str):
            raise ValueError(f"Node {tid}: Nhiệm vụ phải là văn bản")
        for field in ("agent_id", "skill_id", "robot_version_id", "runner_id"):
            if field in task and not isinstance(task[field], str):
                raise ValueError(f"Node {tid}: {field} phải là chuỗi")
        if task["kind"] == "agent" and not isinstance(task.get("runtime"), dict):
            raise ValueError(f"Node {tid}: runtime phải là JSON object")
        if task["kind"] == "agent":
            runtime = task["runtime"]
            effort = runtime.get("reasoning_effort")
            levels = {"codex": ("low", "medium", "high", "xhigh", "max"),
                      "antigravity": ("low", "medium", "high")}
            if effort is not None and effort not in levels.get(runtime.get("adapter"), ()):
                raise ValueError(f"Node {tid}: Mức suy luận không hợp lệ cho công cụ đã chọn")
        for key in ("input_schema", "output_schema"):
            if not isinstance(task.get(key, {}), (dict, bool)):
                raise ValueError(f"Node {tid}: {key} phải là JSON Schema")
        timeout = task.get("execution_timeout_seconds", 300)
        if not isinstance(timeout, int) or not 1 <= timeout <= 86400:
            raise ValueError(f"Node {tid}: timeout phải từ 1–86400 giây")
        targets = set()
        mapping = task.get("input_mapping", [])
        if not isinstance(mapping, list):
            raise ValueError(f"Node {tid}: input_mapping phải là danh sách")
        for binding in mapping:
            if not isinstance(binding, dict):
                raise ValueError(f"Node {tid}: mỗi binding phải là JSON object")
            target = binding.get("target")
            source = binding.get("source")
            if not isinstance(target, str) or not target or target in targets:
                raise ValueError(f"Node {tid}: trường mapping rỗng hoặc trùng")
            targets.add(target)
            if source not in ("literal", "run_input", "task_output"):
                raise ValueError(f"Node {tid}: nguồn mapping không hợp lệ")
            if source == "task_output" and (not isinstance(binding.get("task_id"), str) or binding["task_id"] not in ancestors[tid]):
                raise ValueError(f"Node {tid}: mapping phải lấy output từ node tổ tiên")
            if source == "literal" and "value" not in binding:
                raise ValueError(f"Node {tid}: literal mapping thiếu value")
            pointer = binding.get("pointer")
            if source != "literal" and (not isinstance(pointer, str) or pointer and not pointer.startswith("/")):
                raise ValueError(f"Node {tid}: JSON Pointer không hợp lệ")
