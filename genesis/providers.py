"""Dependency-free real model providers; keys and response bodies are never logged."""
from __future__ import annotations
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from .models import DEFAULT_MODELS, model_catalog, validate_model_config


class ProviderError(RuntimeError):
    """Safe-to-display provider failure."""

    def __init__(self, message, billable_attempts=0):
        super().__init__(message)
        self.billable_attempts = billable_attempts


@dataclass
class ProviderResult:
    text: str
    tool_calls: list[dict]
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    provider_data: dict = field(default_factory=dict)


KEY_NAMES = {"openai": ("GENESIS_OPENAI_API_KEY", "OPENAI_API_KEY"),
             "anthropic": ("GENESIS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
             "gemini": ("GENESIS_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")}


def _key(provider, config):
    key = config.get("api_key") or next((os.environ[n] for n in KEY_NAMES[provider] if os.environ.get(n)), "")
    # Administrative credentials must never reach any model transport. Preserve
    # credential precedence: an invalid selected key does not select another key.
    return "" if isinstance(key, str) and key.startswith("sk-admin-") else key


def provider_status():
    """Configuration presence only, not a claim of network or account health."""
    return [{"provider": p, "configured": bool(_key(p, {})), "default_model": m,
             "models": [entry["id"] for entry in model_catalog(p)] or [m],
             "model_catalog": model_catalog(p), "capabilities": ["text", "function_calling"]} for p, m in DEFAULT_MODELS.items()]



def openai_model_availability(models):
    """Read account-visible exact model IDs; never generates or accepts credentials."""
    if (not isinstance(models, list) or len(models) > 50 or
            any(not isinstance(model, str) or len(model) > 200 or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", model) or
                model.startswith(("sk-", "Bearer")) for model in models)):
        raise ValueError("Expected at most 50 valid model IDs")
    models = list(dict.fromkeys(models))
    key = _key('openai', {})
    result = dict(provider='openai', credential_configured=bool(key), checked=False,
                  generation_tested=False, status='missing_credentials' if not key else 'not_checked',
                  models=[dict(id=model, available=None) for model in models])
    if not key:
        return result
    request = urllib.request.Request('https://api.openai.com/v1/models',
        headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}, method='GET')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        result['status'] = 'invalid_credentials' if code == 401 else ('redirect_refused' if 300 <= code < 400 else 'http_error')
        result['http_status'] = code
        return result
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, ValueError):
        result['status'] = 'connection_error'
        return result
    if len(raw) > 2 * 1024 * 1024:
        result['status'] = 'response_too_large'
        return result
    try:
        payload = json.loads(raw)
        entries = payload['data']
        if not isinstance(entries, list) or any(not isinstance(entry, dict) or not isinstance(entry.get('id'), str) for entry in entries):
            raise ValueError()
    except (UnicodeError, ValueError, KeyError, TypeError):
        result['status'] = 'invalid_response'
        return result
    visible = {entry['id'] for entry in entries}
    result.update(checked=True, status='checked', models=[dict(id=model, available=model in visible) for model in models])
    return result


def _post(url, headers, payload, timeout, max_bytes):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ProviderError(f"Provider HTTP {code}; check credentials, model access, quota, and request configuration") from None
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        raise ProviderError("Provider connection failed or timed out; no automatic retry was made") from None
    if len(raw) > max_bytes:
        raise ProviderError("Provider response exceeded size limit")
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise ProviderError("Provider returned invalid JSON") from None
    if not isinstance(value, dict):
        raise ProviderError("Provider returned an invalid response object")
    return value


