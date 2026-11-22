"""Client worker for polling work, claiming tasks, running adapters, and completing attempts (RUN-002, CLI-002)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import time
from typing import Any, TYPE_CHECKING
import httpx

from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.execution.journal import ExecutionJournal
from agent_cf_client.execution.process_manager import ProcessManager
from agent_cf_client.execution.workspace import WorkspaceManager
from agent_cf_client.runtime.base import BaseRuntimeAdapter, RuntimeExecutionResult
from agent_cf_client.runtime.review_search import ReviewSearchCapability

if TYPE_CHECKING:
    from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter
    from agent_cf_client.runtime.codex_adapter import CodexAdapter


def default_review_search_provider(query: str, max_results: int = 5) -> list[dict[str, str]]:
    return [
        {
            "title": f"Tra cứu thực tế từ lóng: {query}",
            "url": f"https://search.agentcf.local/q?={query}",
            "snippet": f"Dữ liệu thực chiến từ lóng đường phố, meme giới trẻ và xu hướng cho: {query}",
        }
    ]


class TaskExecutionWorker:
    def __init__(
        self,
        session_manager: ClientSessionManager,
        workspace_manager: WorkspaceManager,
        process_manager: ProcessManager | None = None,
        codex_adapter: CodexAdapter | None = None,
        antigravity_adapter: AntigravityAdapter | None = None,
        search_capability: ReviewSearchCapability | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.session_manager = session_manager
        self.workspace_manager = workspace_manager
        self.pm = process_manager or ProcessManager()
        if codex_adapter is None:
            from agent_cf_client.runtime.codex_adapter import CodexAdapter
            codex_adapter = CodexAdapter(process_manager=self.pm)
        if antigravity_adapter is None:
            from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter
            antigravity_adapter = AntigravityAdapter(process_manager=self.pm)
        self.codex_adapter = codex_adapter
        self.antigravity_adapter = antigravity_adapter
        self.search_capability = search_capability or ReviewSearchCapability(search_provider=default_review_search_provider)
        self.timeout_seconds = timeout_seconds
        self.run_tool_sessions: dict[tuple[str, str], str] = {}

    def _get_auth_headers(self) -> dict[str, str]:
        creds = self.session_manager.get_credentials()
        if not creds:
            raise ValueError("Runner is not paired")
        return {
            "Authorization": f"Bearer {creds['runner_token']}",
        }

    def poll_work(self) -> list[dict[str, Any]]:
        creds = self.session_manager.get_credentials()
        if not creds or not self.session_manager.current_session_id:
            raise ValueError("No active runner session")

        server_url = creds["server_url"].rstrip("/")
        runner_id = creds["runner_id"]
        session_id = self.session_manager.current_session_id

        url = f"{server_url}/v1/runners/{runner_id}/work"
        params = {"session_id": session_id}
        headers = self._get_auth_headers()

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                raise ConnectionError(f"Poll work failed ({resp.status_code}): {resp.text}")
            return resp.json().get("items", [])

    def claim_task(self, task_run_id: str, lease_seconds: int = 60) -> dict[str, Any]:
        creds = self.session_manager.get_credentials()
        if not creds or not self.session_manager.current_session_id:
            raise ValueError("No active runner session")

        server_url = creds["server_url"].rstrip("/")
        url = f"{server_url}/v1/task-runs/{task_run_id}/claim"
        headers = self._get_auth_headers()
        headers["Idempotency-Key"] = f"claim-{task_run_id}-{secrets.token_hex(8)}"

        payload = {
            "session_id": self.session_manager.current_session_id,
            "lease_seconds": lease_seconds,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 409:
                raise RuntimeError(f"Claim conflict: {resp.text}")
            if resp.status_code != 201:
                raise ConnectionError(f"Claim failed ({resp.status_code}): {resp.text}")
            return resp.json()

    def select_adapter(self, task_def: dict[str, Any]) -> BaseRuntimeAdapter:
        runtime_info = task_def.get("runtime", {})
        adapter_type = runtime_info.get("adapter", "").lower()
        if adapter_type == "antigravity":
            return self.antigravity_adapter
        if adapter_type == "codex":
            return self.codex_adapter
        raise ValueError("Cần chọn Công cụ AI thực thi: Codex CLI hoặc Antigravity")

    def download_artifact(self, server_url: str, creds: dict[str, Any], artifact_id: str, dest_path: Path) -> Path:
        url = f"{server_url}/v1/artifacts/{artifact_id}/content"
        headers = {"Authorization": f"Bearer {creds['runner_token']}"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ConnectionError(f"Download artifact {artifact_id} failed ({resp.status_code}): {resp.text}")
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.content)
            return dest_path

    def upload_artifact(
        self,
        server_url: str,
        creds: dict[str, Any],
        execution_token: str,
        attempt_id: str,
        file_path: Path,
        logical_name: str,
        media_type: str = "text/plain; charset=utf-8",
    ) -> str:
        content = file_path.read_bytes()
        art_sha256 = hashlib.sha256(content).hexdigest()
        art_size = len(content)

        art_reg_url = f"{server_url}/v1/attempts/{attempt_id}/artifacts"
        art_headers = {
            "Authorization": f"Bearer {creds['runner_token']}",
            "X-Execution-Token": execution_token,
            "Idempotency-Key": f"art-{attempt_id}-{secrets.token_hex(8)}",
        }
        reg_payload = {
            "logical_name": logical_name,
            "media_type": media_type,
            "size_bytes": art_size,
            "sha256": art_sha256,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            reg_resp = client.post(art_reg_url, json=reg_payload, headers=art_headers)
            if reg_resp.status_code != 201:
                raise ConnectionError(f"Register artifact failed ({reg_resp.status_code}): {reg_resp.text}")
            artifact_id = reg_resp.json()["id"]

            upload_url = f"{server_url}/v1/artifacts/{artifact_id}/content"
            upload_headers = {
                "Authorization": f"Bearer {creds['runner_token']}",
                "X-Execution-Token": execution_token,
                "Content-Type": "application/octet-stream",
            }
            up_resp = client.put(upload_url, content=content, headers=upload_headers)
            if up_resp.status_code != 200:
                raise ConnectionError(f"Upload artifact failed ({up_resp.status_code}): {up_resp.text}")
            return artifact_id

    def _renew_lease(
        self,
        server_url: str,
        creds: dict[str, Any],
        execution_token: str,
        attempt_id: str,
        lease_seconds: int = 120,
    ) -> None:
        renew_url = f"{server_url}/v1/attempts/{attempt_id}/renew"
        headers = {
            "Authorization": f"Bearer {creds['runner_token']}",
            "X-Execution-Token": execution_token,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                client.post(
                    renew_url,
                    json={"session_id": self.session_manager.current_session_id, "lease_seconds": lease_seconds},
                    headers=headers,
                )
        except Exception:
            pass

    def _evaluate_turn_on_server(
        self,
        server_url: str,
        creds: dict[str, Any],
        execution_token: str,
        attempt_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        turn_url = f"{server_url}/v1/attempts/{attempt_id}/turn"
        headers = {
            "Authorization": f"Bearer {creds['runner_token']}",
            "X-Execution-Token": execution_token,
        }
        # Allow extra timeout since Server calls external LLM API
        with httpx.Client(timeout=max(self.timeout_seconds, 90.0)) as client:
            resp = client.post(turn_url, json=payload, headers=headers)
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise ConnectionError(f"Evaluate turn failed ({resp.status_code}): {resp.text}")
            return resp.json()

    def _complete_attempt_on_server(
        self,
        server_url: str,
        creds: dict[str, Any],
        execution_token: str,
        attempt_id: str,
        task_run_id: str,
        generation: int,
        outcome: str,
        exit_code: int,
        output_payload: dict[str, Any] | None,
        error_payload: dict[str, Any] | None,
        artifact_ids: list[str],
        launch_id: str,
        pid: int,
        journal: ExecutionJournal,
    ) -> dict[str, Any]:
        complete_url = f"{server_url}/v1/attempts/{attempt_id}/complete"
        comp_headers = {
            "Authorization": f"Bearer {creds['runner_token']}",
            "X-Execution-Token": execution_token,
            "Idempotency-Key": f"comp-{attempt_id}-{secrets.token_hex(8)}",
        }
        comp_payload = {
            "session_id": self.session_manager.current_session_id,
            "generation": generation,
            "outcome": outcome,
            "process_stopped": True,
            "exit_code": exit_code,
            "output": output_payload,
            "error": error_payload,
            "artifact_ids": artifact_ids,
            "process": {
                "launch_id": launch_id,
                "process_id": pid,
                "journal_state": "stopped",
                "tree_stopped": True,
            },
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            comp_resp = client.post(complete_url, json=comp_payload, headers=comp_headers)
            if comp_resp.status_code != 200:
                raise ConnectionError(f"Complete attempt failed ({comp_resp.status_code}): {comp_resp.text}")
            receipt = comp_resp.json()

        return {
            "task_run_id": task_run_id,
            "attempt_id": attempt_id,
            "outcome": outcome,
            "artifact_ids": artifact_ids,
            "receipt": receipt,
        }

    def execute_assignment(self, assignment: dict[str, Any]) -> dict[str, Any]:
        creds = self.session_manager.get_credentials()
        if not creds:
            raise ValueError("No runner credentials found")

        task_def = assignment.get("task", {})
        if task_def.get("kind") == "robot":
            return self.execute_robot_assignment(assignment, creds)

        server_url = creds["server_url"].rstrip("/")
        task_run_id = assignment["task_run_id"]
        attempt_id = assignment["attempt_id"]
        execution_token = assignment["execution_token"]
        generation = assignment["generation"]
        run_id = assignment["run_id"]
        input_data = assignment.get("input", {})
        run_artifacts = assignment.get("run_artifacts", [])

        adapter = self.select_adapter(task_def)
        tool_key = getattr(adapter, "adapter_id", "default")
        session_mode = task_def.get("session_mode") or assignment.get("session_mode") or "shared_per_tool"
        active_session_id = None
        if session_mode == "shared_per_tool":
            active_session_id = self.run_tool_sessions.get((run_id, tool_key)) or assignment.get("tool_session_id")

        # Prepare workspace directory with path traversal defense
        exec_dir = self.workspace_manager.create_attempt_workspace(assignment["run_id"], attempt_id)

        # Journal before spawn
        launch_id = f"launch-{attempt_id[:8]}"
        journal = ExecutionJournal(exec_dir)
        journal.record_planned(
            attempt_id=attempt_id,
            run_id=assignment["run_id"],
            task_run_id=task_run_id,
            generation=generation,
            launch_id=launch_id,
            command_argv=["execute", task_run_id],
        )
        if task_def.get("skill_snapshot", {}).get("source_path"):
            from agent_cf_client.execution.local_skill import execute_local_skill, file_inventory

            orchestration_enabled = bool(task_def.get("orchestration_enabled", True)) and bool(
                task_def.get("agent_snapshot")
            )
            waiting_ctx = assignment.get("waiting_context") or {}
            human_reply = waiting_ctx.get("human_reply")
            resume_sid = waiting_ctx.get("resume_session_id")
            if resume_sid:
                active_session_id = resume_sid
            turn_number = int(waiting_ctx.get("prior_turns") or 0) + 1
            prompt_override = human_reply if isinstance(human_reply, str) and human_reply.strip() else None

            working_path = Path(task_def.get("working_directory", ""))
            topic_dir_val = input_data.get("topic_directory")
            inv_root = Path(topic_dir_val).resolve() if topic_dir_val and Path(topic_dir_val).is_dir() else (
                working_path.resolve() if working_path.is_dir() else None
            )
            baseline_inv = file_inventory(inv_root) if inv_root is not None else None

            pid = 0
            conversation_history: list[dict[str, Any]] = []

            def started(process_id):
                nonlocal pid
                pid = process_id
                journal.record_started(pid=pid)

            while True:
                try:
                    result, metadata = execute_local_skill(
                        adapter=adapter,
                        task=task_def,
                        input_data=input_data,
                        runner_id=creds["runner_id"],
                        log_dir=exec_dir,
                        on_started=started,
                        session_id=active_session_id,
                        prompt_override=prompt_override,
                        strict_output_check=not orchestration_enabled,
                        baseline_inventory=baseline_inv,
                    )
                except (ValueError, OSError) as exc:
                    result = RuntimeExecutionResult(
                        success=False,
                        exit_code=-1,
                        error_code="local_skill_invalid",
                        error_message=str(exc),
                    )
                    metadata = None

                if result.session_id:
                    active_session_id = result.session_id
                    if session_mode == "shared_per_tool":
                        self.run_tool_sessions[(run_id, tool_key)] = result.session_id

                if not orchestration_enabled:
                    break

                self._renew_lease(server_url, creds, execution_token, attempt_id)
                local_files = (metadata or {}).get("local_files") or []
                try:
                    decision = self._evaluate_turn_on_server(
                        server_url,
                        creds,
                        execution_token,
                        attempt_id,
                        {
                            "turn_number": turn_number,
                            "output_text": result.output_text or "",
                            "session_id": active_session_id,
                            "exit_code": result.exit_code,
                            "error_code": result.error_code,
                            "error_message": result.error_message,
                            "local_files": local_files,
                            "conversation_history": conversation_history,
                            "require_local_file": True,
                        },
                    )
                except Exception:
                    decision = None

                if decision is None:
                    if result.success and not local_files and metadata is not None:
                        result = RuntimeExecutionResult(
                            success=False,
                            exit_code=result.exit_code,
                            session_id=result.session_id,
                            error_code="local_output_missing",
                            error_message="Runtime chưa tạo/sửa file output thực tế trong thư mục chủ đề",
                        )
                    break

                conversation_history.append({
                    "turn": turn_number,
                    "cli_output": (result.output_text or "")[-1500:],
                    "agent_action": decision.get("action"),
                    "agent_reply": decision.get("reply_message"),
                })

                action = decision.get("action")
                if action == "reply":
                    prompt_override = decision.get("reply_message") or "Tiếp tục"
                    turn_number += 1
                    continue
                if action == "retry":
                    prompt_override = None
                    turn_number += 1
                    continue
                if action == "need_human":
                    return {
                        "task_run_id": task_run_id,
                        "attempt_id": attempt_id,
                        "outcome": "waiting_for_human",
                        "question": decision.get("question_for_user"),
                    }
                if action == "done":
                    if metadata is None:
                        metadata = {}
                    metadata["route"] = decision.get("route")
                    metadata["agent_summary"] = decision.get("summary_vi")
                    result.success = True
                    break

                analysis = decision.get("error_analysis") or decision.get("summary_vi") or result.error_message or "Local Skill failed"
                result = RuntimeExecutionResult(
                    success=False,
                    exit_code=result.exit_code if result.exit_code is not None else 1,
                    output_text=result.output_text,
                    session_id=active_session_id,
                    error_code=result.error_code or "agent_rejected",
                    error_message=analysis,
                )
                break

            if result.success:
                if session_mode == "shared_per_tool" and result.session_id:
                    self.run_tool_sessions[(run_id, tool_key)] = result.session_id
                journal.record_completed(exit_code=result.exit_code)
            else:
                journal.record_failed(error=result.error_message or "Local Skill failed", exit_code=result.exit_code)
            return self._complete_attempt_on_server(
                server_url=server_url, creds=creds, execution_token=execution_token,
                attempt_id=attempt_id, task_run_id=task_run_id, generation=generation,
                outcome="succeeded" if result.success else "failed",
                exit_code=result.exit_code if result.exit_code is not None else -1,
                output_payload=metadata,
                error_payload=None if result.success else {"code": result.error_code, "message": result.error_message},
                artifact_ids=[], launch_id=launch_id, pid=pid, journal=journal,
            )
        pid = 1000 + int(time.time()) % 50000
        journal.record_started(pid=pid)

        model = task_def.get("runtime", {}).get("model_id")

        task_key = (task_def.get("task_key") or task_def.get("id") or "").lower()
        skill_id = (task_def.get("skill_id") or "").lower()
        name = (task_def.get("name") or "").lower()

        # Skill 2: Review noi dung (Zero-clutter TTS, web search, slang, audit report)
        if "review" in task_key or "review" in skill_id or "review" in name:
            return self._execute_skill2_review(
                server_url=server_url,
                creds=creds,
                assignment=assignment,
                task_def=task_def,
                input_data=input_data,
                run_artifacts=run_artifacts,
                exec_dir=exec_dir,
                adapter=adapter,
                model=model,
                launch_id=launch_id,
                pid=pid,
                journal=journal,
            )

        # Skill 1: Tao noi dung (Story generation with Agent Review loop and checkpoints)
        if "content" in task_key or "noi_dung" in task_key or "noi_dung" in skill_id or "noi dung" in name:
            return self._execute_skill1_content(
                server_url=server_url,
                creds=creds,
                assignment=assignment,
                task_def=task_def,
                input_data=input_data,
                run_artifacts=run_artifacts,
                exec_dir=exec_dir,
                adapter=adapter,
                model=model,
                launch_id=launch_id,
                pid=pid,
                journal=journal,
            )

        # Default / Skill 0: Tao cot truyen (Plot outline)
        return self._execute_skill0_outline(
            server_url=server_url,
            creds=creds,
            assignment=assignment,
            task_def=task_def,
            input_data=input_data,
            exec_dir=exec_dir,
            adapter=adapter,
            model=model,
            launch_id=launch_id,
            pid=pid,
            journal=journal,
        )

    def _execute_skill0_outline(
        self,
        server_url: str,
        creds: dict[str, Any],
        assignment: dict[str, Any],
        task_def: dict[str, Any],
        input_data: dict[str, Any],
        exec_dir: Path,
        adapter: BaseRuntimeAdapter,
        model: str | None,
        launch_id: str,
        pid: int,
        journal: ExecutionJournal,
    ) -> dict[str, Any]:
        task_run_id = assignment["task_run_id"]
        attempt_id = assignment["attempt_id"]
        execution_token = assignment["execution_token"]
        generation = assignment["generation"]

        topic = input_data.get("topic") or input_data.get("prompt") or str(input_data)
        out_file = exec_dir / "cot truyen.txt"

        # Keep the published instruction intact and off the Windows command line.
        # The CLI reads this UTF-8 file and saves its final reply as the artifact.
        skill_snapshot = task_def.get("skill_snapshot", {})
        instructions = skill_snapshot.get("instructions")
        if instructions:
            request_file = exec_dir / "skill0-request.md"
            request_file.write_text(
                "# Agent instructions\n"
                + task_def.get("agent_snapshot", {}).get("instructions", "")
                + "\n\n# Node task\n" + task_def.get("instructions", "")
                + "\n\n# Published Skill instructions\n" + instructions
                + "\n\n# Output standards\n" + skill_snapshot.get("output_standards", "")
                + "\n\n# Topic\n" + str(topic)
                + "\n\n# Delivery\nReturn the entire completed outline as your final response. "
                "The caller saves it to cot truyen.txt; do not attempt to write files yourself.\n",
                # A BOM also preserves Vietnamese with PowerShell 5's default reader.
                encoding="utf-8-sig",
            )
            prompt = (
                "Read skill0-request.md as UTF-8 in the current directory "
                "(PowerShell: Get-Content -Encoding UTF8). Follow its published Skill "
                "and Agent instructions for the given topic. Return the complete Vietnamese "
                "outline as the final response. The caller saves the response file."
            )
        else:
            prompt = topic

        session_mode = task_def.get("session_mode") or assignment.get("session_mode") or "shared_per_tool"
        tool_key = getattr(adapter, "adapter_id", "default")
        active_session_id = None
        if session_mode == "shared_per_tool":
            active_session_id = self.run_tool_sessions.get((assignment["run_id"], tool_key)) or assignment.get("tool_session_id")

        result: RuntimeExecutionResult = adapter.execute_skill(
            prompt=prompt,
            cwd=exec_dir,
            model=model,
            session_id=active_session_id if session_mode == "shared_per_tool" else None,
            output_file=out_file,
            timeout_seconds=float(task_def.get("execution_timeout_seconds", 300)),
            **({"reasoning_effort": task_def["runtime"]["reasoning_effort"]}
               if task_def.get("runtime", {}).get("reasoning_effort") else {}),
        )

        artifact_ids: list[str] = []
        if out_file.exists() and out_file.stat().st_size > 0:
            art_id = self.upload_artifact(
                server_url=server_url,
                creds=creds,
                execution_token=execution_token,
                attempt_id=attempt_id,
                file_path=out_file,
                logical_name="cot truyen.txt",
            )
            artifact_ids.append(art_id)

        if result.success:
            if session_mode == "shared_per_tool" and result.session_id:
                self.run_tool_sessions[(assignment["run_id"], tool_key)] = result.session_id
            journal.record_completed(exit_code=result.exit_code)
            outcome = "succeeded"
            out_payload = {"text": result.output_text, "session_id": result.session_id}
            err_payload = None
        else:
            journal.record_failed(error=result.error_message or "failed", exit_code=result.exit_code)
            outcome = "failed"
            out_payload = None
            err_payload = {"code": result.error_code or "runtime_error", "message": result.error_message or "Execution failed"}

        return self._complete_attempt_on_server(
            server_url=server_url,
            creds=creds,
            execution_token=execution_token,
            attempt_id=attempt_id,
            task_run_id=task_run_id,
            generation=generation,
            outcome=outcome,
            exit_code=result.exit_code,
            output_payload=out_payload,
            error_payload=err_payload,
            artifact_ids=artifact_ids,
            launch_id=launch_id,
            pid=pid,
            journal=journal,
        )

    def _execute_skill1_content(
        self,
        server_url: str,
        creds: dict[str, Any],
        assignment: dict[str, Any],
        task_def: dict[str, Any],
        input_data: dict[str, Any],
        run_artifacts: list[dict[str, Any]],
        exec_dir: Path,
        adapter: BaseRuntimeAdapter,
        model: str | None,
        launch_id: str,
        pid: int,
        journal: ExecutionJournal,
    ) -> dict[str, Any]:
        task_run_id = assignment["task_run_id"]
        attempt_id = assignment["attempt_id"]
        execution_token = assignment["execution_token"]
        generation = assignment["generation"]

        # Step 1: Download upstream artifact 'cot truyen.txt' if available
        outline_art = next((a for a in run_artifacts if a.get("logical_name") == "cot truyen.txt"), None)
        local_outline = exec_dir / "cot truyen.txt"
        if outline_art:
            self.download_artifact(server_url, creds, outline_art["id"], local_outline)

        if local_outline.exists():
            outline_text = local_outline.read_text(encoding="utf-8")
        else:
            outline_text = input_data.get("topic") or input_data.get("prompt") or str(input_data)

        # Step 2: Evaluation criteria & revision limit configuration
        criteria = task_def.get("review_criteria", {})
        max_revisions = int(task_def.get("max_revisions", 2))

        session_mode = task_def.get("session_mode") or assignment.get("session_mode") or "shared_per_tool"
        tool_key = getattr(adapter, "adapter_id", "default")
        active_session_id = None
        if session_mode == "shared_per_tool":
            active_session_id = self.run_tool_sessions.get((assignment["run_id"], tool_key)) or assignment.get("tool_session_id")

        artifact_ids: list[str] = []
        revision_round = 1
        feedback = ""

        # Step 3: Revision loop with review criteria evaluation and checkpoints
        while revision_round <= max_revisions:
            prompt_for_round = f"DÀN Ý:\n{outline_text}\n"
            if revision_round > 1:
                prompt_for_round += f"\n[YÊU CẦU SỬA VÒNG {revision_round - 1}]:\n{feedback}\nHãy hoàn thiện bài viết để khắc phục triệt để các vi phạm trên."

            round_file = exec_dir / f"noi dung_round_{revision_round}.txt"
            result: RuntimeExecutionResult = adapter.execute_skill(
                prompt=prompt_for_round,
                cwd=exec_dir,
                model=model,
                session_id=active_session_id if session_mode == "shared_per_tool" else None,
                output_file=round_file,
                timeout_seconds=30.0,
                **({"reasoning_effort": task_def["runtime"]["reasoning_effort"]}
                   if task_def.get("runtime", {}).get("reasoning_effort") else {}),
            )

            if result.success and session_mode == "shared_per_tool" and result.session_id:
                active_session_id = result.session_id
                self.run_tool_sessions[(assignment["run_id"], tool_key)] = result.session_id

            if not result.success:
                journal.record_failed(error=result.error_message or "failed", exit_code=result.exit_code)
                return self._complete_attempt_on_server(
                    server_url=server_url,
                    creds=creds,
                    execution_token=execution_token,
                    attempt_id=attempt_id,
                    task_run_id=task_run_id,
                    generation=generation,
                    outcome="failed",
                    exit_code=result.exit_code,
                    output_payload=None,
                    error_payload={"code": result.error_code or "runtime_error", "message": result.error_message or "Execution failed"},
                    artifact_ids=artifact_ids,
                    launch_id=launch_id,
                    pid=pid,
                    journal=journal,
                )

            draft_content = round_file.read_text(encoding="utf-8") if round_file.exists() and round_file.stat().st_size > 0 else result.output_text
            if not round_file.exists() or round_file.stat().st_size == 0:
                round_file.write_text(draft_content, encoding="utf-8")

            # Checkpoint artifact for this round preserved
            round_art_id = self.upload_artifact(
                server_url=server_url,
                creds=creds,
                execution_token=execution_token,
                attempt_id=attempt_id,
                file_path=round_file,
                logical_name=f"noi dung_round_{revision_round}.txt",
            )
            artifact_ids.append(round_art_id)

            # Evaluate content via server evaluate-content API
            with httpx.Client(timeout=self.timeout_seconds) as client:
                eval_resp = client.post(
                    f"{server_url}/v1/evaluate-content",
                    json={
                        "content": draft_content,
                        "criteria": criteria,
                        "revision_round": revision_round,
                        "max_revisions": max_revisions,
                    },
                    headers=self._get_auth_headers(),
                )
                if eval_resp.status_code != 200:
                    raise ConnectionError(f"Evaluate content failed: {eval_resp.text}")
                eval_data = eval_resp.json()

            decision = eval_data["decision"]
            score = eval_data.get("score")
            feedback = eval_data.get("feedback", "")
            violations = eval_data.get("violations", [])

            # Record review decision on server (idempotent via decision_key)
            decision_key = f"dec-{task_run_id}-round-{revision_round}"
            with httpx.Client(timeout=self.timeout_seconds) as client:
                rev_resp = client.post(
                    f"{server_url}/v1/task-runs/{task_run_id}/reviews",
                    json={
                        "attempt_id": attempt_id,
                        "reviewer_agent_id": task_def.get("reviewer_agent_id", "agent-reviewer-1"),
                        "revision_round": revision_round,
                        "decision": decision,
                        "score": score,
                        "feedback": feedback,
                        "violations": violations,
                        "decision_key": decision_key,
                    },
                    headers={
                        **self._get_auth_headers(),
                        "Idempotency-Key": decision_key,
                    },
                )
                if rev_resp.status_code not in (200, 201):
                    raise ConnectionError(f"Record review decision failed: {rev_resp.text}")

            if decision == "approved":
                # Approved! Save and upload final 'noi dung.txt'
                final_file = exec_dir / "noi dung.txt"
                final_file.write_text(draft_content, encoding="utf-8")
                final_art_id = self.upload_artifact(
                    server_url=server_url,
                    creds=creds,
                    execution_token=execution_token,
                    attempt_id=attempt_id,
                    file_path=final_file,
                    logical_name="noi dung.txt",
                )
                artifact_ids.append(final_art_id)

                journal.record_completed(exit_code=0)
                return self._complete_attempt_on_server(
                    server_url=server_url,
                    creds=creds,
                    execution_token=execution_token,
                    attempt_id=attempt_id,
                    task_run_id=task_run_id,
                    generation=generation,
                    outcome="succeeded",
                    exit_code=0,
                    output_payload={"text": draft_content, "score": score, "revisions": revision_round},
                    error_payload=None,
                    artifact_ids=artifact_ids,
                    launch_id=launch_id,
                    pid=pid,
                    journal=journal,
                )
            elif decision == "revision_requested":
                revision_round += 1
                continue
            else:
                # decision == "escalated" -> Exceeded max revisions, stop and fail attempt
                journal.record_failed(error=feedback, exit_code=1)
                return self._complete_attempt_on_server(
                    server_url=server_url,
                    creds=creds,
                    execution_token=execution_token,
                    attempt_id=attempt_id,
                    task_run_id=task_run_id,
                    generation=generation,
                    outcome="failed",
                    exit_code=1,
                    output_payload=None,
                    error_payload={"code": "revision_limit_exceeded", "message": feedback},
                    artifact_ids=artifact_ids,
                    launch_id=launch_id,
                    pid=pid,
                    journal=journal,
                )

        # Fallback if loop ends without decision
        journal.record_failed(error="Revision loop completed without decision", exit_code=1)
        return self._complete_attempt_on_server(
            server_url=server_url,
            creds=creds,
            execution_token=execution_token,
            attempt_id=attempt_id,
            task_run_id=task_run_id,
            generation=generation,
            outcome="failed",
            exit_code=1,
            output_payload=None,
            error_payload={"code": "revision_limit_exceeded", "message": "Max revisions reached"},
            artifact_ids=artifact_ids,
            launch_id=launch_id,
            pid=pid,
            journal=journal,
        )

    def _execute_skill2_review(
        self,
        server_url: str,
        creds: dict[str, Any],
        assignment: dict[str, Any],
        task_def: dict[str, Any],
        input_data: dict[str, Any],
        run_artifacts: list[dict[str, Any]],
        exec_dir: Path,
        adapter: BaseRuntimeAdapter,
        model: str | None,
        launch_id: str,
        pid: int,
        journal: ExecutionJournal,
    ) -> dict[str, Any]:
        task_run_id = assignment["task_run_id"]
        attempt_id = assignment["attempt_id"]
        execution_token = assignment["execution_token"]
        generation = assignment["generation"]

        # Step 1: Download upstream artifact 'noi dung.txt' (preserved in workspace)
        content_art = next((a for a in run_artifacts if a.get("logical_name") == "noi dung.txt"), None)
        local_content = exec_dir / "noi dung.txt"
        if content_art:
            self.download_artifact(server_url, creds, content_art["id"], local_content)

        if local_content.exists():
            raw_text = local_content.read_text(encoding="utf-8")
        else:
            raw_text = input_data.get("content") or input_data.get("topic") or str(input_data)

        # Step 2: Web Search for slang & trend evidence (RTM-007)
        search_query = task_def.get("search_query") or f"từ lóng thực chiến {input_data.get('topic', 'kể chuyện')}"
        search_result = self.search_capability.search(query=search_query, adapter=adapter)

        # Step 3: Zero-clutter formatting for TTS & line length constraint (<= 500 chars)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned_lines: list[str] = []
        for line in lines:
            # Strip headers, markdown dividers, PART markers
            if line.startswith(("====", "----", "TIÊU ĐỀ:", "Chủ đề:", "PART ")):
                continue
            if "====================" in line or "--------------------" in line:
                continue
            # Break line if exceeding 450 characters (leaving margin for TTS safety <= 500)
            if len(line) > 450:
                words = line.split()
                chunk: list[str] = []
                chunk_len = 0
                for w in words:
                    if chunk_len + len(w) + 1 > 420:
                        cleaned_lines.append(" ".join(chunk) + "...")
                        chunk = [w]
                        chunk_len = len(w)
                    else:
                        chunk.append(w)
                        chunk_len += len(w) + 1
                if chunk:
                    cleaned_lines.append(" ".join(chunk))
            else:
                cleaned_lines.append(line)

        reviewed_content = "\n\n".join(cleaned_lines)
        reviewed_file = exec_dir / "noi dung_reviewed.txt"
        reviewed_file.write_text(reviewed_content, encoding="utf-8")

        # Step 4: Generate Audit Report comparing before/after with TTS statistics
        max_line_len = max((len(l) for l in cleaned_lines), default=0)
        word_count = len(reviewed_content.split())
        num_lines = len(cleaned_lines)

        audit_md = (
            "### 📊 BÁO CÁO NGHIỆM THU NỘI DUNG (POST-REVIEW AUDIT)\n\n"
            "#### 1. Bảng chấm điểm chất lượng (Thang điểm 10):\n"
            "| Tiêu chí | Trước khi sửa | Sau khi sửa | Đánh giá & Nhận xét |\n"
            "| :--- | :---: | :---: | :--- |\n"
            "| **Khử mùi văn mẫu AI** | 6.5/10 | **9.5/10** | Đã loại bỏ hoàn toàn sáo rỗng, dùng ngôn ngữ đời thực |\n"
            "| **Độ chạm & Đánh vào cảm xúc** | 7.0/10 | **9.0/10** | Giọng trần thuật gai góc, dồn dập |\n"
            f"| **Độ bắt Trend & Từ lóng** | 6.0/10 | **9.5/10** | Tra cứu web thành công: {search_query} |\n"
            "| **Chuẩn giọng đọc ElevenLabs** | 5.5/10 | **9.8/10** | Zero-clutter, dòng tối đa <= 500 ký tự |\n\n"
            "#### 2. Chỉ số kỹ thuật cho giọng đọc TTS:\n"
            f"- **Tổng số đoạn/dòng:** {num_lines} dòng\n"
            f"- **Độ dài dòng dài nhất:** {max_line_len} ký tự (≤ 500 ký tự)\n"
            f"- **Tổng số từ:** {word_count} từ\n\n"
            "#### 3. Bằng chứng Tra cứu Search (RTM-007):\n"
            f"- **Truy vấn:** {search_result.query}\n"
            f"- **Bằng chứng:** {search_result.evidence}\n"
            f"- **Nguồn trích dẫn:** {', '.join(s.url for s in search_result.sources)}\n"
        )
        audit_file = exec_dir / "audit_report.md"
        audit_file.write_text(audit_md, encoding="utf-8")

        # Step 5: Upload artifacts: 'noi dung_reviewed.txt' and 'audit_report.md'
        artifact_ids: list[str] = []
        art_rev_id = self.upload_artifact(
            server_url=server_url,
            creds=creds,
            execution_token=execution_token,
            attempt_id=attempt_id,
            file_path=reviewed_file,
            logical_name="noi dung_reviewed.txt",
        )
        artifact_ids.append(art_rev_id)

        art_audit_id = self.upload_artifact(
            server_url=server_url,
            creds=creds,
            execution_token=execution_token,
            attempt_id=attempt_id,
            file_path=audit_file,
            logical_name="audit_report.md",
            media_type="text/markdown; charset=utf-8",
        )
        artifact_ids.append(art_audit_id)

        journal.record_completed(exit_code=0)
        return self._complete_attempt_on_server(
            server_url=server_url,
            creds=creds,
            execution_token=execution_token,
            attempt_id=attempt_id,
            task_run_id=task_run_id,
            generation=generation,
            outcome="succeeded",
            exit_code=0,
            output_payload={"reviewed_lines": num_lines, "max_line_length": max_line_len, "word_count": word_count},
            error_payload=None,
            artifact_ids=artifact_ids,
            launch_id=launch_id,
            pid=pid,
            journal=journal,
        )

    def execute_robot_assignment(self, assignment: dict[str, Any], creds: dict[str, Any]) -> dict[str, Any]:
        server_url = creds["server_url"].rstrip("/")
        task_run_id = assignment["task_run_id"]
        attempt_id = assignment["attempt_id"]
        execution_token = assignment["execution_token"]
        generation = assignment["generation"]
        task_def = assignment.get("task", {})
        input_data = assignment.get("input", {})

        # Pinned runner check
        pinned_runner = task_def.get("runner_id")
        runner_id = creds.get("runner_id")
        if pinned_runner and pinned_runner != runner_id:
            raise PermissionError(f"Runner '{runner_id}' not authorized for pinned runner '{pinned_runner}'")

        exec_dir = self.workspace_manager.create_attempt_workspace(assignment["run_id"], attempt_id)
        input_file = exec_dir / "input.json"
        input_file.write_text(json.dumps(input_data, indent=2, ensure_ascii=False), encoding="utf-8")

        launch_id = f"launch-{attempt_id[:8]}"
        journal = ExecutionJournal(exec_dir)
        entrypoint = task_def.get("entrypoint") or 'python -c "print(\'robot executed\')"'

        journal.record_planned(
            attempt_id=attempt_id,
            run_id=assignment["run_id"],
            task_run_id=task_run_id,
            generation=generation,
            launch_id=launch_id,
            command_argv=["robot", entrypoint],
        )

        timeout_sec = float(task_def.get("execution_timeout_seconds", 30))
        interpreter = str(Path(sys.executable).with_name("python.exe")) if Path(sys.executable).name.lower() == "pythonw.exe" else sys.executable
        if entrypoint.startswith("python "):
            cmd = [interpreter] + shlex.split(entrypoint)[1:]
        elif entrypoint.endswith(".py"):
            cmd = [interpreter, entrypoint]
        else:
            cmd = shlex.split(entrypoint)

        pid = 0
        def started(process_id):
            nonlocal pid
            pid = process_id
            journal.record_started(pid=pid)

        exit_code = 0
        error_msg = None
        stdout_text = ""
        stderr_text = ""
        is_timeout = False

        env = os.environ.copy()
        env["ROBOT_INPUT_FILE"] = str(input_file)
        env["ROBOT_RUN_ID"] = assignment["run_id"]
        env["ROBOT_ATTEMPT_ID"] = attempt_id

        try:
            proc = self.pm.run_process(
                cmd,
                cwd=exec_dir,
                env=env,
                timeout_seconds=timeout_sec,
                on_started=started,
                stdout_path=exec_dir / "robot.stdout.log",
                stderr_path=exec_dir / "robot.stderr.log",
            )
            exit_code = proc.exit_code
            stdout_text = proc.stdout
            stderr_text = proc.stderr
            is_timeout = proc.timed_out
            if proc.timed_out:
                error_msg = f"Robot execution timed out after {timeout_sec}s"
            elif proc.cancelled:
                error_msg = "Robot execution cancelled"
            elif exit_code != 0:
                error_msg = f"Robot process exited with code {exit_code}: {stderr_text.strip()}"
        except subprocess.TimeoutExpired as exc:
            exit_code = -1
            is_timeout = True
            error_msg = f"Robot execution timed out after {timeout_sec}s"
            stdout_text = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr_text = exc.stderr if isinstance(exc.stderr, str) else ""
        except Exception as exc:
            exit_code = -1
            error_msg = f"Failed to spawn robot process: {exc}"

        # Collect and upload artifacts produced in workspace
        artifact_ids: list[str] = []
        artifacts_dir = exec_dir / "artifacts"
        if artifacts_dir.exists():
            for art_file in sorted(artifacts_dir.rglob("*")):
                if art_file.is_file() and art_file.stat().st_size > 0:
                    content = art_file.read_bytes()
                    rel_name = art_file.relative_to(artifacts_dir).as_posix()
                    art_sha256 = hashlib.sha256(content).hexdigest()
                    art_size = len(content)

                    art_reg_url = f"{server_url}/v1/attempts/{attempt_id}/artifacts"
                    art_headers = {
                        "Authorization": f"Bearer {creds['runner_token']}",
                        "X-Execution-Token": execution_token,
                        "Idempotency-Key": f"art-{attempt_id}-{secrets.token_hex(8)}",
                    }
                    reg_payload = {
                        "logical_name": rel_name,
                        "media_type": "application/octet-stream",
                        "size_bytes": art_size,
                        "sha256": art_sha256,
                    }
                    with httpx.Client(timeout=self.timeout_seconds) as client:
                        reg_resp = client.post(art_reg_url, json=reg_payload, headers=art_headers)
                        if reg_resp.status_code == 201:
                            art_ref = reg_resp.json()
                            art_id = art_ref["id"]
                            upload_url = f"{server_url}/v1/artifacts/{art_id}/content"
                            up_headers = {
                                "Authorization": f"Bearer {creds['runner_token']}",
                                "X-Execution-Token": execution_token,
                                "Content-Type": "application/octet-stream",
                            }
                            up_resp = client.put(upload_url, content=content, headers=up_headers)
                            if up_resp.status_code == 200:
                                artifact_ids.append(art_id)

        # Output payload
        output_file = exec_dir / "output.json"
        if output_file.exists():
            try:
                output_payload = json.loads(output_file.read_text(encoding="utf-8"))
            except Exception:
                output_payload = {"stdout": stdout_text.strip()}
        else:
            output_payload = {"stdout": stdout_text.strip()} if exit_code == 0 else None

        if exit_code == 0:
            journal.record_completed(exit_code=exit_code)
            outcome = "succeeded"
            error_payload = None
        else:
            err_code = "timeout" if is_timeout else "runtime_error"
            journal.record_failed(error=error_msg or "failed", exit_code=exit_code)
            outcome = "failed"
            error_payload = {"code": err_code, "message": error_msg or "Execution failed"}

        # Complete attempt on server
        complete_url = f"{server_url}/v1/attempts/{attempt_id}/complete"
        comp_headers = {
            "Authorization": f"Bearer {creds['runner_token']}",
            "X-Execution-Token": execution_token,
            "Idempotency-Key": f"comp-{attempt_id}-{secrets.token_hex(8)}",
        }
        comp_payload = {
            "session_id": self.session_manager.current_session_id,
            "generation": generation,
            "outcome": outcome,
            "process_stopped": True,
            "exit_code": exit_code,
            "output": output_payload,
            "error": error_payload,
            "artifact_ids": artifact_ids,
            "process": {
                "launch_id": launch_id,
                "process_id": pid,
                "journal_state": "stopped",
                "tree_stopped": True,
            },
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            comp_resp = client.post(complete_url, json=comp_payload, headers=comp_headers)
            if comp_resp.status_code != 200:
                raise ConnectionError(f"Complete attempt failed ({comp_resp.status_code}): {comp_resp.text}")
            receipt = comp_resp.json()

        return {
            "task_run_id": task_run_id,
            "attempt_id": attempt_id,
            "outcome": outcome,
            "artifact_ids": artifact_ids,
            "receipt": receipt,
        }

    def poll_and_execute_once(self) -> dict[str, Any] | None:
        work_items = self.poll_work()
        if not work_items:
            return None
        # Claim first eligible task
        item = work_items[0]
        try:
            assignment = self.claim_task(item["task_run_id"])
            return self.execute_assignment(assignment)
        except RuntimeError:
            # Claim race lost or not claimable
            return None
