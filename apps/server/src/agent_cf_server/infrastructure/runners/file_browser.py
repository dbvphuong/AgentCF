"""Short-lived, bounded metadata requests; only the authenticated PC reads its disk."""

from threading import Lock
from time import monotonic
from uuid import uuid4


class FileBrowser:
    def __init__(self):
        self._lock = Lock()
        self._requests = {}

    def _prune(self):
        now = monotonic()
        self._requests = {k: v for k, v in self._requests.items() if v["expires"] > now}

    def create(self, runner_id, path):
        with self._lock:
            self._prune()
            if len(self._requests) >= 128:
                raise ValueError("Có quá nhiều yêu cầu chọn file; thử lại sau")
            item = {"id": str(uuid4()), "runner_id": runner_id, "path": path, "status": "pending", "expires": monotonic() + 60}
            self._requests[item["id"]] = item
            return self._public(item)

    @staticmethod
    def _public(item):
        return {k: v for k, v in item.items() if k != "expires"}

    def get(self, runner_id, request_id):
        with self._lock:
            self._prune()
            item = self._requests.get(request_id)
            if not item or item["runner_id"] != runner_id:
                raise KeyError(request_id)
            return self._public(item)

    def pending(self, runner_id):
        with self._lock:
            self._prune()
            return [self._public(v) for v in self._requests.values() if v["runner_id"] == runner_id and v["status"] == "pending"][:8]

    def complete(self, runner_id, request_id, result):
        with self._lock:
            self._prune()
            item = self._requests.get(request_id)
            if not item or item["runner_id"] != runner_id:
                raise KeyError(request_id)
            if item["status"] == "pending":
                item.update(status="completed", result=result)
