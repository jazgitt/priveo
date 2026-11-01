"""The model adapter, tested against a tiny fake HTTP endpoint. No real model is called.
The live class at the bottom runs only with MANI_LIVE_OLLAMA=1 and talks to local Ollama."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.mani.config import EMBEDDING_DIMENSIONS, ManiSettings
from app.mani.contracts import ChatMessage, ModelError, ToolCall, ToolSpec
from app.mani.llm import build_embedder, build_llm

KEY = "sk-secret-test-key-123"
PRIVACY = {"data_collection": "deny", "zdr": True, "allow_fallbacks": False, "require_parameters": True}


class FakeServer:
    """Records every request and answers with whatever `reply` holds."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.status = 200
        self.body: bytes | str | dict = {}
        self.delay = 0.0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                outer.requests.append({"path": self.path, "headers": dict(self.headers.items()),
                                       "body": json.loads(self.rfile.read(length))})
                if outer.delay:
                    threading.Event().wait(outer.delay)
                body = outer.body
                raw = body if isinstance(body, bytes) else (body.encode() if isinstance(body, str)
                                                            else json.dumps(body).encode())
                try:
                    self.send_response(outer.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except OSError:
                    pass  # the client gave up (timeout test)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    fake = FakeServer()
    yield fake
    fake.close()


def settings(server: FakeServer, backend: str = "local", key: str = "", timeout: float = 5.0) -> ManiSettings:
    return ManiSettings(_env_file=None, backend=backend, base_url=server.url, MANI_API_KEY=key,
                        request_timeout_seconds=timeout, chat_model="chat-x", embedding_model="embed-x")


def chat_reply(message: dict, usage: dict | None = None, finish: str = "stop") -> dict:
    return {"model": "chat-x", "choices": [{"message": {"role": "assistant", **message}, "finish_reason": finish}],
            "usage": usage or {"prompt_tokens": 11, "completion_tokens": 7}}


def vectors_reply(count: int, size: int = EMBEDDING_DIMENSIONS) -> dict:
    return {"data": [{"index": i, "embedding": [float(i)] * size} for i in range(count)],
            "usage": {"prompt_tokens": 5}}


TOOL = ToolSpec(name="jobs_summary", description="Counts jobs.",
                parameters={"type": "object", "properties": {"society": {"type": "string"}}})


class TestChat:
    def test_request_body_and_local_has_no_auth_or_provider(self, server):
        server.body = chat_reply({"content": "hello"})
        result = build_llm(settings(server)).chat([ChatMessage("system", "be brief"), ChatMessage("user", "hi")],
                                                   [TOOL], temperature=0.2)
        request = server.requests[0]
        assert request["path"] == "/v1/chat/completions"
        assert "Authorization" not in request["headers"]
        body = request["body"]
        assert "provider" not in body
        assert body["model"] == "chat-x"
        assert body["temperature"] == 0.2
        assert body["messages"] == [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
        assert body["tools"] == [{"type": "function", "function": {
            "name": "jobs_summary", "description": "Counts jobs.", "parameters": TOOL.parameters}}]
        assert result.message.content == "hello"
        assert result.message.role == "assistant"
        assert result.usage.prompt_tokens == 11
        assert result.usage.completion_tokens == 7
        assert result.usage.latency_ms >= 0
        assert result.usage.cost_usd == 0
        assert result.finish_reason == "stop"
        assert result.model == "chat-x"

    def test_no_tools_key_when_none_given(self, server):
        server.body = chat_reply({"content": "ok"})
        build_llm(settings(server)).chat([ChatMessage("user", "hi")])
        assert "tools" not in server.requests[0]["body"]

    def test_openrouter_sends_key_privacy_block_and_cost(self, server):
        server.body = chat_reply({"content": "ok"}, {"prompt_tokens": 3, "completion_tokens": 2, "cost": 0.0042})
        result = build_llm(settings(server, "openrouter", KEY)).chat([ChatMessage("user", "hi")])
        request = server.requests[0]
        assert request["headers"]["Authorization"] == f"Bearer {KEY}"
        assert request["body"]["provider"] == PRIVACY
        assert str(result.usage.cost_usd) == "0.0042"

    def test_openrouter_without_cost_is_zero_and_local_ignores_cost(self, server):
        server.body = chat_reply({"content": "ok"}, {"prompt_tokens": 3, "completion_tokens": 2})
        assert build_llm(settings(server, "openrouter", KEY)).chat([ChatMessage("user", "x")]).usage.cost_usd == 0
        server.body = chat_reply({"content": "ok"}, {"cost": 9})
        assert build_llm(settings(server)).chat([ChatMessage("user", "x")]).usage.cost_usd == 0

    def test_tool_call_arguments_as_json_string(self, server):
        server.body = chat_reply({"content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "jobs_summary", "arguments": '{"society": "GM"}'}}]},
            finish="tool_calls")
        result = build_llm(settings(server)).chat([ChatMessage("user", "x")], [TOOL])
        assert result.message.tool_calls == (ToolCall(id="c1", name="jobs_summary", arguments={"society": "GM"}),)
        assert result.finish_reason == "tool_calls"

    def test_tool_call_arguments_as_dict(self, server):
        server.body = chat_reply({"content": None, "tool_calls": [
            {"id": "c2", "function": {"name": "jobs_summary", "arguments": {"society": "GM"}}}]})
        result = build_llm(settings(server)).chat([ChatMessage("user", "x")], [TOOL])
        assert result.message.tool_calls[0].arguments == {"society": "GM"}
        assert result.message.content == ""

    def test_tool_call_without_id_gets_one(self, server):
        server.body = chat_reply({"tool_calls": [{"function": {"name": "jobs_summary", "arguments": "{}"}}]})
        result = build_llm(settings(server)).chat([ChatMessage("user", "x")], [TOOL])
        assert result.message.tool_calls[0].id == "call_0"

    def test_invalid_json_arguments_raise(self, server):
        server.body = chat_reply({"tool_calls": [
            {"id": "c", "function": {"name": "jobs_summary", "arguments": "{not json"}}]})
        with pytest.raises(ModelError, match="invalid JSON arguments"):
            build_llm(settings(server)).chat([ChatMessage("user", "x")], [TOOL])

    def test_think_blocks_are_stripped(self, server):
        server.body = chat_reply({"content": "<think>\nplan\nmore plan\n</think>\n\nThe answer is 7."})
        result = build_llm(settings(server)).chat([ChatMessage("user", "x")])
        assert result.message.content == "The answer is 7."

    def test_message_round_trip_with_tool_results(self, server):
        server.body = chat_reply({"content": "7 missed"})
        history = [
            ChatMessage("user", "how many missed?"),
            ChatMessage("assistant", "", tool_calls=(ToolCall("c1", "jobs_summary", {"society": "GM"}),)),
            ChatMessage("tool", '{"missed": 7}', tool_call_id="c1", name="jobs_summary"),
        ]
        build_llm(settings(server)).chat(history, [TOOL])
        sent = server.requests[0]["body"]["messages"]
        assert sent[1]["role"] == "assistant"
        assert sent[1]["tool_calls"] == [{"id": "c1", "type": "function", "function": {
            "name": "jobs_summary", "arguments": '{"society": "GM"}'}}]
        assert sent[2] == {"role": "tool", "content": '{"missed": 7}', "tool_call_id": "c1", "name": "jobs_summary"}
        assert "tool_calls" not in sent[0]

    def test_missing_choices_raise(self, server):
        server.body = {"oops": True}
        with pytest.raises(ModelError):
            build_llm(settings(server)).chat([ChatMessage("user", "x")])


class TestProvider:
    def test_each_provider_picks_its_route_address_and_key(self):
        local = ManiSettings(_env_file=None, provider="localllm")
        assert (local.backend, local.base_url) == ("local", "http://localhost:11434/v1")
        router = ManiSettings(_env_file=None, provider="openrouter", MANI_API_KEY="or-key")
        assert (router.backend, router.base_url) == ("openrouter", "https://openrouter.ai/api/v1")
        google = ManiSettings(_env_file=None, provider="google", GEMINI_API_KEY="g-key", MANI_API_KEY="other")
        assert google.backend == "google" and google.api_key == "g-key"
        assert google.base_url.startswith("https://generativelanguage.googleapis.com/")
        assert google.embeddings_backend == "local"  # the stored vectors come from the local model

    def test_an_unknown_provider_is_refused_and_awsbedrock_is_not_built(self):
        import pytest
        with pytest.raises(ValueError, match="MANI_PROVIDER"):
            ManiSettings(_env_file=None, provider="azure")
        with pytest.raises(ModelError, match="not built yet"):
            build_llm(ManiSettings(_env_file=None, provider="awsbedrock"))

    def test_google_sends_a_bearer_key_and_no_openrouter_privacy_block(self, server):
        server.body = chat_reply({"content": "hi"})
        google = ManiSettings(_env_file=None, provider="google", base_url=server.url, GEMINI_API_KEY="g-key",
                              chat_model="gemini-x")
        build_llm(google).chat([ChatMessage("user", "x")])
        request = server.requests[-1]
        assert request["headers"]["Authorization"] == "Bearer g-key" and "provider" not in request["body"]

    def test_a_tool_calls_provider_data_goes_back_with_it(self, server):
        signed = {"google": {"thought_signature": "sig-1"}}
        server.body = chat_reply({"content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}, "extra_content": signed}]})
        google = ManiSettings(_env_file=None, provider="google", base_url=server.url, GEMINI_API_KEY="g-key",
                              chat_model="gemini-x")
        client = build_llm(google)
        call = client.chat([ChatMessage("user", "x")]).message.tool_calls[0]
        assert call.extra == signed
        server.body = chat_reply({"content": "done"})
        client.chat([ChatMessage("user", "x"), ChatMessage("assistant", "", tool_calls=(call,))])
        assert server.requests[-1]["body"]["messages"][1]["tool_calls"][0]["extra_content"] == signed

    def test_a_hosted_provider_without_its_key_is_refused(self):
        import pytest
        with pytest.raises(ModelError, match="needs an API key"):
            build_llm(ManiSettings(_env_file=None, provider="google", GEMINI_API_KEY="", MANI_API_KEY=""))


class TestEmbeddings:
    def test_the_no_retention_rule_is_on_unless_the_evaluation_switches_it_off(self, server):
        server.body = chat_reply({"content": "hi"})
        build_llm(settings(server, backend="openrouter", key="k")).chat([ChatMessage("user", "x")])
        assert server.requests[-1]["body"]["provider"]["zdr"] is True
        relaxed = settings(server, backend="openrouter", key="k")
        relaxed.eval_allow_data_retention = True
        build_llm(relaxed).chat([ChatMessage("user", "x")])
        provider = server.requests[-1]["body"]["provider"]
        assert "zdr" not in provider and "data_collection" not in provider

    def test_embeddings_can_stay_local_while_the_chat_is_hosted(self, server):
        server.body = vectors_reply(1)
        own = ManiSettings(_env_file=None, backend="openrouter", base_url="https://openrouter.invalid/api/v1",
                           embedding_backend="local", embedding_base_url=server.url, MANI_API_KEY="sk-secret",
                           embedding_model="embed-x")
        assert own.embeddings_backend == "local" and own.backend == "openrouter"
        build_embedder(own).embed(["a"])
        request = server.requests[0]
        assert "provider" not in request["body"] and "Authorization" not in request["headers"]

    def test_embeddings_follow_the_chat_backend_unless_told_otherwise(self):
        both = ManiSettings(_env_file=None, backend="openrouter", base_url="https://x.invalid/v1", MANI_API_KEY="k")
        assert both.embeddings_backend == "openrouter" and both.embeddings_base_url == "https://x.invalid/v1"
        split = ManiSettings(_env_file=None, backend="openrouter", embedding_backend="local", MANI_API_KEY="k")
        assert split.embeddings_base_url == "http://localhost:11434/v1"

    def test_local_asks_for_1024_and_keeps_order(self, server):
        # The server answers out of order; the adapter must restore input order.
        reply = vectors_reply(3)
        reply["data"].reverse()
        server.body = reply
        result = build_embedder(settings(server)).embed(["a", "b", "c"])
        request = server.requests[0]
        assert request["path"] == "/v1/embeddings"
        assert request["body"]["dimensions"] == 1024
        assert request["body"]["input"] == ["a", "b", "c"]
        assert request["body"]["model"] == "embed-x"
        assert "provider" not in request["body"]
        assert "Authorization" not in request["headers"]
        assert [v[0] for v in result.vectors] == [0.0, 1.0, 2.0]
        assert result.usage.prompt_tokens == 5

    def test_openrouter_asks_for_1024_with_privacy_block(self, server):
        server.body = vectors_reply(1)
        build_embedder(settings(server, "openrouter", KEY)).embed(["a"])
        request = server.requests[0]
        assert request["body"]["dimensions"] == 1024
        assert request["body"]["provider"] == PRIVACY
        assert request["headers"]["Authorization"] == f"Bearer {KEY}"

    def test_dimensions_property(self, server):
        assert build_embedder(settings(server)).dimensions == 1024

    def test_wrong_length_vector_raises(self, server):
        server.body = vectors_reply(1, size=4096)
        with pytest.raises(ModelError, match="4096"):
            build_embedder(settings(server)).embed(["a"])

    def test_wrong_count_raises(self, server):
        server.body = vectors_reply(1)
        with pytest.raises(ModelError):
            build_embedder(settings(server)).embed(["a", "b"])

    def test_empty_input_makes_no_request(self, server):
        assert build_embedder(settings(server)).embed([]).vectors == []
        assert server.requests == []


class TestRefusals:
    def test_empty_key_refused_before_any_request(self, server):
        with pytest.raises(ModelError, match="API key"):
            build_llm(settings(server, "openrouter", ""))
        with pytest.raises(ModelError, match="API key"):
            build_embedder(settings(server, "openrouter", ""))
        assert server.requests == []

    def test_unknown_backend_refused(self, server):
        with pytest.raises(ModelError, match="not approved"):
            build_llm(settings(server, "someone-else", KEY))
        with pytest.raises(ModelError, match="not approved"):
            build_embedder(settings(server, "someone-else", KEY))
        assert server.requests == []


class TestFailures:
    def test_http_500_has_status_and_truncated_body_but_no_key(self, server):
        server.status = 500
        server.body = "boom " + KEY + " " + "x" * 2000
        client = build_llm(settings(server, "openrouter", KEY))
        with pytest.raises(ModelError) as caught:
            client.chat([ChatMessage("user", "x")])
        text = str(caught.value)
        assert "500" in text and "boom" in text
        assert KEY not in text and "Bearer" not in text
        assert len(text) < 600
        assert len(server.requests) == 1  # no silent retry

    def test_embeddings_http_error_has_no_key(self, server):
        server.status = 401
        server.body = {"error": f"bad key {KEY}"}
        with pytest.raises(ModelError) as caught:
            build_embedder(settings(server, "openrouter", KEY)).embed(["a"])
        assert "401" in str(caught.value) and KEY not in str(caught.value)

    def test_timeout(self, server):
        server.delay = 1.0
        with pytest.raises(ModelError, match="timed out"):
            build_llm(settings(server, timeout=0.2)).chat([ChatMessage("user", "x")])

    def test_invalid_json_reply(self, server):
        server.body = "<html>not json</html>"
        with pytest.raises(ModelError, match="not valid JSON"):
            build_llm(settings(server)).chat([ChatMessage("user", "x")])
        with pytest.raises(ModelError, match="not valid JSON"):
            build_embedder(settings(server)).embed(["a"])

    def test_connection_refused(self, server):
        config = settings(server)
        server.close()
        with pytest.raises(ModelError, match="Cannot reach"):
            build_llm(config).chat([ChatMessage("user", "x")])


@pytest.mark.skipif(os.environ.get("MANI_LIVE_OLLAMA") != "1", reason="set MANI_LIVE_OLLAMA=1 to use local Ollama")
class TestLiveOllama:
    """Mirrors the Phase 0 check. Talks only to http://localhost:11434."""

    @staticmethod
    def live_settings() -> ManiSettings:
        return ManiSettings(_env_file=None, backend="local", base_url="http://localhost:11434/v1", MANI_API_KEY="",
                            chat_model="qwen3:8b", embedding_model="qwen3-embedding:8b",
                            request_timeout_seconds=300)

    def test_tool_call_round_trip(self):
        client = build_llm(self.live_settings())
        tool = ToolSpec(name="jobs_summary",
                        description="Counts of today's jobs by status for a housing society. "
                                    "Use it for any question about today's jobs.",
                        parameters={"type": "object", "required": ["society"],
                                    "properties": {"society": {"type": "string", "description": "Society name"}}})
        messages = [
            ChatMessage("system", "You are a concise business assistant. Answer from tool results only."),
            ChatMessage("user", "How many jobs were missed today in Green Meadows? Use the tool, do not guess."),
        ]
        first = client.chat(messages, [tool])
        assert len(first.message.tool_calls) == 1
        call = first.message.tool_calls[0]
        assert call.name == "jobs_summary"
        assert "green meadows" in str(call.arguments.get("society", "")).lower()
        assert first.usage.latency_ms > 0
        messages += [first.message,
                     ChatMessage("tool", json.dumps({"society": "Green Meadows", "scheduled": 42, "done": 31,
                                                     "skipped": 4, "missed": 7}),
                                 tool_call_id=call.id, name=call.name)]
        second = client.chat(messages, [tool])
        assert "7" in second.message.content
        assert "<think>" not in second.message.content

    def test_embeddings_are_1024(self):
        result = build_embedder(self.live_settings()).embed(
            ["A payment is Over due for 7 days.", "भुगतान 7 दिन से बकाया है"])
        assert len(result.vectors) == 2
        assert all(len(v) == EMBEDDING_DIMENSIONS for v in result.vectors)
