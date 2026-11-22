"""Agent orchestration decision engine reading CLI output and controlling execution flow."""

from __future__ import annotations

import json
from typing import Any

from agent_cf_server.infrastructure.agents.llm_gateway import LLMGateway, LLMGatewayError

_MAX_OUTPUT_CHARS = 12000

DEFAULT_ORCHESTRATION_PROMPT = (
    "Kiểm tra kết quả công cụ AI trả về và tình trạng file đã tạo/sửa:\n"
    "- Chọn done: khi công việc đã hoàn thành đúng mục tiêu và có kết quả hợp lệ.\n"
    "- Chọn reply: khi công cụ hỏi có tiếp tục không (ví dụ viết Part tiếp theo), hỏi xác nhận đơn giản "
    "hoặc cần nhắc hoàn tất ghi file -> nhập câu trả lời ngắn gọn.\n"
    "- Chọn need_human: khi công cụ hỏi quyết định nghiệp vụ quan trọng, thiếu thông tin từ chủ dự án "
    "hoặc cần đăng nhập/thao tác tay.\n"
    "- Chọn retry: khi gặp lỗi mạng, timeout hoặc CLI ngắt tạm thời.\n"
    "- Chọn fail: khi lỗi không tự xử lý được -> giải thích rõ nguyên nhân và cách khắc phục bằng tiếng Việt."
)


def _truncate_tail(text: str, limit: int = _MAX_OUTPUT_CHARS) -> str:
    clean = (text or "").strip()
    if len(clean) <= limit:
        return clean
    return "...(đã lược bớt phần đầu)...\n" + clean[-limit:]


