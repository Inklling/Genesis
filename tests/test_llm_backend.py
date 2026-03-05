"""Tests for llm_backend module — backend abstraction, factory, protocol."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from dojigiri.llm_backend import (
    LLMResponse,
    LLMBackend,
    AnthropicBackend,
    OpenAICompatibleBackend,
    OllamaBackend,
    get_backend,
)


# ─── LLMResponse ──────────────────────────────────────────────────────

class TestLLMResponse:
    def test_dataclass_fields(self):
        r = LLMResponse(text="hello", input_tokens=10, output_tokens=5)
        assert r.text == "hello"
        assert r.input_tokens == 10
        assert r.output_tokens == 5

    def test_equality(self):
        a = LLMResponse(text="x", input_tokens=1, output_tokens=2)
        b = LLMResponse(text="x", input_tokens=1, output_tokens=2)
        assert a == b

    def test_inequality(self):
        a = LLMResponse(text="x", input_tokens=1, output_tokens=2)
        b = LLMResponse(text="y", input_tokens=1, output_tokens=2)
        assert a != b


# ─── AnthropicBackend ─────────────────────────────────────────────────

class TestAnthropicBackend:
    def test_properties(self):
        b = AnthropicBackend(api_key="test-key")
        assert b.is_local is False
        assert b.cost_per_million_input == 3.0
        assert b.cost_per_million_output == 15.0

    def test_no_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear any ANTHROPIC_API_KEY from environment
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                b = AnthropicBackend(api_key=None)
                with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                    b._get_client()

    def test_model_from_env(self):
        with patch.dict(os.environ, {"DOJI_LLM_MODEL": "claude-opus-4-6"}):
            b = AnthropicBackend(api_key="key")
            assert b._model == "claude-opus-4-6"

    def test_model_explicit_overrides_env(self):
        with patch.dict(os.environ, {"DOJI_LLM_MODEL": "from-env"}):
            b = AnthropicBackend(api_key="key", model="explicit")
            assert b._model == "explicit"

    def test_chat_wraps_anthropic_sdk(self):
        b = AnthropicBackend(api_key="test-key")
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="response text")]
        mock_resp.usage.input_tokens = 100
        mock_resp.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_resp
        b._client = mock_client

        result = b.chat(system="sys", messages=[{"role": "user", "content": "hi"}])

        assert isinstance(result, LLMResponse)
        assert result.text == "response text"
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        mock_client.messages.create.assert_called_once()

    def test_conforms_to_protocol(self):
        b = AnthropicBackend(api_key="key")
        assert isinstance(b, LLMBackend)


# ─── OpenAICompatibleBackend ──────────────────────────────────────────

class TestOpenAICompatibleBackend:
    def test_properties_remote(self):
        b = OpenAICompatibleBackend(base_url="http://example.com", is_local=False)
        assert b.is_local is False
        assert b.cost_per_million_input == 1.0
        assert b.cost_per_million_output == 1.0

    def test_properties_local(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:8080", is_local=True)
        assert b.is_local is True
        assert b.cost_per_million_input == 0.0
        assert b.cost_per_million_output == 0.0

    def test_base_url_trailing_slash_stripped(self):
        b = OpenAICompatibleBackend(base_url="http://example.com/")
        assert b._base_url == "http://example.com"

    def test_chat_builds_correct_payload(self):
        b = OpenAICompatibleBackend(
            base_url="http://localhost:8080",
            api_key="test-key",
            model="test-model",
        )

        response_body = json.dumps({
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = b.chat(
                system="you are helpful",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                temperature=0.5,
            )

            assert result.text == "hello"
            assert result.input_tokens == 10
            assert result.output_tokens == 5

            # Verify the request was made
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            assert req.full_url == "http://localhost:8080/v1/chat/completions"
            assert req.get_header("Authorization") == "Bearer test-key"
            assert req.get_header("Content-type") == "application/json"

            # Verify payload
            payload = json.loads(req.data)
            assert payload["model"] == "test-model"
            assert payload["max_tokens"] == 100
            assert payload["temperature"] == 0.5
            assert payload["messages"][0] == {"role": "system", "content": "you are helpful"}
            assert payload["messages"][1] == {"role": "user", "content": "hi"}

    def test_chat_no_auth_header_without_key(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:8080", api_key=None)

        response_body = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            b.chat(system="sys", messages=[{"role": "user", "content": "hi"}])
            req = mock_urlopen.call_args[0][0]
            assert req.get_header("Authorization") is None

    def test_chat_empty_choices_raises(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:8080")

        response_body = json.dumps({"choices": [], "usage": {}}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="empty choices"):
                b.chat(system="sys", messages=[])

    def test_chat_missing_choices_raises(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:8080")

        response_body = json.dumps({"usage": {}}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="empty choices"):
                b.chat(system="sys", messages=[])

    def test_chat_http_error_raises(self):
        import urllib.error
        b = OpenAICompatibleBackend(base_url="http://localhost:8080")

        error = urllib.error.HTTPError(
            url="http://localhost:8080/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},  # type: ignore
            fp=MagicMock(read=MagicMock(return_value=b'server error')),
        )

        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="LLM API error 500"):
                b.chat(system="sys", messages=[])

    def test_chat_url_error_raises(self):
        import urllib.error
        b = OpenAICompatibleBackend(base_url="http://localhost:8080")

        error = urllib.error.URLError(reason="Connection refused")

        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="Cannot connect"):
                b.chat(system="sys", messages=[])

    def test_chat_missing_usage_defaults_to_zero(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:8080")

        response_body = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = b.chat(system="sys", messages=[])
            assert result.input_tokens == 0
            assert result.output_tokens == 0

    def test_conforms_to_protocol(self):
        b = OpenAICompatibleBackend(base_url="http://example.com")
        assert isinstance(b, LLMBackend)


# ─── OllamaBackend ───────────────────────────────────────────────────

class TestOllamaBackend:
    def test_default_host(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove OLLAMA_HOST if set
            env = {k: v for k, v in os.environ.items() if k != "OLLAMA_HOST"}
            with patch.dict(os.environ, env, clear=True):
                b = OllamaBackend()
                assert b._base_url == "http://localhost:11434"

    def test_custom_host_from_env(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://myhost:9999"}):
            b = OllamaBackend()
            assert b._base_url == "http://myhost:9999"

    def test_host_without_scheme_gets_http(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "myhost:9999"}):
            b = OllamaBackend()
            assert b._base_url == "http://myhost:9999"

    def test_is_local(self):
        b = OllamaBackend()
        assert b.is_local is True

    def test_zero_cost(self):
        b = OllamaBackend()
        assert b.cost_per_million_input == 0.0
        assert b.cost_per_million_output == 0.0

    def test_default_model(self):
        with patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                      if k != "DOJI_LLM_MODEL"}, clear=True):
            b = OllamaBackend()
            assert b._model == "llama3.1"

    def test_custom_model(self):
        b = OllamaBackend(model="mistral")
        assert b._model == "mistral"

    def test_conforms_to_protocol(self):
        b = OllamaBackend()
        assert isinstance(b, LLMBackend)


# ─── get_backend factory ─────────────────────────────────────────────

class TestGetBackend:
    def test_explicit_anthropic(self):
        b = get_backend({"backend": "anthropic", "api_key": "test"})
        assert isinstance(b, AnthropicBackend)

    def test_explicit_ollama(self):
        b = get_backend({"backend": "ollama"})
        assert isinstance(b, OllamaBackend)

    def test_explicit_openai_requires_base_url(self):
        with pytest.raises(RuntimeError, match="requires --base-url"):
            get_backend({"backend": "openai"})

    def test_explicit_openai_with_base_url(self):
        b = get_backend({"backend": "openai", "base_url": "http://localhost:8080"})
        assert isinstance(b, OpenAICompatibleBackend)

    def test_unknown_backend_raises(self):
        with pytest.raises(RuntimeError, match="Unknown LLM backend"):
            get_backend({"backend": "gpt4all"})

    def test_auto_detect_anthropic(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}, clear=False):
            b = get_backend({})
            assert isinstance(b, AnthropicBackend)

    def test_auto_detect_ollama(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        env["OLLAMA_HOST"] = "http://localhost:11434"
        with patch.dict(os.environ, env, clear=True):
            b = get_backend({})
            assert isinstance(b, OllamaBackend)

    def test_auto_detect_openai_from_base_url(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "OLLAMA_HOST")}
        with patch.dict(os.environ, env, clear=True):
            b = get_backend({"base_url": "http://localhost:8080"})
            assert isinstance(b, OpenAICompatibleBackend)

    def test_env_var_backend_override(self):
        with patch.dict(os.environ, {"DOJI_LLM_BACKEND": "ollama"}, clear=False):
            b = get_backend({})
            assert isinstance(b, OllamaBackend)

    def test_config_overrides_env(self):
        with patch.dict(os.environ, {"DOJI_LLM_BACKEND": "ollama"}, clear=False):
            b = get_backend({"backend": "anthropic", "api_key": "test"})
            assert isinstance(b, AnthropicBackend)

    def test_model_passed_through(self):
        b = get_backend({"backend": "ollama", "model": "codellama"})
        assert isinstance(b, OllamaBackend)
        assert b._model == "codellama"

    def test_case_insensitive_backend(self):
        b = get_backend({"backend": "OLLAMA"})
        assert isinstance(b, OllamaBackend)

    def test_openai_compatible_alias(self):
        b = get_backend({"backend": "openai-compatible", "base_url": "http://localhost:8080"})
        assert isinstance(b, OpenAICompatibleBackend)

    def test_none_config_defaults(self):
        """get_backend(None) should not crash."""
        # Will default to anthropic (may fail at runtime if no key, but should return backend)
        b = get_backend(None)
        assert isinstance(b, (AnthropicBackend, OllamaBackend, OpenAICompatibleBackend))
