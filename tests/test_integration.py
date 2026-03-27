"""
Integration tests for MiniMax LLM and TTS providers.

These tests verify real API connectivity and are skipped
when MINIMAX_API_KEY is not set in the environment.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock heavy optional dependencies for TTS tests
for mod in ["MeCab", "unidic", "alkana", "torch"]:
    if mod not in sys.modules:
        from unittest.mock import MagicMock
        sys.modules[mod] = MagicMock()

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
SKIP_REASON = "MINIMAX_API_KEY not set"


@unittest.skipUnless(MINIMAX_API_KEY, SKIP_REASON)
class TestMiniMaxLLMIntegration(unittest.TestCase):
    """Integration tests for MiniMax LLM via LLMClient."""

    def test_chat_completion(self):
        from utils.llm_client import LLMClient

        client = LLMClient(provider="minimax", api_key=MINIMAX_API_KEY)
        messages = [{"role": "user", "content": "Say 'hello' in one word."}]
        result = client.chat(messages, max_tokens=256, temperature=0.01)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_chat_highspeed_model(self):
        from utils.llm_client import LLMClient

        client = LLMClient(
            provider="minimax",
            api_key=MINIMAX_API_KEY,
            model="MiniMax-M2.7-highspeed",
        )
        messages = [{"role": "user", "content": "Reply with just 'ok'."}]
        result = client.chat(messages, max_tokens=256, temperature=0.01)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_temperature_clamping_works(self):
        from utils.llm_client import LLMClient

        client = LLMClient(provider="minimax", api_key=MINIMAX_API_KEY)
        messages = [{"role": "user", "content": "Say 'yes'."}]
        # temperature=0 should be clamped to 0.01 and not error
        result = client.chat(messages, max_tokens=256, temperature=0.0)
        self.assertIsInstance(result, str)


@unittest.skipUnless(MINIMAX_API_KEY, SKIP_REASON)
class TestMiniMaxTTSIntegration(unittest.TestCase):
    """Integration tests for MiniMax Cloud TTS."""

    def test_tts_generates_audio(self):
        from utils.TTS import minimax_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Hello world", voice_id="lovely_girl", output_file=out_path)
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 100)
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_tts_turbo_model(self):
        from utils.TTS import minimax_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts(
                "Test turbo",
                voice_id="sweet_girl",
                model="speech-2.8-turbo",
                output_file=out_path,
            )
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 100)
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
