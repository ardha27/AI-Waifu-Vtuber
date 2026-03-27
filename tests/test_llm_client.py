"""Unit tests for the LLM client abstraction."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.llm_client import (
    LLMClient,
    PROVIDER_PRESETS,
    PROVIDER_MODELS,
    _clamp_temperature,
    _strip_think_tags,
)


class TestClampTemperature(unittest.TestCase):
    """Test temperature clamping for different providers."""

    def test_minimax_clamps_zero_to_minimum(self):
        self.assertEqual(_clamp_temperature("minimax", 0.0), 0.01)

    def test_minimax_clamps_negative_to_minimum(self):
        self.assertEqual(_clamp_temperature("minimax", -1.0), 0.01)

    def test_minimax_clamps_above_one(self):
        self.assertEqual(_clamp_temperature("minimax", 2.0), 1.0)

    def test_minimax_preserves_valid_temperature(self):
        self.assertEqual(_clamp_temperature("minimax", 0.7), 0.7)

    def test_minimax_preserves_one(self):
        self.assertEqual(_clamp_temperature("minimax", 1.0), 1.0)

    def test_openai_no_clamping(self):
        self.assertEqual(_clamp_temperature("openai", 0.0), 0.0)
        self.assertEqual(_clamp_temperature("openai", 2.0), 2.0)

    def test_none_temperature(self):
        self.assertIsNone(_clamp_temperature("minimax", None))
        self.assertIsNone(_clamp_temperature("openai", None))


class TestStripThinkTags(unittest.TestCase):
    """Test stripping <think>...</think> tags from MiniMax output."""

    def test_strips_think_tags(self):
        text = "<think>reasoning here</think>Hello!"
        self.assertEqual(_strip_think_tags(text), "Hello!")

    def test_strips_multiline_think_tags(self):
        text = "<think>\nline1\nline2\n</think>Answer here"
        self.assertEqual(_strip_think_tags(text), "Answer here")

    def test_no_think_tags(self):
        text = "No thinking here"
        self.assertEqual(_strip_think_tags(text), "No thinking here")

    def test_empty_string(self):
        self.assertEqual(_strip_think_tags(""), "")

    def test_multiple_think_tags(self):
        text = "<think>a</think>Hello <think>b</think>World"
        self.assertEqual(_strip_think_tags(text), "Hello World")


class TestProviderPresets(unittest.TestCase):
    """Test provider presets configuration."""

    def test_openai_preset_exists(self):
        self.assertIn("openai", PROVIDER_PRESETS)
        self.assertEqual(PROVIDER_PRESETS["openai"]["base_url"], "https://api.openai.com/v1")
        self.assertEqual(PROVIDER_PRESETS["openai"]["default_model"], "gpt-3.5-turbo")

    def test_minimax_preset_exists(self):
        self.assertIn("minimax", PROVIDER_PRESETS)
        self.assertEqual(PROVIDER_PRESETS["minimax"]["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(PROVIDER_PRESETS["minimax"]["default_model"], "MiniMax-M2.7")

    def test_minimax_env_key(self):
        self.assertEqual(PROVIDER_PRESETS["minimax"]["env_key"], "MINIMAX_API_KEY")

    def test_provider_models_minimax(self):
        models = PROVIDER_MODELS["minimax"]
        self.assertIn("MiniMax-M2.7", models)
        self.assertIn("MiniMax-M2.7-highspeed", models)
        self.assertIn("MiniMax-M2.5", models)
        self.assertIn("MiniMax-M2.5-highspeed", models)

    def test_provider_models_openai(self):
        models = PROVIDER_MODELS["openai"]
        self.assertIn("gpt-3.5-turbo", models)
        self.assertIn("gpt-4", models)


class TestLLMClientInit(unittest.TestCase):
    """Test LLMClient initialization."""

    @patch("utils.llm_client.OpenAI")
    def test_init_openai_provider(self, mock_openai):
        client = LLMClient(provider="openai", api_key="test-key")
        self.assertEqual(client.provider, "openai")
        self.assertEqual(client.model, "gpt-3.5-turbo")
        self.assertEqual(client.base_url, "https://api.openai.com/v1")

    @patch("utils.llm_client.OpenAI")
    def test_init_minimax_provider(self, mock_openai):
        client = LLMClient(provider="minimax", api_key="test-key")
        self.assertEqual(client.provider, "minimax")
        self.assertEqual(client.model, "MiniMax-M2.7")
        self.assertEqual(client.base_url, "https://api.minimax.io/v1")

    @patch("utils.llm_client.OpenAI")
    def test_init_custom_model(self, mock_openai):
        client = LLMClient(provider="minimax", api_key="k", model="MiniMax-M2.7-highspeed")
        self.assertEqual(client.model, "MiniMax-M2.7-highspeed")

    @patch("utils.llm_client.OpenAI")
    def test_init_custom_base_url(self, mock_openai):
        client = LLMClient(provider="openai", api_key="k", base_url="http://localhost:8080/v1")
        self.assertEqual(client.base_url, "http://localhost:8080/v1")

    def test_init_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            LLMClient(provider="unknown", api_key="k")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_api_key_raises(self):
        with self.assertRaises(ValueError):
            LLMClient(provider="openai")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "env-key"}, clear=True)
    @patch("utils.llm_client.OpenAI")
    def test_auto_detect_minimax_from_env(self, mock_openai):
        client = LLMClient()
        self.assertEqual(client.provider, "minimax")
        self.assertEqual(client.api_key, "env-key")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "oai-key"}, clear=True)
    @patch("utils.llm_client.OpenAI")
    def test_auto_detect_openai_from_env(self, mock_openai):
        client = LLMClient()
        self.assertEqual(client.provider, "openai")

    @patch("utils.llm_client.OpenAI")
    def test_repr(self, mock_openai):
        client = LLMClient(provider="minimax", api_key="k")
        self.assertIn("minimax", repr(client))
        self.assertIn("MiniMax-M2.7", repr(client))


class TestLLMClientChat(unittest.TestCase):
    """Test LLMClient.chat() method."""

    @patch("utils.llm_client.OpenAI")
    def test_chat_returns_text(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, I'm Pina!"
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(provider="openai", api_key="k")
        result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(result, "Hello, I'm Pina!")

    @patch("utils.llm_client.OpenAI")
    def test_chat_minimax_strips_think_tags(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "<think>hmm</think>Hello!"
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(provider="minimax", api_key="k")
        result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(result, "Hello!")

    @patch("utils.llm_client.OpenAI")
    def test_chat_minimax_clamps_temperature(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "ok"
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(provider="minimax", api_key="k")
        client.chat([{"role": "user", "content": "Hi"}], temperature=0.0)

        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs.get("temperature") or call_kwargs[1].get("temperature"), 0.01)

    @patch("utils.llm_client.OpenAI")
    def test_chat_handles_none_content(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient(provider="openai", api_key="k")
        result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertEqual(result, "")

    @patch("utils.llm_client.OpenAI")
    def test_list_models(self, mock_openai_cls):
        client = LLMClient(provider="minimax", api_key="k")
        models = client.list_models()
        self.assertIn("MiniMax-M2.7", models)
        self.assertIn("MiniMax-M2.7-highspeed", models)


class TestLLMClientProviderCase(unittest.TestCase):
    """Test provider name case insensitivity."""

    @patch("utils.llm_client.OpenAI")
    def test_provider_case_insensitive(self, mock_openai):
        client = LLMClient(provider="MiniMax", api_key="k")
        self.assertEqual(client.provider, "minimax")

    @patch("utils.llm_client.OpenAI")
    def test_provider_uppercase(self, mock_openai):
        client = LLMClient(provider="OPENAI", api_key="k")
        self.assertEqual(client.provider, "openai")


if __name__ == "__main__":
    unittest.main()