class AgentOrchestrator:
    """Evaluates a completed local CLI/Robot turn using the Agent's configured API model."""

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway or LLMGateway()

    def evaluate_turn(
        self,
        *,
        provider: dict[str, Any],
        model: dict[str, Any],
        agent: dict[str, Any],
        task_def: dict[str, Any],
        run_input: dict[str, Any],
        available_routes: list[dict[str, str]],
        turn_number: int,
        output_text: str,
        local_files: list[dict[str, Any]],
        exit_code: int | None,
        error_code: str | None,
        error_message: str | None,
        conversation_history: list[dict[str, Any]],
        require_local_file: bool = True,
    ) -> dict[str, Any]:
        allow_reply = bool(agent.get("allow_reply", True))
        allow_retry = bool(agent.get("allow_retry", True))
        allow_need_human = bool(agent.get("allow_need_human", True))
        max_turns = max(1, int(agent.get("max_turns") or 10))
        can_reply_more = allow_reply and turn_number < max_turns

        allowed_actions = ["done", "fail"]
        if can_reply_more:
            allowed_actions.append("reply")
        if allow_need_human:
            allowed_actions.append("need_human")
        if allow_retry and turn_number < max_turns:
            allowed_actions.append("retry")

        agent_rules = str(agent.get("instructions") or "").strip() or DEFAULT_ORCHESTRATION_PROMPT
        system_prompt = self._build_system_prompt(
            allowed_actions=allowed_actions,
            available_routes=available_routes,
            require_local_file=require_local_file,
        )
        user_prompt = self._build_user_prompt(
            agent_name=str(agent.get("name") or "Agent điều phối"),
            agent_rules=agent_rules,
            task_def=task_def,
            run_input=run_input,
            available_routes=available_routes,
            turn_number=turn_number,
            max_turns=max_turns,
            output_text=output_text,
            local_files=local_files,
            exit_code=exit_code,
            error_code=error_code,
            error_message=error_message,
            conversation_history=conversation_history,
        )

        try:
            completion = self.gateway.complete_json(
                provider=provider,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except LLMGatewayError as exc:
            return self._fallback_on_gateway_error(
                exc=exc,
                allow_need_human=allow_need_human,
                exit_code=exit_code,
                output_text=output_text,
                error_message=error_message,
            )

        decision = self._normalize_decision(
            raw=completion.parsed_json,
            allowed_actions=allowed_actions,
            available_routes=available_routes,
            allow_need_human=allow_need_human,
            can_reply_more=can_reply_more,
            require_local_file=require_local_file,
            local_files=local_files,
            exit_code=exit_code,
            error_message=error_message,
        )
        decision["prompt_tokens"] = completion.prompt_tokens
        decision["completion_tokens"] = completion.completion_tokens
        decision["total_tokens"] = completion.total_tokens
        return decision

    @staticmethod
    def _build_system_prompt(
        *,
        allowed_actions: list[str],
        available_routes: list[dict[str, str]],
        require_local_file: bool,
    ) -> str:
        route_note = (
            "Các nhánh đi tiếp hợp lệ ở bước này: "
            + ", ".join(f'"{r["route_key"]}" ({r.get("label") or r["route_key"]})' for r in available_routes)
            + ". Khi action=\"done\", bắt buộc điền \"route\" bằng một trong các route_key trên."
            if available_routes
            else "Bước này không chia nhánh điều kiện; khi action=\"done\" để \"route\": null."
        )
        file_note = (
            "LƯU Ý: Bước này dùng Skill thao tác file tại PC. Nếu chưa có file nào tạo/sửa mới trong local_files "
            "và công cụ chỉ mới hỏi xác nhận/option, KHÔNG được chọn \"done\"."
            if require_local_file
            else ""
        )
        return (
            "Bạn là Agent điều phối của hệ thống Agent CF. Nhiệm vụ của bạn là đọc kết quả text công cụ AI/Robot "
            "vừa chạy và quyết định hành động tiếp theo cho quy trình.\n"
            f"Chỉ được trả về DUY NHẤT 1 JSON object hợp lệ (không markdown, không giải thích ngoài JSON).\n"
            f"Trường \"action\" BẮT BUỘC là một trong các giá trị: {', '.join(allowed_actions)}.\n"
            f"{route_note}\n"
            f"{file_note}\n"
            "Schema JSON bắt buộc:\n"
            "{\n"
            f'  "action": "{" | ".join(allowed_actions)}",\n'
            '  "reply_message": "Chuỗi câu trả lời gửi tiếp vào phiên chat nếu action=reply, ngược lại null",\n'
            '  "route": "route_key nếu action=done và bước có chia nhánh, ngược lại null",\n'
            '  "summary_vi": "Tóm tắt ngắn gọn 1-2 câu bằng tiếng Việt về kết quả lượt này",\n'
            '  "question_for_user": "Câu hỏi/yêu cầu rõ ràng cho người dùng nếu action=need_human, ngược lại null",\n'
            '  "suggested_options": ["Tối đa 4 gợi ý trả lời ngắn nếu action=need_human, ngược lại []"],\n'
            '  "error_analysis": "Nếu action=fail hoặc retry: phân tích nguyên nhân gốc và gợi ý cách sửa dễ hiểu bằng tiếng Việt, ngược lại null"\n'
            "}"
        )

    @staticmethod
    def _build_user_prompt(
        *,
        agent_name: str,
        agent_rules: str,
        task_def: dict[str, Any],
        run_input: dict[str, Any],
        available_routes: list[dict[str, str]],
        turn_number: int,
        max_turns: int,
        output_text: str,
        local_files: list[dict[str, Any]],
        exit_code: int | None,
        error_code: str | None,
        error_message: str | None,
        conversation_history: list[dict[str, Any]],
    ) -> str:
        files_summary = [
            {"path": f.get("path"), "size_bytes": f.get("size_bytes", 0)}
            for f in local_files[:30]
        ]
        payload = {
            "agent_name": agent_name,
            "agent_rules": agent_rules,
            "step_name": task_def.get("name"),
            "step_instructions": task_def.get("instructions") or "",
            "run_topic": run_input.get("topic_directory") or run_input.get("topic") or run_input.get("prompt") or "",
            "user_request": run_input.get("request") or "",
            "turn": f"{turn_number}/{max_turns}",
            "available_routes": available_routes,
            "prior_turns": conversation_history[-6:],
            "execution_result": {
                "exit_code": exit_code,
                "error_code": error_code,
                "error_message": error_message,
                "changed_files_count": len(local_files),
                "changed_files": files_summary,
                "cli_output_text": _truncate_tail(output_text),
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize_decision(
        *,
        raw: dict[str, Any],
        allowed_actions: list[str],
        available_routes: list[dict[str, str]],
        allow_need_human: bool,
        can_reply_more: bool,
        require_local_file: bool,
        local_files: list[dict[str, Any]],
        exit_code: int | None,
        error_message: str | None,
    ) -> dict[str, Any]:
        action = str(raw.get("action") or "").strip().lower()
        if action not in allowed_actions:
            if action == "reply" and allow_need_human:
                action = "need_human"
            elif exit_code == 0 and allow_need_human:
                action = "need_human"
            else:
                action = "fail"

        reply_message = str(raw.get("reply_message") or "").strip() or None
        route = str(raw.get("route") or "").strip() or None
        summary_vi = str(raw.get("summary_vi") or "").strip()
        question = str(raw.get("question_for_user") or "").strip() or None
        raw_options = raw.get("suggested_options")
        suggested_options = (
            [str(opt).strip() for opt in raw_options if str(opt).strip()][:4]
            if isinstance(raw_options, list)
            else []
        )
        error_analysis = str(raw.get("error_analysis") or "").strip() or None

        # Prevent premature "done" when a file-producing local skill hasn't touched any file yet
        if action == "done" and require_local_file and not local_files:
            if can_reply_more:
                action = "reply"
                reply_message = reply_message or "Hãy hoàn tất và lưu kết quả ra file trong thư mục chủ đề."
                summary_vi = summary_vi or "Công cụ chưa tạo/sửa file kết quả; Agent yêu cầu hoàn tất ghi file."
            elif allow_need_human:
                action = "need_human"
                question = question or (
                    summary_vi
                    or "Công cụ đã chạy xong nhưng chưa thấy file nào được tạo/sửa. Bạn kiểm tra và nhập chỉ dẫn tiếp theo."
                )
            else:
                action = "fail"
                error_analysis = error_analysis or "Công cụ kết thúc nhưng chưa tạo hoặc cập nhật file nào trong thư mục chủ đề."

        if action == "reply" and not reply_message:
            reply_message = "Tiếp tục"

        if action == "done" and available_routes:
            valid_keys = {r["route_key"] for r in available_routes}
            if route not in valid_keys:
                route = available_routes[0]["route_key"]
        elif action != "done":
            route = None

        if action == "need_human" and not question:
            question = summary_vi or "Bước này cần bạn xác nhận hoặc trả lời để tiếp tục."

        if action == "fail" and not error_analysis:
            error_analysis = summary_vi or error_message or "Bước thực thi thất bại."

        if not summary_vi:
            summary_vi = question or error_analysis or (f"Gửi tiếp: {reply_message}" if reply_message else "Hoàn tất đánh giá lượt chạy.")

        return {
            "action": action,
            "reply_message": reply_message if action == "reply" else None,
            "route": route,
            "summary_vi": summary_vi,
            "question_for_user": question if action == "need_human" else None,
            "suggested_options": suggested_options if action == "need_human" else [],
            "error_analysis": error_analysis if action in ("fail", "retry") else None,
        }

    @staticmethod
    def _fallback_on_gateway_error(
        *,
        exc: LLMGatewayError,
        allow_need_human: bool,
        exit_code: int | None,
        output_text: str,
        error_message: str | None,
    ) -> dict[str, Any]:
        api_err = f"Không gọi được Agent API ({exc.message})."
        if exit_code not in (0, None) and error_message:
            detail = f"{api_err} Lỗi từ công cụ thực thi: {error_message}"
        elif output_text.strip():
            detail = f"{api_err} Công cụ đã trả phản hồi cuối: {output_text.strip()[:300]}"
        else:
            detail = api_err

        if allow_need_human and exit_code == 0:
            return {
                "action": "need_human",
                "reply_message": None,
                "route": None,
                "summary_vi": api_err,
                "question_for_user": f"{detail} Bạn kiểm tra kết quả/API key rồi bấm Tiếp tục hoặc Hủy.",
                "suggested_options": ["Tiếp tục", "Xác nhận đã xong"],
                "error_analysis": detail,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        return {
            "action": "fail",
            "reply_message": None,
            "route": None,
            "summary_vi": api_err,
            "question_for_user": None,
            "suggested_options": [],
            "error_analysis": detail,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
