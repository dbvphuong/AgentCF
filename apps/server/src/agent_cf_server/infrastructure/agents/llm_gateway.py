"""LLM Gateway calling configured API Providers (OpenAI, Anthropic, Google, Custom)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx


class LLMGatewayError(RuntimeError):
    """Raised when an Agent API provider call fails or returns unusable output."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class LLMCompletionResult:
    parsed_json: dict[str, Any]
    raw_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise LLMGatewayError("empty_llm_response", "Model API trả về nội dung rỗng.")

    # Strip ```json ... ``` markdown fences if present
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
    except ValueError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            loaded = json.loads(text[start : end + 1])
            if isinstance(loaded, dict):
                return loaded
        except ValueError:
            pass
    raise LLMGatewayError("invalid_llm_json", "Model API không trả về đúng định dạng JSON hợp lệ.")


def _validate_base_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise LLMGatewayError("invalid_provider_url", f"Base URL của Provider không hợp lệ: {base_url}")
    return url


def _join_versioned_endpoint(base_url: str, version_prefix: str, suffix: str) -> str:
    if base_url.endswith(version_prefix):
        return f"{base_url}{suffix}"
    return f"{base_url}{version_prefix}{suffix}"


class LLMGateway:
    """HTTP client calling OpenAI, Anthropic, Google Gemini, or custom OpenAI-compatible APIs."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def complete_json(
        self,
        *,
        provider: dict[str, Any],
        model: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
    ) -> LLMCompletionResult:
        api_format = (provider.get("api_format") or "openai").lower()
        base_url = _validate_base_url(str(provider.get("base_url") or ""))
        api_key = provider.get("api_key") or provider.get("api_key_ciphertext")
        timeout = float(provider.get("request_timeout_seconds") or 60)
        model_id = str(model.get("model_identifier") or "").strip()
        if not model_id:
            raise LLMGatewayError("missing_model_identifier", "Model API của Agent thiếu model_identifier.")
        temperature = model.get("temperature")
        max_tokens = model.get("max_output_tokens") or 1024

        headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
        if api_format == "anthropic":
            if api_key:
                headers["x-api-key"] = str(api_key)
            headers["anthropic-version"] = "2023-06-01"
            endpoint = _join_versioned_endpoint(base_url, "/v1", "/messages")
            body: dict[str, Any] = {
                "model": model_id,
                "max_tokens": int(max_tokens),
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            if temperature is not None:
                body["temperature"] = float(temperature)
        elif api_format == "google":
            if api_key:
                headers["x-goog-api-key"] = str(api_key)
            endpoint = _join_versioned_endpoint(
                base_url, "/v1beta", f"/models/{model_id}:generateContent"
            )
            gen_config: dict[str, Any] = {
                "responseMimeType": "application/json",
                "maxOutputTokens": int(max_tokens),
            }
            if temperature is not None:
                gen_config["temperature"] = float(temperature)
            body = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": gen_config,
            }
        else:
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            endpoint = f"{base_url}/chat/completions"
            body = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": int(max_tokens),
                "response_format": {"type": "json_object"},
            }
            if temperature is not None:
                body["temperature"] = float(temperature)

        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                resp = client.post(endpoint, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise LLMGatewayError("provider_timeout", f"Hết thời gian chờ Provider ({timeout:.0f}s).") from exc
        except httpx.HTTPError as exc:
            raise LLMGatewayError("provider_connection_failed", f"Không kết nối được tới Provider: {exc}") from exc

        if resp.status_code < 200 or resp.status_code >= 300:
            snippet = resp.text.strip()[:300]
            raise LLMGatewayError(
                "provider_http_error",
                f"Provider trả về lỗi HTTP {resp.status_code}: {snippet or 'Không có chi tiết'}",
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMGatewayError("invalid_provider_response", "Provider trả về phản hồi không phải JSON.") from exc

        raw_text, prompt_tokens, completion_tokens, total_tokens = self._parse_provider_payload(api_format, data)
        parsed = _extract_json_object(raw_text)
        return LLMCompletionResult(
            parsed_json=parsed,
            raw_text=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens or (prompt_tokens + completion_tokens),
        )

    @staticmethod
    def _parse_provider_payload(api_format: str, data: dict[str, Any]) -> tuple[str, int, int, int]:
        if api_format == "anthropic":
            blocks = data.get("content") or []
            texts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
            usage = data.get("usage") or {}
            pt = int(usage.get("input_tokens") or 0)
            ct = int(usage.get("output_tokens") or 0)
            return "\n".join(texts).strip(), pt, ct, pt + ct

        if api_format == "google":
            candidates = data.get("candidates") or []
            parts: list[str] = []
            if candidates and isinstance(candidates[0], dict):
                content = candidates[0].get("content") or {}
                for part in content.get("parts") or []:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
            usage = data.get("usageMetadata") or {}
            pt = int(usage.get("promptTokenCount") or 0)
            ct = int(usage.get("candidatesTokenCount") or 0)
            tt = int(usage.get("totalTokenCount") or (pt + ct))
            return "\n".join(parts).strip(), pt, ct, tt

        choices = data.get("choices") or []
        raw_text = ""
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            raw_text = str(message.get("content") or "")
        usage = data.get("usage") or {}
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
        tt = int(usage.get("total_tokens") or (pt + ct))
        return raw_text.strip(), pt, ct, tt
