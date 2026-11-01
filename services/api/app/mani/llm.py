"""The model adapter: chat and embeddings over an OpenAI-compatible endpoint (architecture 8.1).

One class pair serves both approved backends. `local` is Ollama, `openrouter` is the hosted
route. A failure is raised as ModelError. There is no retry and no switch to another backend
or model. Prompts and answers are never logged, and the API key never appears in an error."""
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from app.mani.config import BACKENDS, EMBEDDING_DIMENSIONS, ManiSettings
from app.mani.contracts import (
    ChatMessage,
    ChatResult,
    Embedder,
    EmbedResult,
    LLMClient,
    ModelError,
    ToolCall,
    ToolSpec,
    Usage,
)

# Sent on every OpenRouter request, chat and embeddings: no data kept or trained on, only
# zero-data-retention providers, no other provider tried (D8).
_PRIVACY = {"data_collection": "deny", "zdr": True, "allow_fallbacks": False, "require_parameters": True}
_RELAXED = {"allow_fallbacks": False, "require_parameters": True}  # evaluation only: no retention rule
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_BODY_LIMIT = 300  # characters of an error body kept in a message


HOSTED = ("openrouter", "google")  # the routes that need a key


def _check_backend(backend: str, api_key: str) -> None:
    if backend == "awsbedrock":
        raise ModelError("The awsbedrock provider is not built yet. Use localllm, openrouter or google.")
    if backend not in BACKENDS:
        raise ModelError(f"The model backend '{backend}' is not approved. Use one of: {', '.join(BACKENDS)}.")
    if backend in HOSTED and not api_key:
        raise ModelError(f"The {backend} backend needs an API key, and none is set.")


class _Endpoint:
    """The shared HTTP part: headers, the privacy block and error mapping."""

    def __init__(self, settings: ManiSettings, model: str, *, backend: str | None = None,
                 base_url: str | None = None) -> None:
        backend = backend or settings.backend
        _check_backend(backend, settings.api_key)
        self.backend = backend
        self.model = model
        self._base = (base_url or settings.base_url).rstrip("/")
        self._key = settings.api_key if backend in HOSTED else ""
        self._timeout = settings.request_timeout_seconds
        self._provider = _RELAXED if settings.eval_allow_data_retention else _PRIVACY

    def _clean(self, text: str) -> str:
        """Truncate and make sure the key cannot leak through an echoed body."""
        if self._key:
            text = text.replace(self._key, "[key]")
        return text[:_BODY_LIMIT]

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = {**body, "model": self.model}
        headers = {"Content-Type": "application/json"}
        if self.backend == "openrouter":
            payload["provider"] = dict(self._provider)
        if self.backend in HOSTED:
            headers["Authorization"] = f"Bearer {self._key}"
        request = urllib.request.Request(
            self._base + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
        where = f"{self.backend} model backend ({path})"
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            try:
                detail = error.read().decode("utf-8", "replace")
            except Exception:
                detail = ""
            raise ModelError(f"The {where} answered HTTP {error.code}: {self._clean(detail)}") from None
        except TimeoutError:
            raise ModelError(f"The {where} timed out after {self._timeout:g} seconds.") from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ModelError(f"The {where} timed out after {self._timeout:g} seconds.") from None
            raise ModelError(f"Cannot reach the {where}: {self._clean(str(error.reason))}") from None
        except OSError as error:
            raise ModelError(f"Cannot reach the {where}: {self._clean(str(error))}") from None
        try:
            data = json.loads(raw)
        except ValueError:
            raise ModelError(f"The {where} sent a reply that is not valid JSON: "
                             f"{self._clean(raw.decode('utf-8', 'replace'))}") from None
        if not isinstance(data, dict):
            raise ModelError(f"The {where} sent an unexpected reply.")
        return data


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _cost(backend: str, usage: dict[str, Any]) -> Decimal:
    if backend != "openrouter" or usage.get("cost") is None:
        return Decimal(0)
    try:
        return Decimal(str(usage["cost"]))
    except InvalidOperation:
        return Decimal(0)


def _wire_message(message: ChatMessage) -> dict[str, Any]:
    wire: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.role == "assistant" and message.tool_calls:
        wire["tool_calls"] = [
            {"id": call.id, "type": "function",
             "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
             **({"extra_content": call.extra} if call.extra else {})}
            for call in message.tool_calls
        ]
    if message.role == "tool":
        wire["tool_call_id"] = message.tool_call_id
        if message.name:
            wire["name"] = message.name
    return wire


def _wire_tool(spec: ToolSpec) -> dict[str, Any]:
    return {"type": "function",
            "function": {"name": spec.name, "description": spec.description, "parameters": spec.parameters}}


def _parse_tool_calls(raw_calls: Any) -> tuple[ToolCall, ...]:
    calls = []
    for index, raw in enumerate(raw_calls or []):
        try:
            function = raw["function"]
            name = function["name"]
            arguments = function.get("arguments", {})
        except (KeyError, TypeError, AttributeError):
            raise ModelError("The model sent a tool call in a shape that cannot be read.") from None
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except ValueError:
                raise ModelError(f"The model sent invalid JSON arguments for the tool '{name}'.") from None
        if not isinstance(arguments, dict):
            raise ModelError(f"The model sent arguments for the tool '{name}' that are not an object.")
        extra = raw.get("extra_content")
        calls.append(ToolCall(id=str(raw.get("id") or f"call_{index}"), name=str(name), arguments=arguments,
                              extra=extra if isinstance(extra, dict) else None))
    return tuple(calls)


class OpenAICompatibleClient(_Endpoint):
    """LLMClient over POST {base_url}/chat/completions."""

    def __init__(self, settings: ManiSettings) -> None:
        super().__init__(settings, settings.chat_model)

    def chat(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec] = (), *,
             temperature: float = 0.0) -> ChatResult:
        body: dict[str, Any] = {"messages": [_wire_message(m) for m in messages], "temperature": temperature}
        if tools:
            body["tools"] = [_wire_tool(t) for t in tools]
        started = time.monotonic()
        data = self._post("/chat/completions", body)
        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            choice = data["choices"][0]
            wire = choice["message"]
        except (KeyError, IndexError, TypeError):
            raise ModelError(f"The {self.backend} model backend sent a chat reply with no message.") from None
        content = _THINK.sub("", wire.get("content") or "").strip()
        message = ChatMessage(role="assistant", content=content, tool_calls=_parse_tool_calls(wire.get("tool_calls")))
        raw_usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        usage = Usage(prompt_tokens=_int(raw_usage.get("prompt_tokens")),
                      completion_tokens=_int(raw_usage.get("completion_tokens")),
                      latency_ms=latency_ms, cost_usd=_cost(self.backend, raw_usage))
        return ChatResult(message=message, usage=usage, model=str(data.get("model") or self.model),
                          finish_reason=str(choice.get("finish_reason") or "stop"))


