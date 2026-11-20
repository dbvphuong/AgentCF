"""Human-readable deletion blockers shared by the local operator catalogs."""

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any


def reference_list(labels: Iterable[str]) -> str:
    """Keep messages readable while explicitly reporting omitted references."""
    items = list(dict.fromkeys(labels))
    result = "; ".join(items[:8])
    if len(items) > 8:
        result += f"; và {len(items) - 8} mục khác"
    return result


def run_label(row: Mapping[str, Any]) -> str:
    status = {
        "queued": "đang chờ", "running": "đang chạy", "reconciling": "đang đối soát",
        "cancelling": "đang dừng", "succeeded": "đã thành công", "failed": "đã lỗi", "cancelled": "đã hủy",
    }.get(row["status"], "chưa kết thúc")
    timestamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    local_time = timestamp.astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M:%S")
    return f'Process “{row["process_name"]}” trong Project “{row["project_name"]}”, Run tạo lúc {local_time} (giờ Việt Nam, {status})'


RUN_CONTEXT = (
    "SELECT r.created_at,r.status,p.name AS process_name,pr.name AS project_name "
    "FROM process_runs r JOIN processes p ON p.id=r.process_id "
    "JOIN projects pr ON pr.id=r.project_id "
)
