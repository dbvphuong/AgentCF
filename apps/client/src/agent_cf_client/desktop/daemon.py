"""One general Runner session and one task at a time, independent of the desktop UI."""

from concurrent.futures import ThreadPoolExecutor
import logging
import platform
import threading
import time

from agent_cf_client.execution.process_manager import ProcessManager
from agent_cf_client.execution.task_worker import TaskExecutionWorker
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.desktop.tray import DesktopController


class CancellableProcessManager(ProcessManager):
    def __init__(self):
        self.cancel_event = threading.Event()

    def run_process(self, *args, **kwargs):
        kwargs.setdefault("cancel_event", self.cancel_event)
        return super().run_process(*args, **kwargs)


class ClientDaemon:
    def __init__(self, manager, folder, on_status, worker_factory=TaskExecutionWorker):
        self.manager = manager
        self.folder = folder
        self.on_status = on_status
        self.desktop = DesktopController()
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.pm = CancellableProcessManager()
        self.worker = worker_factory(manager, WorkspaceManager(folder / "workspaces"), process_manager=self.pm)
        self.thread = None
        self.busy = False

    def report(self, state, message, **details):
        self.on_status({"state": state, "message": message, **details})

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self.run, name="CF Client Runner", daemon=True)
        self.thread.start()

    def shutdown(self):
        self.stop.set()  # Drain current work before closing its session.

    def run(self):
        from agent_cf_client.desktop.metrics import SystemMetrics
        metrics = SystemMetrics()
        assignment, future = None, None
        self.manager.current_session_id = None
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="CF Client Task") as executor:
            while not self.stop.is_set() or future is not None:
                if assignment and time.monotonic() >= assignment["_local_deadline"]:
                    self.pm.cancel_event.set()
                if future is not None and future.done():
                    try:
                        outcome = future.result()
                        self.report("idle", "Đã hoàn thành việc" if outcome.get("outcome") == "succeeded" else "Việc kết thúc có lỗi; xem Runs trên Web")
                    except Exception:
                        logging.exception("Attempt requires reconciliation; never automatically retry")
                        self.paused.set()
                        self.report("error", "Kết quả chưa được Server xác nhận. Đã ngừng nhận việc để đối soát; xem Runs trên Web.")
                    future, assignment = None, None
                    self.busy = False
                if self.stop.is_set() and future is None:
                    break
                try:
                    if not self.manager.current_session_id:
                        self.report("connecting", "Đang kết nối Server…")
                        capabilities = ["desktop-client-v1", "python"] + [name for name, adapter in (("codex", self.worker.codex_adapter), ("antigravity", self.worker.antigravity_adapter)) if adapter.is_available()]
                        from agent_cf_client.desktop.identity import device_identity
                        identity = device_identity(self.folder) if platform.system() == 'Windows' else {}
                        self.manager.start_session(capabilities=capabilities, client_version="0.3.4", os_name=platform.platform(), **identity)
                    running = [assignment["attempt_id"]] if assignment else []
                    heartbeat = self.manager.send_heartbeat(running_attempts=running, **metrics.sample())
                    if heartbeat.get("stop_requested"):
                        self.paused.set()
                        self.stop.set()
                    if assignment and (assignment["attempt_id"] in heartbeat.get("stop_attempt_ids", []) or time.monotonic() >= assignment["_local_deadline"]):
                        self.pm.cancel_event.set()
                    if future is None and not self.stop.is_set():
                        if self.paused.is_set():
                            self.report("paused", "Đã ngừng nhận việc mới; kết nối vẫn hoạt động")
                        elif self.desktop.is_windows_session_locked():
                            self.report("paused", "Windows đang khóa; chưa nhận việc mới")
                        else:
                            self.report("idle", "Đã kết nối · Sẵn sàng nhận việc")
                            for item in self.worker.poll_work():
                                assignment = self.worker.claim_task(item["task_run_id"], lease_seconds=3600)
                                # Existing Server grants have a fixed execution deadline. Never run
                                # past it or create a new session to revive expired execution rights.
                                from datetime import datetime, timezone
                                deadline = datetime.fromisoformat(assignment["execution_deadline_at"].replace("Z", "+00:00"))
                                assignment["_local_deadline"] = time.monotonic() + max(0, (deadline-datetime.now(timezone.utc)).total_seconds()-2)
                                self.pm.cancel_event.clear()
                                self.busy = True
                                self.report("running", "Đang thực hiện: " + assignment.get("task", {}).get("name", "Công việc"), run_id=assignment["run_id"])
                                future = executor.submit(self.worker.execute_assignment, assignment)
                                break
                except Exception as exc:
                    # Do not include codes/tokens or response payloads in desktop error text.
                    if "(401)" in str(exc) or "(403)" in str(exc):
                        self.pm.cancel_event.set()
                        self.paused.set()
                        self.stop.set()
                        self.report("error", "Kết nối hết hạn hoặc bị thu hồi. Ghép nối lại từ Web.")
                    else:
                        self.report("connecting", "Mất kết nối Server; đang thử lại. Không chạy lại việc đã nhận.")
                # Busy task and heartbeat remain alive during graceful shutdown.
                if self.stop.is_set() and future is None:
                    break
                time.sleep(1)
        try:
            self.manager.close_session()
        except Exception:
            logging.warning("Session not closed; Server freshness/reconciliation remains authoritative")
        self.manager.current_session_id = None
        self.report("disconnected", "Client đã ngắt kết nối")