class OpenAICompatibleEmbedder(_Endpoint):
    """Embedder over POST {base_url}/embeddings. Always asks for 1024 values."""

    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, settings: ManiSettings) -> None:
        super().__init__(settings, settings.embedding_model, backend=settings.embeddings_backend,
                         base_url=settings.embeddings_base_url)

    def embed(self, texts: Sequence[str]) -> EmbedResult:
        if not texts:
            return EmbedResult(vectors=[], usage=Usage())
        started = time.monotonic()
        data = self._post("/embeddings", {"input": list(texts), "dimensions": self.dimensions})
        latency_ms = int((time.monotonic() - started) * 1000)
        items = data.get("data")
        if not isinstance(items, list) or len(items) != len(texts):
            raise ModelError(f"The {self.backend} model backend returned the wrong number of embeddings.")
        # Keep the input order even if the server sends the items in another order.
        if all(isinstance(i, dict) and isinstance(i.get("index"), int) for i in items):
            items = sorted(items, key=lambda i: i["index"])
        vectors: list[list[float]] = []
        for item in items:
            try:
                vector = [float(x) for x in item["embedding"]]
            except (KeyError, TypeError, ValueError):
                raise ModelError(f"The {self.backend} model backend sent an embedding that cannot be read.") from None
            if len(vector) != self.dimensions:
                raise ModelError(f"The {self.backend} model backend returned an embedding of {len(vector)} "
                                 f"values, not {self.dimensions}.")
            vectors.append(vector)
        raw_usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        usage = Usage(prompt_tokens=_int(raw_usage.get("prompt_tokens")), latency_ms=latency_ms,
                      cost_usd=_cost(self.backend, raw_usage))
        return EmbedResult(vectors=vectors, usage=usage)


def build_llm(settings: ManiSettings) -> LLMClient:
    return OpenAICompatibleClient(settings)


def build_embedder(settings: ManiSettings) -> Embedder:
    return OpenAICompatibleEmbedder(settings)