def _arguments(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ProviderError("Provider returned malformed function arguments") from None
    if not isinstance(value, dict):
        raise ProviderError("Provider function arguments must be an object")
    return value


def _tokens(usage, name):
    """Provider usage is a JSON integer, never a coercible or signed value."""
    if not isinstance(usage, dict):
        raise ProviderError("Provider returned invalid token usage")
    value = usage.get(name, 0)
    if type(value) is not int or value < 0:
        raise ProviderError("Provider token usage must contain nonnegative integers")
    return value


def _content(message):
    value = message.get("content", "")
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class OpenAIAdapter:
    endpoint = "https://api.openai.com/v1/responses"

    def request(self, messages, tools, config):
        config = validate_model_config(config)
        items = []
        for m in messages:
            if m["role"] == "tool":
                items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": _content(m)})
                continue
            if m["role"] == "assistant" and m.get("provider_data", {}).get("openai_output"):
                items.extend(m["provider_data"]["openai_output"])
                continue
            if _content(m):
                items.append({"role": m["role"], "content": _content(m)})
            for c in m.get("tool_calls", []):
                items.append({"type": "function_call", "call_id": c["id"], "name": c["name"], "arguments": json.dumps(c["arguments"])})
        payload = {"model": config["model"], "input": items, "max_output_tokens": config.get("max_output_tokens", 2048), "store": False,
                   "include": ["reasoning.encrypted_content"]}
        if tools:
            payload["tools"] = [{"type": "function", "name": t["name"], "description": t.get("description", ""), "parameters": t["parameters"], "strict": False} for t in tools]
        if "temperature" in config:
            payload["temperature"] = config["temperature"]
        if "reasoning_effort" in config:
            payload["reasoning"] = {"effort": config["reasoning_effort"]}
        return self.endpoint, {"Authorization": "Bearer " + config["api_key"]}, payload

    def parse(self, data):
        if data.get("status") not in (None, "completed") or data.get("error"):
            raise ProviderError("OpenAI did not complete the response; check output limits or provider status")
        if not isinstance(data.get("output"), list):
            raise ProviderError("OpenAI response is missing output")
        text, calls = [], []
        for item in data["output"]:
            if item.get("type") == "message":
                text.extend(c["text"] for c in item.get("content", []) if c.get("type") == "output_text")
            elif item.get("type") == "function_call":
                calls.append({"id": item["call_id"], "name": item["name"], "arguments": _arguments(item["arguments"])})
        usage = data.get("usage", {})
        inp, out = _tokens(usage, "input_tokens"), _tokens(usage, "output_tokens")
        def detail(container, field):
            if container not in usage:
                return None
            details = usage[container]
            if not isinstance(details, dict):
                raise ProviderError("Provider returned invalid token usage")
            return _tokens(details, field) if field in details else None
        cached = detail("input_tokens_details", "cached_tokens")
        reasoning = detail("output_tokens_details", "reasoning_tokens")
        if (cached is not None and cached > inp) or (reasoning is not None and reasoning > out):
            raise ProviderError("Provider token usage details exceed reported totals")
        return "\n".join(text), calls, inp, out, {"openai_output": data["output"],
            "usage_complete": "input_tokens" in usage and "output_tokens" in usage,
            "cached_input_tokens": cached, "reasoning_output_tokens": reasoning,
            "raw_usage": deepcopy(usage)}


class AnthropicAdapter:
    endpoint = "https://api.anthropic.com/v1/messages"

    def request(self, messages, tools, config):
        history, system = [], []
        for m in messages:
            role = m["role"]
            if role == "system":
                system.append(_content(m))
                continue
            if role == "tool":
                role, content = "user", [{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": _content(m)}]
            else:
                content = [{"type": "text", "text": _content(m)}] if _content(m) else []
                content.extend({"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["arguments"]} for c in m.get("tool_calls", []))
            if history and history[-1]["role"] == role:
                history[-1]["content"].extend(content)
            else:
                history.append({"role": role, "content": content})
        payload = {"model": config["model"], "messages": history, "max_tokens": config.get("max_output_tokens", 2048)}
        if system:
            payload["system"] = "\n\n".join(system)
        if tools:
            payload["tools"] = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t["parameters"]} for t in tools]
        if "temperature" in config:
            payload["temperature"] = config["temperature"]
        return self.endpoint, {"x-api-key": config["api_key"], "anthropic-version": "2023-06-01"}, payload

    def parse(self, data):
        if data.get("stop_reason") in ("max_tokens", "refusal", "pause_turn"):
            raise ProviderError("Anthropic did not complete the response; check output limits or provider status")
        if not isinstance(data.get("content"), list):
            raise ProviderError("Anthropic response is missing content")
        text, calls = [], []
        for c in data["content"]:
            if c.get("type") == "text":
                text.append(c["text"])
            elif c.get("type") == "tool_use":
                calls.append({"id": c["id"], "name": c["name"], "arguments": _arguments(c["input"])})
        usage = data.get("usage", {})
        return "\n".join(text), calls, _tokens(usage, "input_tokens"), _tokens(usage, "output_tokens"), {"usage_complete": "input_tokens" in usage and "output_tokens" in usage}


class GeminiAdapter:
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def request(self, messages, tools, config):
        history, system, call_names = [], [], {}
        for m in messages:
            if m["role"] == "system":
                system.append(_content(m))
                continue
            role = "model" if m["role"] == "assistant" else "user"
            if m["role"] == "tool":
                name = m.get("name") or call_names.get(m["tool_call_id"])
                if not name:
                    raise ProviderError("Gemini tool result is missing its function name")
                parts = [{"functionResponse": {"id": m["tool_call_id"], "name": name, "response": {"result": _content(m)}}}]
            else:
                parts = [{"text": _content(m)}] if _content(m) else []
                for c in m.get("tool_calls", []):
                    call_names[c["id"]] = c["name"]
                    part = {"functionCall": {"id": c["id"], "name": c["name"], "args": c["arguments"]}}
                    if c.get("_provider_data", {}).get("thoughtSignature"):
                        part["thoughtSignature"] = c["_provider_data"]["thoughtSignature"]
                    parts.append(part)
                if m.get("provider_data", {}).get("gemini_parts"):
                    parts = m["provider_data"]["gemini_parts"]
            if history and history[-1]["role"] == role:
                history[-1]["parts"].extend(parts)
            else:
                history.append({"role": role, "parts": parts})
        payload = {"contents": history, "generationConfig": {"maxOutputTokens": config.get("max_output_tokens", 2048)}}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system)}]}
        if tools:
            payload["tools"] = [{"functionDeclarations": [{"name": t["name"], "description": t.get("description", ""), "parametersJsonSchema": t["parameters"]} for t in tools]}]
        if "temperature" in config:
            payload["generationConfig"]["temperature"] = config["temperature"]
        return self.endpoint.format(model=urllib.parse.quote(config["model"], safe="")), {"x-goog-api-key": config["api_key"]}, payload

    def parse(self, data):
        candidates = data.get("candidates", [])
        if not candidates or candidates[0].get("finishReason") not in (None, "STOP"):
            raise ProviderError("Gemini returned no complete candidate; check safety settings or output limits")
        parts = candidates[0].get("content", {}).get("parts", [])
        text, calls = [], []
        for p in parts:
            if "text" in p and not p.get("thought"):
                text.append(p["text"])
            if "functionCall" in p:
                c = p["functionCall"]
                call = {"id": c.get("id") or "gemini_" + uuid.uuid4().hex, "name": c["name"], "arguments": _arguments(c.get("args", {}))}
                if "thoughtSignature" in p:
                    call["_provider_data"] = {"thoughtSignature": p["thoughtSignature"]}
                c["id"] = call["id"]
                calls.append(call)
        usage = data.get("usageMetadata", {})
        return "\n".join(text), calls, _tokens(usage, "promptTokenCount"), _tokens(usage, "candidatesTokenCount") + _tokens(usage, "thoughtsTokenCount"), {"gemini_parts": parts, "usage_complete": "promptTokenCount" in usage and "candidatesTokenCount" in usage}


class ProviderRouter:
    def __init__(self, transport=None, timeout=60, max_response_bytes=4 * 1024 * 1024):
        self.transport = transport or _post
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.adapters = {"openai": OpenAIAdapter(), "anthropic": AnthropicAdapter(), "gemini": GeminiAdapter()}

    def generate(self, messages, tools, config):
        """One request per explicit candidate. Tool execution belongs to the runtime."""
        try:
            config = validate_model_config(config)
        except ValueError as exc:
            raise ProviderError(str(exc), billable_attempts=0) from None
        base = {k: v for k, v in config.items() if k not in ("api_key", "provider", "model", "fallbacks", "reasoning_effort")}
        try:
            candidates = [config] + [validate_model_config({**base, **f}) for f in config.get("fallbacks", [])]
        except ValueError as exc:
            raise ProviderError(str(exc), billable_attempts=0) from None
        errors = []
        billable_attempts = 0
        for candidate in candidates:
            provider = candidate.get("provider", "openai")
            if provider not in self.adapters:
                errors.append("Unsupported provider")
                continue
            model = candidate.get("model") or DEFAULT_MODELS[provider]
            key = _key(provider, candidate)
            if not key:
                errors.append(f"{provider}: missing API key; set {KEY_NAMES[provider][0]}")
                continue
            try:
                adapter = self.adapters[provider]
                url, headers, payload = adapter.request(messages, tools, {**candidate, "model": model, "api_key": key})
                billable_attempts += 1
                data = self.transport(url, headers, payload, self.timeout, self.max_response_bytes)
                text, calls, inp, out, metadata = adapter.parse(data)
                if not text and not calls:
                    raise ProviderError("Provider returned neither text nor function calls")
                metadata["_prior_billable_attempts"] = billable_attempts - 1
                return ProviderResult(text, calls, int(inp), int(out), provider, model, metadata)
            except ProviderError as exc:
                errors.append(f"{provider}: {exc}")
            except (KeyError, TypeError, ValueError, AttributeError):
                errors.append(f"{provider}: invalid request configuration or malformed provider response")
        raise ProviderError("; ".join(errors), billable_attempts=billable_attempts)
